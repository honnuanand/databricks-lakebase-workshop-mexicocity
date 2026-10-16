# Databricks notebook source
# MAGIC %md-sandbox
# MAGIC <div style="display:flex; align-items:center; gap:10px; padding:8px 16px; background:#F9F7F4; border-bottom:2px solid #E0E0E0; font-family:sans-serif; line-height:1;">
# MAGIC   <span style="display:inline-block; width:12px; height:12px; border-radius:2px; background:#FF3621;"></span>
# MAGIC   <span style="font-weight:bold; color:#0b2026;">Lakebase workshop</span>
# MAGIC   <span style="color:#999;">|</span>
# MAGIC   <span style="color:#5A6F77;">Part 2 · Agent developers · Journey 1 of 5 · Shared Agent Memory</span>
# MAGIC </div>

# COMMAND ----------

# MAGIC %md
# MAGIC # Shared Agent Memory
# MAGIC #### Duration: about 20 minutes
# MAGIC
# MAGIC *Journey 1 of 5. Part 1 showed what Lakebase does with your data. This track puts AI agents on top of it, starting with the simplest thing agents need: a place to remember.*
# MAGIC
# MAGIC ## Overview
# MAGIC
# MAGIC Overnight, the fraud queue flagged `CTA-100240`: a late-night SPEI transfer of MXN 38,500 to a new
# MAGIC beneficiary, with an anomaly score of 8.7. A fraud advisor agent wrote a note about it. In the
# MAGIC morning, an operations assistant agent is asked whether the hold on the account can be released.
# MAGIC It should give the same answer the fraud advisor would, without the two agents ever talking to each
# MAGIC other.
# MAGIC
# MAGIC In this lab both agents share one Postgres table on your branch. Each agent reads the table, asks a
# MAGIC real model (a Foundation Model endpoint in this workspace) for its answer, and appends its turn. No
# MAGIC message queue, no cache, no orchestration service: just one governed table.
# MAGIC
# MAGIC ## Learning objectives
# MAGIC
# MAGIC By the end of this lab, you will be able to:
# MAGIC
# MAGIC 1. **Seed shared memory** for agents as rows in a Lakebase table.
# MAGIC 2. **Ground a model's answer** in that memory by reading it with SQL and passing it in the prompt.
# MAGIC 3. **Hand context from one agent to another** by appending turns to the same table.
# MAGIC 4. **Explain why a database works as agent memory:** durable, consistent, queryable, and governed like any other table.

# COMMAND ----------

# MAGIC %md
# MAGIC ## Key concepts
# MAGIC
# MAGIC - **Agent memory:** what an agent knows from earlier turns. Here it is rows in `bank.agent_memory`, one per message.
# MAGIC - **Namespace and session:** the `namespace` and `session_id` columns scope memory, so different teams or conversations don't see each other's rows. This lab uses `default` / `sess-01`.
# MAGIC - **Foundation Model endpoint:** a model served by Databricks Model Serving. The notebook calls it over HTTPS with your Databricks identity. The default is `databricks-claude-opus-4-8`.
# MAGIC - **Grounding:** putting facts (here, the memory rows) into the prompt, so the model answers from them instead of from general knowledge.
# MAGIC
# MAGIC More terms are defined in `docs/glossary.md` in the workshop folder.

# COMMAND ----------

# MAGIC %md-sandbox
# MAGIC ## A. Setup
# MAGIC
# MAGIC <div style="border-left:4px solid #1B5162; background:#EEF4F6; padding:12px 16px; border-radius:4px; margin:12px 0; font-family:sans-serif;">
# MAGIC   <strong style="display:block; color:#1B5162; margin-bottom:6px;">Before you start</strong>
# MAGIC   <div style="color:#333;">
# MAGIC     Run <code>00-setup/setup_databricks</code> once to create your branch and load the bank.
# MAGIC     Attach this notebook to <strong>serverless</strong> compute. The agents call the Foundation Model
# MAGIC     endpoint <code>databricks-claude-opus-4-8</code>; it must be <strong>Ready</strong> in this workspace
# MAGIC     (left sidebar, <strong>Serving</strong>). If it isn't, the notebook still runs, with fixed replies.
# MAGIC   </div>
# MAGIC </div>
# MAGIC
# MAGIC <div style="max-width:720px; margin:12px auto; font-family:sans-serif;">
# MAGIC <svg viewBox="0 0 720 200" xmlns="http://www.w3.org/2000/svg" style="width:100%; height:auto; display:block;" font-family="sans-serif">
# MAGIC   <rect x="10" y="10" width="700" height="180" rx="10" fill="#F9F7F4" stroke="#E0E0E0"/>
# MAGIC   <rect x="40" y="40" width="170" height="56" rx="8" fill="#FFFFFF" stroke="#1B5162" stroke-width="2"/>
# MAGIC   <text x="125" y="64" text-anchor="middle" font-size="14" font-weight="700" fill="#0b2026">fraud_advisor</text>
# MAGIC   <text x="125" y="84" text-anchor="middle" font-size="12" fill="#5A6F77">agent 1</text>
# MAGIC   <rect x="40" y="114" width="170" height="56" rx="8" fill="#FFFFFF" stroke="#1B5162" stroke-width="2"/>
# MAGIC   <text x="125" y="138" text-anchor="middle" font-size="14" font-weight="700" fill="#0b2026">ops_assistant</text>
# MAGIC   <text x="125" y="158" text-anchor="middle" font-size="12" fill="#5A6F77">agent 2</text>
# MAGIC   <rect x="290" y="70" width="190" height="70" rx="8" fill="#FFF1EE" stroke="#FF3621" stroke-width="2"/>
# MAGIC   <text x="385" y="98" text-anchor="middle" font-size="14" font-weight="700" fill="#0b2026">bank.agent_memory</text>
# MAGIC   <text x="385" y="118" text-anchor="middle" font-size="12" fill="#5A6F77">one table on your branch</text>
# MAGIC   <rect x="540" y="70" width="150" height="70" rx="8" fill="#FFFFFF" stroke="#5A6F77" stroke-width="2" stroke-dasharray="6 4"/>
# MAGIC   <text x="615" y="98" text-anchor="middle" font-size="14" font-weight="700" fill="#0b2026">model</text>
# MAGIC   <text x="615" y="118" text-anchor="middle" font-size="12" fill="#5A6F77">claude-opus-4-8</text>
# MAGIC   <line x1="210" y1="68" x2="282" y2="95" stroke="#1B5162" stroke-width="2"/>
# MAGIC   <polygon points="282,89 290,98 279,100" fill="#1B5162"/>
# MAGIC   <line x1="210" y1="142" x2="282" y2="117" stroke="#1B5162" stroke-width="2"/>
# MAGIC   <polygon points="279,111 290,113 283,122" fill="#1B5162"/>
# MAGIC   <text x="250" y="60" text-anchor="middle" font-size="11" fill="#5A6F77">read + append</text>
# MAGIC   <text x="250" y="168" text-anchor="middle" font-size="11" fill="#5A6F77">read + append</text>
# MAGIC   <line x1="480" y1="105" x2="532" y2="105" stroke="#5A6F77" stroke-width="2" stroke-dasharray="4 3"/>
# MAGIC   <polygon points="532,99 542,105 532,111" fill="#5A6F77"/>
# MAGIC   <text x="510" y="94" text-anchor="middle" font-size="11" fill="#5A6F77">prompt</text>
# MAGIC </svg>
# MAGIC </div>

# COMMAND ----------

# MAGIC %md
# MAGIC ### A1. Install the driver and pick your branch
# MAGIC
# MAGIC Run the next three cells before anything else. They install the Postgres driver, upgrade the
# MAGIC Databricks SDK if your environment's version predates the Lakebase API, and set `LB_PROJECT`,
# MAGIC `LB_BRANCH`, and `LB_SCHEMA` from the widgets at the top of this notebook. `LB_BRANCH` defaults to
# MAGIC the branch `00-setup/setup_databricks` created for you. Change a widget only if you used a
# MAGIC different project or branch name.

# COMMAND ----------

# MAGIC %pip install "databricks-sdk>=0.120.0" "psycopg[binary]==3.3.4"

# COMMAND ----------

dbutils.library.restartPython()

# COMMAND ----------

import os, sys
sys.path.insert(0, os.path.join(os.getcwd(), "..", "..", "common", "scripts"))
from lakebase import notebook_env
notebook_env(dbutils);

# COMMAND ----------

# MAGIC %md-sandbox
# MAGIC **Expected result:** `signed in as` your email, followed by your project, branch, and schema:
# MAGIC
# MAGIC ```
# MAGIC signed in as alex.kim@example.com
# MAGIC   LB_PROJECT = bank
# MAGIC   LB_BRANCH = u-alex-kim
# MAGIC   LB_SCHEMA = bank
# MAGIC ```
# MAGIC
# MAGIC <div style="border-left:4px solid #FF9800; background:#FFF3E0; padding:12px 16px; border-radius:4px; margin:12px 0; font-family:sans-serif;">
# MAGIC   <strong style="display:block; color:#E65100; margin-bottom:6px;">Troubleshooting</strong>
# MAGIC   <div style="color:#333;">
# MAGIC     <ul style="margin:0; padding-left:20px;">
# MAGIC       <li><code>databricks-sdk ... predates the Lakebase API</code>: rerun the install cell and the restart cell, then this one.</li>
# MAGIC       <li><code>Fill in LB_BRANCH in the widgets at the top of the notebook</code>: type your branch name in the <code>LB_BRANCH</code> box, then rerun this cell.</li>
# MAGIC       <li>The widgets show an old branch name: run <code>dbutils.widgets.removeAll()</code> in a new cell, then rerun this one.</li>
# MAGIC     </ul>
# MAGIC   </div>
# MAGIC </div>

# COMMAND ----------

# MAGIC %md
# MAGIC ### A2. Connect and define the model call
# MAGIC
# MAGIC This cell loads the shared helper from `common/scripts/` and defines the names the lab uses: the
# MAGIC memory table, the session, and the question both agents will answer.
# MAGIC
# MAGIC - `connect()` opens a Postgres connection to your branch. Under the hood it asks the Lakebase API
# MAGIC   for the branch's host name, gets a login token from your Databricks identity (valid for about an
# MAGIC   hour), and connects with `psycopg`, a Postgres driver for Python.
# MAGIC - `fm_call()` sends a list of chat messages to the Foundation Model endpoint over HTTPS, signed in as
# MAGIC   you, and returns the model's text. If the call fails, it prints why and returns `None`, and the
# MAGIC   agent uses a fixed reply instead.
# MAGIC
# MAGIC In the steps below, the SQL block in each step is the statement that runs on your branch. The
# MAGIC Python cell under it sends that statement and prints the result.

# COMMAND ----------

import os, sys
import requests
sys.path.insert(0, os.path.join(os.getcwd(), "..", "..", "common", "scripts"))
from lakebase import connect, _env, client

NAMESPACE = "default"
SESSION_ID = "sess-01"
FM_ENDPOINT = os.getenv("FM_ENDPOINT", "databricks-claude-opus-4-8")
TABLE = "bank.agent_memory"
QUESTION = "Is CTA-100240 cleared, or do we freeze it for suspected fraud?"

def fm_call(messages, max_tokens=400):
    """Call the Foundation Model API; return text, or None to use the fallback."""
    try:
        w = client()
        tok = w.config.authenticate()["Authorization"][len("Bearer "):]
        r = requests.post(
            f"{w.config.host}/serving-endpoints/{FM_ENDPOINT}/invocations",
            headers={"Authorization": f"Bearer {tok}", "Content-Type": "application/json"},
            json={"messages": messages, "max_tokens": max_tokens},
            timeout=60,
        )
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"]
    except Exception as e:
        print(f"  (FM API unavailable: {e}; using fallback simulation)")
        return None

print(f"Session: {SESSION_ID}, FM endpoint: {FM_ENDPOINT}")

# COMMAND ----------

# MAGIC %md-sandbox
# MAGIC **Expected result:** `Session: sess-01, FM endpoint: databricks-claude-opus-4-8`
# MAGIC
# MAGIC <div style="border-left:4px solid #FF9800; background:#FFF3E0; padding:12px 16px; border-radius:4px; margin:12px 0; font-family:sans-serif;">
# MAGIC   <strong style="display:block; color:#E65100; margin-bottom:6px;">Troubleshooting</strong>
# MAGIC   <div style="color:#333;">
# MAGIC     <ul style="margin:0; padding-left:20px;">
# MAGIC       <li><code>Missing required env var LB_PROJECT</code> in a later cell: the A1 cells didn't run in this session. Run the three A1 cells, then this one.</li>
# MAGIC       <li>Your workshop uses a different model endpoint: change the default in the <code>FM_ENDPOINT = ...</code> line of this cell, then rerun it.</li>
# MAGIC     </ul>
# MAGIC   </div>
# MAGIC </div>

# COMMAND ----------

# MAGIC %md
# MAGIC ## B. Seed shared memory
# MAGIC
# MAGIC Start the session with one note from the fraud advisor, as if it had written it overnight. This row
# MAGIC is the shared state both agents will read. The cell first deletes this session's earlier rows, so a
# MAGIC rerun starts clean. The SQL:
# MAGIC
# MAGIC ```sql
# MAGIC INSERT INTO bank.agent_memory (namespace, session_id, agent_id, role, content)
# MAGIC VALUES ('default', 'sess-01', 'fraud_advisor', 'assistant',
# MAGIC         'CTA-100240: late-night SPEI transfer of MXN 38,500 to a new beneficiary, anomaly score 8.7. Keep on watch, do not release the hold until the customer is reached.');
# MAGIC ```

# COMMAND ----------

SEED_NOTE = ("CTA-100240: late-night SPEI transfer of MXN 38,500 to a new beneficiary, anomaly score 8.7. "
             "Keep on watch, do not release the hold until the customer is reached.")

with connect() as conn:
    with conn.cursor() as cur:
        cur.execute(f"DELETE FROM {TABLE} WHERE namespace=%s AND session_id=%s", [NAMESPACE, SESSION_ID])
        cur.execute(
            f"INSERT INTO {TABLE} (namespace, session_id, agent_id, role, content) "
            f"VALUES (%s, %s, %s, %s, %s)",
            [NAMESPACE, SESSION_ID, "fraud_advisor", "assistant", SEED_NOTE]
        )
print("Seeded agent_memory with prior fraud note")

# COMMAND ----------

# MAGIC %md-sandbox
# MAGIC **Expected result:** `Seeded agent_memory with prior fraud note`
# MAGIC
# MAGIC **What this proves:** agent memory is an ordinary row. Any agent, app, or analyst with access to your branch can read it.
# MAGIC
# MAGIC <div style="border-left:4px solid #FF9800; background:#FFF3E0; padding:12px 16px; border-radius:4px; margin:12px 0; font-family:sans-serif;">
# MAGIC   <strong style="display:block; color:#E65100; margin-bottom:6px;">Troubleshooting</strong>
# MAGIC   <div style="color:#333;">
# MAGIC     <ul style="margin:0; padding-left:20px;">
# MAGIC       <li><code>relation "bank.agent_memory" does not exist</code>: the bank isn't loaded on your branch. Rerun <code>00-setup/setup_databricks</code>.</li>
# MAGIC     </ul>
# MAGIC   </div>
# MAGIC </div>

# COMMAND ----------

# MAGIC %md
# MAGIC ## C. Read the shared memory
# MAGIC
# MAGIC Before answering, an agent reads everything in its session, oldest first. The SQL:
# MAGIC
# MAGIC ```sql
# MAGIC SELECT agent_id, role, content FROM bank.agent_memory
# MAGIC WHERE namespace = 'default' AND session_id = 'sess-01'
# MAGIC ORDER BY created_at;
# MAGIC ```

# COMMAND ----------

with connect() as conn:
    with conn.cursor() as cur:
        cur.execute(
            f"SELECT agent_id, role, content FROM {TABLE} "
            f"WHERE namespace=%s AND session_id=%s ORDER BY created_at",
            [NAMESPACE, SESSION_ID]
        )
        rows = cur.fetchall()

print(f"Prior memory ({len(rows)} rows):")
for agent_id, role, content in rows:
    print(f"  {agent_id}: {content[:80]}..." if len(content) > 80 else f"  {agent_id}: {content}")

# COMMAND ----------

# MAGIC %md-sandbox
# MAGIC **Expected result:**
# MAGIC
# MAGIC ```
# MAGIC Prior memory (1 rows):
# MAGIC   fraud_advisor: CTA-100240: late-night SPEI transfer of MXN 38,500 to a new beneficiary, anomaly...
# MAGIC ```
# MAGIC
# MAGIC **What this proves:** the read is plain SQL, so what an agent "remembers" is exactly what's in the table, in order.
# MAGIC
# MAGIC <div style="border-left:4px solid #1B5162; background:#EEF4F6; padding:12px 16px; border-radius:4px; margin:12px 0; font-family:sans-serif;">
# MAGIC   <strong style="display:block; color:#1B5162; margin-bottom:6px;">See it in the UI (optional)</strong>
# MAGIC   <div style="color:#333;">
# MAGIC     Open the <strong>Lakebase Postgres</strong> app, select your project and your branch, then the
# MAGIC     <strong>Tables</strong> tab. <code>agent_memory</code> in the <code>bank</code> schema holds the row you just wrote.
# MAGIC   </div>
# MAGIC </div>

# COMMAND ----------

# MAGIC %md
# MAGIC ## D. The fraud advisor answers
# MAGIC
# MAGIC The fraud advisor gets three messages: its role, the memory rows as context, and the question
# MAGIC *"Is CTA-100240 cleared, or do we freeze it for suspected fraud?"* It calls the model, then appends
# MAGIC two rows to memory: the question and its answer.

# COMMAND ----------

fraud_sys = ("You are a fraud advisor at a retail bank. You read overnight alerts and prior notes "
             "about account risk, including anomaly scores (0-10, higher is riskier). Decide whether "
             "an account should be cleared or kept on a hold / frozen for suspected fraud, grounded in "
             "the notes. Keep answers to 1-2 sentences.")

messages = [{"role": "system", "content": fraud_sys},
            {"role": "system", "content": "Prior context from shared memory:\n" +
             "\n".join(f"{a} ({r}): {c}" for a, r, c in rows)},
            {"role": "user", "content": QUESTION}]

response1 = fm_call(messages)
if response1 is None:
    response1 = ("CTA-100240 is not cleared. An anomaly score of 8.7 on a late-night SPEI transfer to a new "
                 "beneficiary is a strong fraud signal. Keep the hold in place and verify the transfer with "
                 "the customer before releasing any funds.")

with connect() as conn:
    with conn.cursor() as cur:
        cur.execute(f"INSERT INTO {TABLE} (namespace, session_id, agent_id, role, content) VALUES (%s,%s,%s,%s,%s)",
                    [NAMESPACE, SESSION_ID, "fraud_advisor", "user", QUESTION])
        cur.execute(f"INSERT INTO {TABLE} (namespace, session_id, agent_id, role, content) VALUES (%s,%s,%s,%s,%s)",
                    [NAMESPACE, SESSION_ID, "fraud_advisor", "assistant", response1])

print("fraud_advisor appended:")
print(f"  {response1}")

# COMMAND ----------

# MAGIC %md-sandbox
# MAGIC **Expected result:** the model's answer, which differs on every run. From a test run:
# MAGIC
# MAGIC ```
# MAGIC fraud_advisor appended:
# MAGIC   Keep CTA-100240 on hold — per prior notes, the late-night MXN 38,500 SPEI transfer to a new beneficiary (anomaly score 8.7) warrants holding until the customer is reached and verifies the transaction.
# MAGIC ```
# MAGIC
# MAGIC Check that the answer is "keep the hold" and that it cites the note: the SPEI transfer, the 8.7 score, or reaching the customer.
# MAGIC
# MAGIC **What this proves:** the model answered from the shared memory. Nothing about this account was in its prompt except the row you seeded.
# MAGIC
# MAGIC <div style="border-left:4px solid #FF9800; background:#FFF3E0; padding:12px 16px; border-radius:4px; margin:12px 0; font-family:sans-serif;">
# MAGIC   <strong style="display:block; color:#E65100; margin-bottom:6px;">Troubleshooting</strong>
# MAGIC   <div style="color:#333;">
# MAGIC     <ul style="margin:0; padding-left:20px;">
# MAGIC       <li><code>(FM API unavailable: 404 Client Error: Not Found for url: ...; using fallback simulation)</code>: the endpoint name is wrong or it doesn't exist in this workspace. Check <strong>Serving</strong> in the left sidebar, and fix <code>FM_ENDPOINT</code> in A2.</li>
# MAGIC       <li>A <code>403</code> error in the same line: you don't have permission to query the endpoint. Ask your instructor for <code>CAN_QUERY</code> on it.</li>
# MAGIC       <li>With a fallback line, the lab still runs: the agent uses a fixed reply, and the memory flow is the same.</li>
# MAGIC     </ul>
# MAGIC   </div>
# MAGIC </div>

# COMMAND ----------

# MAGIC %md
# MAGIC ## E. The ops assistant answers
# MAGIC
# MAGIC The ops assistant reads the **full** memory, including the fraud advisor's answer, and gets the
# MAGIC same question. Its role says to defer to the fraud advisor's determination when there is one. It
# MAGIC appends its own question and answer.

# COMMAND ----------

with connect() as conn:
    with conn.cursor() as cur:
        cur.execute(
            f"SELECT agent_id, role, content FROM {TABLE} "
            f"WHERE namespace=%s AND session_id=%s ORDER BY created_at",
            [NAMESPACE, SESSION_ID]
        )
        full_memory = cur.fetchall()

print(f"Full memory for ops assistant ({len(full_memory)} rows):")
for agent_id, role, content in full_memory:
    print(f"  {agent_id}: {content[:70]}..." if len(content) > 70 else f"  {agent_id}: {content}")

ops_sys = ("You are an operations assistant at a retail bank branch. You release or keep account holds. "
           "You defer to the fraud advisor's determination when present in the shared notes. Answer whether "
           "the hold stays or can be released, grounded in the notes. Keep answers to 1-2 sentences.")

messages2 = [{"role": "system", "content": ops_sys},
             {"role": "system", "content": "Prior context from shared memory:\n" +
              "\n".join(f"{a} ({r}): {c}" for a, r, c in full_memory)},
             {"role": "user", "content": QUESTION}]

response2 = fm_call(messages2)
if response2 is None:
    response2 = ("I will keep the hold on CTA-100240 in place and not release funds, in line with the fraud "
                 "advisor's determination. I will contact the customer to confirm the late-night transfer first.")

with connect() as conn:
    with conn.cursor() as cur:
        cur.execute(f"INSERT INTO {TABLE} (namespace, session_id, agent_id, role, content) VALUES (%s,%s,%s,%s,%s)",
                    [NAMESPACE, SESSION_ID, "ops_assistant", "user", QUESTION])
        cur.execute(f"INSERT INTO {TABLE} (namespace, session_id, agent_id, role, content) VALUES (%s,%s,%s,%s,%s)",
                    [NAMESPACE, SESSION_ID, "ops_assistant", "assistant", response2])

print(f"\nops_assistant appended:")
print(f"  {response2}")

# COMMAND ----------

# MAGIC %md-sandbox
# MAGIC **Expected result:** three rows of memory, then the ops assistant's answer. From a test run:
# MAGIC
# MAGIC ```
# MAGIC Full memory for ops assistant (3 rows):
# MAGIC   fraud_advisor: CTA-100240: late-night SPEI transfer of MXN 38,500 to a new beneficiar...
# MAGIC   fraud_advisor: Is CTA-100240 cleared, or do we freeze it for suspected fraud?
# MAGIC   fraud_advisor: Keep CTA-100240 on hold — per prior notes, the late-night MXN 38,500 S...
# MAGIC
# MAGIC ops_assistant appended:
# MAGIC   The hold on CTA-100240 stays in place per the fraud advisor's determination — the late-night MXN 38,500 SPEI transfer to a new beneficiary (anomaly score 8.7) must remain held until the customer is reached and verifies the transaction.
# MAGIC ```
# MAGIC
# MAGIC **What this proves:** the second agent picked up the first agent's decision from the table. They never called each other.

# COMMAND ----------

# MAGIC %md-sandbox
# MAGIC ##### EXPAND FOR ADDITIONAL NOTES
# MAGIC
# MAGIC <details>
# MAGIC <summary><strong>Why a table, and not a cache or a message queue</strong></summary>
# MAGIC
# MAGIC Agents need memory that survives restarts, that two agents can read and write at the same time
# MAGIC without losing a turn, and that someone can audit later. A Postgres table gives you all three:
# MAGIC writes are durable as soon as they commit, every reader sees committed rows, and the history is a
# MAGIC `SELECT` away. It's also governed like the rest of your data, so the same access controls apply.
# MAGIC
# MAGIC The `namespace` and `session_id` columns are how you keep memory apart: one namespace per team or
# MAGIC product, one session per conversation. Add an index on `(namespace, session_id, created_at)` when
# MAGIC the table grows.
# MAGIC
# MAGIC </details>

# COMMAND ----------

# MAGIC %md
# MAGIC ## F. Read the whole conversation
# MAGIC
# MAGIC The full session, oldest first. This is the same query as in C; there are just more rows now.

# COMMAND ----------

with connect() as conn:
    with conn.cursor() as cur:
        cur.execute(
            f"SELECT agent_id, role, content FROM {TABLE} "
            f"WHERE namespace=%s AND session_id=%s ORDER BY created_at",
            [NAMESPACE, SESSION_ID]
        )
        final_memory = cur.fetchall()

print(f"Final memory ({len(final_memory)} total rows):")
for agent_id, role, content in final_memory:
    print(f"  [{agent_id}] {content}")

# COMMAND ----------

# MAGIC %md-sandbox
# MAGIC **Expected result:** five rows, in the order they were written (the two answers are cut short here):
# MAGIC
# MAGIC ```
# MAGIC Final memory (5 total rows):
# MAGIC   [fraud_advisor] CTA-100240: late-night SPEI transfer of MXN 38,500 to a new beneficiary, anomaly score 8.7. Keep on watch, do not release the hold until the customer is reached.
# MAGIC   [fraud_advisor] Is CTA-100240 cleared, or do we freeze it for suspected fraud?
# MAGIC   [fraud_advisor] Keep CTA-100240 on hold — ...
# MAGIC   [ops_assistant] Is CTA-100240 cleared, or do we freeze it for suspected fraud?
# MAGIC   [ops_assistant] The hold on CTA-100240 stays in place per the fraud advisor's determination — ...
# MAGIC ```
# MAGIC
# MAGIC **What this proves:** the table is the complete, ordered record of what both agents saw and said.

# COMMAND ----------

# MAGIC %md-sandbox
# MAGIC ##### Check your understanding
# MAGIC
# MAGIC <details>
# MAGIC <summary><strong>1. How did the ops assistant know what the fraud advisor had decided?</strong></summary>
# MAGIC
# MAGIC It read the `agent_memory` table, which already held the fraud advisor's answer. The two agents never messaged each other.
# MAGIC
# MAGIC </details>
# MAGIC
# MAGIC <details>
# MAGIC <summary><strong>2. Why does the model's answer mention the SPEI transfer and the 8.7 score?</strong></summary>
# MAGIC
# MAGIC Because the memory rows were passed to the model in its prompt. That's grounding: the answer comes from your data, not from what the model already knew.
# MAGIC
# MAGIC </details>
# MAGIC
# MAGIC <details>
# MAGIC <summary><strong>3. What do the namespace and session_id columns do?</strong></summary>
# MAGIC
# MAGIC They scope memory, so one team's or one conversation's rows don't mix with another's. Each read filters on both.
# MAGIC
# MAGIC </details>

# COMMAND ----------

# MAGIC %md
# MAGIC ## G. Conclusion
# MAGIC
# MAGIC In this lab two agents shared one Lakebase table: the fraud advisor read a seeded note and
# MAGIC answered, and the ops assistant read both and deferred to it. Key takeaways:
# MAGIC
# MAGIC 1. **Agent memory can be a plain table:** read with `SELECT`, append with `INSERT`, no extra system.
# MAGIC 2. **Grounding is just SQL plus a prompt:** read the rows, pass them to the model, and its answer follows your data.
# MAGIC 3. **Agents coordinate through the data,** not by calling each other: whatever one writes, the next one reads.
# MAGIC 4. **The memory is governed and auditable** like any other table on your branch.
# MAGIC
# MAGIC The next journey gives an agent tools: it reads an account's risk, places a hold, and uses this
# MAGIC same memory table to avoid doing it twice.

# COMMAND ----------

# MAGIC %md
# MAGIC ---
# MAGIC **Next in the Agent developers track:** <a href="$../agentic-work/agentic_work_databricks">Tool-Calling Agents →</a>
# MAGIC
# MAGIC <a href="$../../START_HERE">← Back to the table of contents</a>
