# Databricks notebook source
# MAGIC %md-sandbox
# MAGIC <div style="display:flex; align-items:center; gap:10px; padding:8px 16px; background:#F9F7F4; border-bottom:2px solid #E0E0E0; font-family:sans-serif; line-height:1;">
# MAGIC   <span style="display:inline-block; width:12px; height:12px; border-radius:2px; background:#FF3621;"></span>
# MAGIC   <span style="font-weight:bold; color:#0b2026;">Lakebase workshop</span>
# MAGIC   <span style="color:#999;">|</span>
# MAGIC   <span style="color:#5A6F77;">Part 2 · Agent developers · Journey 2 of 5 · Tool-Calling Agents</span>
# MAGIC </div>

# COMMAND ----------

# MAGIC %md
# MAGIC # Tool-Calling Agents
# MAGIC #### Duration: about 20 minutes
# MAGIC
# MAGIC *Journey 2 of 5. In Shared Agent Memory, agents only talked. Here an agent acts: it changes data on your branch, and uses the same memory table to remember what it did.*
# MAGIC
# MAGIC ## Overview
# MAGIC
# MAGIC `CTA-100240` is still on `watch`, and its riskiest transaction, the late-night SPEI transfer, scored
# MAGIC 8.7. A fraud-ops agent has two tools: one reads an account's risk, the other places a hold. It should
# MAGIC place the hold once, and only once: if it is asked again, it must notice that the job is done.
# MAGIC
# MAGIC Each tool is a few lines of SQL against your branch. In this lab the order of the tool calls is fixed
# MAGIC in the notebook (read the risk, then place the hold), and a real model explains each decision in
# MAGIC plain language. In a production agent the model would choose which tool to call; the database side,
# MAGIC which is what this lab is about, stays the same.
# MAGIC
# MAGIC ## Learning objectives
# MAGIC
# MAGIC By the end of this lab, you will be able to:
# MAGIC
# MAGIC 1. **Write agent tools as SQL** against Lakebase: one that reads state and one that changes it.
# MAGIC 2. **Record an action in two places** (the account's status and a case note) so it's visible to people and to other systems.
# MAGIC 3. **Make an agent idempotent** by checking its memory before it acts.
# MAGIC 4. **Explain how the model fits in:** it explains the decision; the tools and the data do the work.

# COMMAND ----------

# MAGIC %md
# MAGIC ## Key concepts
# MAGIC
# MAGIC - **Tool:** a function an agent can call to read or change the outside world. Here, `get_account_risk` and `place_hold` are SQL on your branch.
# MAGIC - **Function calling:** a model feature where the model picks a tool and its arguments. This lab fixes the order in code, so you can see each tool's effect step by step.
# MAGIC - **Idempotent action:** an action that has the same result whether it runs once or twice. The agent checks memory first, so a second request doesn't place a second hold.
# MAGIC - **Audit trail:** the `case_note` row with `action='hold_placed'` records what the agent did, when, and why.
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
# MAGIC     Attach this notebook to <strong>serverless</strong> compute. The agent's explanations come from the
# MAGIC     Foundation Model endpoint <code>databricks-claude-opus-4-8</code> (left sidebar, <strong>Serving</strong>);
# MAGIC     if it isn't available, the notebook prints a fixed line instead. Shared Agent Memory is not
# MAGIC     required first.
# MAGIC   </div>
# MAGIC </div>
# MAGIC
# MAGIC <div style="max-width:720px; margin:12px auto; font-family:sans-serif;">
# MAGIC <svg viewBox="0 0 720 150" xmlns="http://www.w3.org/2000/svg" style="width:100%; height:auto; display:block;" font-family="sans-serif">
# MAGIC   <rect x="10" y="10" width="700" height="130" rx="10" fill="#F9F7F4" stroke="#E0E0E0"/>
# MAGIC   <rect x="30" y="45" width="140" height="56" rx="8" fill="#FFFFFF" stroke="#1B5162" stroke-width="2"/>
# MAGIC   <text x="100" y="69" text-anchor="middle" font-size="13" font-weight="700" fill="#0b2026">get_account_risk</text>
# MAGIC   <text x="100" y="88" text-anchor="middle" font-size="11" fill="#5A6F77">read status + score</text>
# MAGIC   <rect x="200" y="45" width="140" height="56" rx="8" fill="#FFF1EE" stroke="#FF3621" stroke-width="2"/>
# MAGIC   <text x="270" y="69" text-anchor="middle" font-size="13" font-weight="700" fill="#0b2026">place_hold</text>
# MAGIC   <text x="270" y="88" text-anchor="middle" font-size="11" fill="#5A6F77">freeze + case note</text>
# MAGIC   <rect x="370" y="45" width="140" height="56" rx="8" fill="#FFFFFF" stroke="#1B5162" stroke-width="2"/>
# MAGIC   <text x="440" y="69" text-anchor="middle" font-size="13" font-weight="700" fill="#0b2026">remember</text>
# MAGIC   <text x="440" y="88" text-anchor="middle" font-size="11" fill="#5A6F77">append to memory</text>
# MAGIC   <rect x="540" y="45" width="150" height="56" rx="8" fill="#FFFFFF" stroke="#5A6F77" stroke-width="2" stroke-dasharray="6 4"/>
# MAGIC   <text x="615" y="69" text-anchor="middle" font-size="13" font-weight="700" fill="#0b2026">asked again</text>
# MAGIC   <text x="615" y="88" text-anchor="middle" font-size="11" fill="#5A6F77">memory says: refuse</text>
# MAGIC   <line x1="170" y1="73" x2="192" y2="73" stroke="#1B5162" stroke-width="2"/><polygon points="192,67 200,73 192,79" fill="#1B5162"/>
# MAGIC   <line x1="340" y1="73" x2="362" y2="73" stroke="#1B5162" stroke-width="2"/><polygon points="362,67 370,73 362,79" fill="#1B5162"/>
# MAGIC   <line x1="510" y1="73" x2="532" y2="73" stroke="#1B5162" stroke-width="2"/><polygon points="532,67 540,73 532,79" fill="#1B5162"/>
# MAGIC   <text x="360" y="125" text-anchor="middle" font-size="11" fill="#5A6F77">all reads and writes are SQL on your branch; the model explains steps 2 and 4</text>
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
# MAGIC This cell loads the shared helper from `common/scripts/` and names the account and tables the
# MAGIC agent works on.
# MAGIC
# MAGIC - `connect()` opens a Postgres connection to your branch. Under the hood it asks the Lakebase API
# MAGIC   for the branch's host name, gets a login token from your Databricks identity (valid for about an
# MAGIC   hour), and connects with `psycopg`, a Postgres driver for Python.
# MAGIC - `fm_call()` sends chat messages to the Foundation Model endpoint over HTTPS, signed in as you, and
# MAGIC   returns the model's text, or `None` if the call fails (then a fixed line is used).
# MAGIC
# MAGIC In the steps below, the SQL block in each step is what runs on your branch.

# COMMAND ----------

import os, sys
import requests
sys.path.insert(0, os.path.join(os.getcwd(), "..", "..", "common", "scripts"))
from lakebase import connect, _env, client

NAMESPACE = "default"
SESSION_ID = "sess-01"
ACCOUNT_ID = "CTA-100240"
FM_ENDPOINT = os.getenv("FM_ENDPOINT", "databricks-claude-opus-4-8")
TABLE_MEMORY = "bank.agent_memory"
TABLE_ACCOUNT = "bank.account"
TABLE_TXN = "bank.txn"
TABLE_CASE = "bank.case_note"

def fm_call(messages, max_tokens=300):
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
        print(f"  (FM API unavailable: {e}; using fallback)")
        return None

print(f"Account under review: {ACCOUNT_ID}, FM endpoint: {FM_ENDPOINT}")

# COMMAND ----------

# MAGIC %md-sandbox
# MAGIC **Expected result:** `Account under review: CTA-100240, FM endpoint: databricks-claude-opus-4-8`
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
# MAGIC ### A3. Reset the account
# MAGIC
# MAGIC Put `CTA-100240` back on `watch` and clear any hold and memory left by an earlier run, so the first
# MAGIC review places the hold and the second one refuses. The SQL:
# MAGIC
# MAGIC ```sql
# MAGIC UPDATE bank.account SET status = 'watch' WHERE account_id = 'CTA-100240';
# MAGIC DELETE FROM bank.case_note WHERE account_id = 'CTA-100240' AND action = 'hold_placed';
# MAGIC DELETE FROM bank.agent_memory
# MAGIC WHERE namespace = 'default' AND session_id = 'sess-01' AND content LIKE '%CTA-100240%';
# MAGIC ```

# COMMAND ----------

with connect() as conn:
    with conn.cursor() as cur:
        cur.execute(f"UPDATE {TABLE_ACCOUNT} SET status='watch' WHERE account_id=%s", [ACCOUNT_ID])
        cur.execute(f"DELETE FROM {TABLE_CASE} WHERE account_id=%s AND action='hold_placed'", [ACCOUNT_ID])
        cur.execute(f"DELETE FROM {TABLE_MEMORY} WHERE namespace=%s AND session_id=%s AND content LIKE %s",
                    [NAMESPACE, SESSION_ID, f"%{ACCOUNT_ID}%"])

print(f"Prepared: {ACCOUNT_ID} reset to 'watch', ready for review")

# COMMAND ----------

# MAGIC %md
# MAGIC **Expected result:** `Prepared: CTA-100240 reset to 'watch', ready for review`
# MAGIC
# MAGIC This also removes the `CTA-100240` rows that Shared Agent Memory wrote, if you ran it before.

# COMMAND ----------

# MAGIC %md
# MAGIC ## B. Look at the account
# MAGIC
# MAGIC Check the account and its riskiest transaction. The SQL:
# MAGIC
# MAGIC ```sql
# MAGIC SELECT account_id, line, type, status, health_pct FROM bank.account WHERE account_id = 'CTA-100240';
# MAGIC SELECT MAX(anomaly_score) FROM bank.txn WHERE account_id = 'CTA-100240';
# MAGIC ```

# COMMAND ----------

with connect() as conn:
    with conn.cursor() as cur:
        cur.execute(f"SELECT account_id, line, type, status, health_pct FROM {TABLE_ACCOUNT} WHERE account_id=%s", [ACCOUNT_ID])
        acct = cur.fetchone()
        cur.execute(f"SELECT MAX(anomaly_score) FROM {TABLE_TXN} WHERE account_id=%s", [ACCOUNT_ID])
        top_score = cur.fetchone()[0]

print(f"Initial state:")
print(f"  {ACCOUNT_ID}: {acct[1]} ({acct[2]}), status={acct[3]}, health={acct[4]}%")
print(f"  top transaction anomaly_score: {top_score}")

# COMMAND ----------

# MAGIC %md-sandbox
# MAGIC **Expected result:**
# MAGIC
# MAGIC ```
# MAGIC Initial state:
# MAGIC   CTA-100240: Credit (retail), status=watch, health=91.00%
# MAGIC   top transaction anomaly_score: 8.70
# MAGIC ```
# MAGIC
# MAGIC **What this proves:** the agent starts from live data: a retail credit account on `watch`, with one transaction scored 8.7.
# MAGIC
# MAGIC <div style="border-left:4px solid #FF9800; background:#FFF3E0; padding:12px 16px; border-radius:4px; margin:12px 0; font-family:sans-serif;">
# MAGIC   <strong style="display:block; color:#E65100; margin-bottom:6px;">Troubleshooting</strong>
# MAGIC   <div style="color:#333;">
# MAGIC     <ul style="margin:0; padding-left:20px;">
# MAGIC       <li><code>TypeError: 'NoneType' object is not subscriptable</code>: <code>CTA-100240</code> isn't on your branch. The bank isn't loaded; rerun <code>00-setup/setup_databricks</code>.</li>
# MAGIC     </ul>
# MAGIC   </div>
# MAGIC </div>

# COMMAND ----------

# MAGIC %md
# MAGIC ## C. Tool 1: read the account's risk
# MAGIC
# MAGIC The first tool the agent calls, `get_account_risk`, reads the status and the top anomaly score.
# MAGIC Scores run from 0 to 10; the agent treats 8 or more as a high fraud signal. The SQL:
# MAGIC
# MAGIC ```sql
# MAGIC SELECT status FROM bank.account WHERE account_id = 'CTA-100240';
# MAGIC SELECT MAX(anomaly_score) FROM bank.txn WHERE account_id = 'CTA-100240';
# MAGIC ```

# COMMAND ----------

with connect() as conn:
    with conn.cursor() as cur:
        cur.execute(f"SELECT status FROM {TABLE_ACCOUNT} WHERE account_id=%s", [ACCOUNT_ID])
        status = cur.fetchone()[0]
        cur.execute(f"SELECT MAX(anomaly_score) FROM {TABLE_TXN} WHERE account_id=%s", [ACCOUNT_ID])
        top_score = cur.fetchone()[0]

print(f"Account risk: status={status}, top anomaly_score={top_score}")
if top_score and float(top_score) >= 8.0:
    print(f"  High fraud signal. The agent will place a hold.")

# COMMAND ----------

# MAGIC %md
# MAGIC **Expected result:**
# MAGIC
# MAGIC ```
# MAGIC Account risk: status=watch, top anomaly_score=8.70
# MAGIC   High fraud signal. The agent will place a hold.
# MAGIC ```
# MAGIC
# MAGIC **What this proves:** a tool is just a query. What the agent knows about the account is exactly what's on your branch.

# COMMAND ----------

# MAGIC %md
# MAGIC ## D. Tool 2: place the hold
# MAGIC
# MAGIC The second tool, `place_hold`, does one logical action with two writes: it freezes the account, and
# MAGIC it writes a `case_note` row that records the hold. Then the model explains the action in a sentence
# MAGIC or two. The SQL:
# MAGIC
# MAGIC ```sql
# MAGIC UPDATE bank.account SET status = 'frozen' WHERE account_id = 'CTA-100240';
# MAGIC INSERT INTO bank.case_note (account_id, writeup, category, finding, action, confidence)
# MAGIC VALUES ('CTA-100240', 'Automated hold: anomaly_score 8.70 on a late-night SPEI transfer to a new beneficiary.',
# MAGIC         'fraud', 'spei_new_beneficiary_anomaly_8.70', 'hold_placed', 0.95);
# MAGIC ```

# COMMAND ----------

with connect() as conn:
    with conn.cursor() as cur:
        cur.execute(f"UPDATE {TABLE_ACCOUNT} SET status='frozen' WHERE account_id=%s", [ACCOUNT_ID])
        cur.execute(
            f"""INSERT INTO {TABLE_CASE} (account_id, writeup, category, finding, action, confidence)
               VALUES (%s, %s, 'fraud', %s, 'hold_placed', 0.95)""",
            [ACCOUNT_ID,
             f"Automated hold: anomaly_score {top_score} on a late-night SPEI transfer to a new beneficiary.",
             f"spei_new_beneficiary_anomaly_{top_score}"]
        )

print(f"Placed hold on {ACCOUNT_ID}: account frozen, case_note flag written")

# Let the model narrate the decision; fall back to a canned line.
narrated = fm_call([
    {"role": "system", "content": (
        "You are a fraud-ops agent at a retail bank. You just read an account's status and "
        "its top transaction anomaly score (0-10, higher is riskier), and placed a hold. "
        "State the action and the reason in one or two sentences.")},
    {"role": "user", "content": (
        f"Account {ACCOUNT_ID} status was '{status}', top anomaly_score {top_score}. "
        f"You placed a hold. Summarize.")},
])
response = narrated or (
    f"Hold placed on {ACCOUNT_ID} due to anomaly score {top_score} on a late-night SPEI transfer "
    f"to a new beneficiary. Account frozen pending customer verification."
)
print(f"\nAgent response:\n  {response}")

# COMMAND ----------

# MAGIC %md-sandbox
# MAGIC **Expected result:** the hold, then the model's explanation, which differs on every run. From a test run:
# MAGIC
# MAGIC ```
# MAGIC Placed hold on CTA-100240: account frozen, case_note flag written
# MAGIC
# MAGIC Agent response:
# MAGIC   Placed a hold on account CTA-100240, which was already flagged as 'watch' and showed a high top anomaly score of 8.70, indicating elevated fraud risk warranting the freeze pending review.
# MAGIC ```
# MAGIC
# MAGIC **What this proves:** the agent changed real data. The account is now `frozen`, and the case note says why.
# MAGIC
# MAGIC <div style="border-left:4px solid #1B5162; background:#EEF4F6; padding:12px 16px; border-radius:4px; margin:12px 0; font-family:sans-serif;">
# MAGIC   <strong style="display:block; color:#1B5162; margin-bottom:6px;">See it in the UI (optional)</strong>
# MAGIC   <div style="color:#333;">
# MAGIC     Open the <strong>Lakebase Postgres</strong> app, select your project and your branch, then the
# MAGIC     <strong>Tables</strong> tab. In <code>account</code>, <code>CTA-100240</code> is <code>frozen</code>; in
# MAGIC     <code>case_note</code>, the newest row has <code>action = hold_placed</code>.
# MAGIC   </div>
# MAGIC </div>
# MAGIC
# MAGIC <div style="border-left:4px solid #FF9800; background:#FFF3E0; padding:12px 16px; border-radius:4px; margin:12px 0; font-family:sans-serif;">
# MAGIC   <strong style="display:block; color:#E65100; margin-bottom:6px;">Troubleshooting</strong>
# MAGIC   <div style="color:#333;">
# MAGIC     <ul style="margin:0; padding-left:20px;">
# MAGIC       <li><code>(FM API unavailable: 404 Client Error: Not Found for url: ...; using fallback)</code>: the endpoint name is wrong or it doesn't exist in this workspace. The hold was still placed; only the explanation is the fixed line. To use a model, fix <code>FM_ENDPOINT</code> in A2.</li>
# MAGIC       <li>A <code>403</code> error in the same line: you don't have permission to query the endpoint. Ask your instructor for <code>CAN_QUERY</code> on it.</li>
# MAGIC     </ul>
# MAGIC   </div>
# MAGIC </div>

# COMMAND ----------

# MAGIC %md
# MAGIC ## E. Remember the action
# MAGIC
# MAGIC The agent appends what it did to the shared memory table from Shared Agent Memory. The SQL:
# MAGIC
# MAGIC ```sql
# MAGIC INSERT INTO bank.agent_memory (namespace, session_id, agent_id, role, content)
# MAGIC VALUES ('default', 'sess-01', 'fraud_advisor', 'assistant', 'placed hold on CTA-100240');
# MAGIC ```

# COMMAND ----------

with connect() as conn:
    with conn.cursor() as cur:
        cur.execute(
            f"INSERT INTO {TABLE_MEMORY} (namespace, session_id, agent_id, role, content) "
            f"VALUES (%s, %s, %s, %s, %s)",
            [NAMESPACE, SESSION_ID, "fraud_advisor", "assistant", f"placed hold on {ACCOUNT_ID}"]
        )

print(f"Remembered the hold in agent_memory")

# COMMAND ----------

# MAGIC %md
# MAGIC **Expected result:** `Remembered the hold in agent_memory`
# MAGIC
# MAGIC **What this proves:** the agent's decision is now durable. Any later call, from this agent or another one, can read it.

# COMMAND ----------

# MAGIC %md
# MAGIC ## F. Ask again: the agent refuses
# MAGIC
# MAGIC A second request comes in: review `CTA-100240` and act on the fraud signal. Before calling any tool,
# MAGIC the agent reads its memory. It finds the hold it already placed, refuses to place another, and the
# MAGIC model phrases the refusal. The SQL:
# MAGIC
# MAGIC ```sql
# MAGIC SELECT content FROM bank.agent_memory
# MAGIC WHERE namespace = 'default' AND session_id = 'sess-01'
# MAGIC   AND agent_id = 'fraud_advisor' AND content LIKE '%hold on CTA-100240%';
# MAGIC ```

# COMMAND ----------

with connect() as conn:
    with conn.cursor() as cur:
        cur.execute(
            f"SELECT content FROM {TABLE_MEMORY} "
            f"WHERE namespace=%s AND session_id=%s AND agent_id='fraud_advisor' AND content LIKE %s",
            [NAMESPACE, SESSION_ID, f"%hold on {ACCOUNT_ID}%"]
        )
        prior = cur.fetchone()

if prior:
    print(f"Agent reads memory: \"{prior[0]}\"")
    print(f"REFUSE: {ACCOUNT_ID} is already on hold. No double-action.")
    # Let the model phrase the refusal; fall back to a canned line.
    refusal = fm_call([
        {"role": "system", "content": (
            "You are a fraud-ops agent. You previously placed a hold on this account. "
            "Decline to act again in one sentence.")},
        {"role": "user", "content": f"Prior memory says: a hold is already placed on "
                                     f"{ACCOUNT_ID}. The request is: Review {ACCOUNT_ID} and act on the fraud signal"},
    ])
    print(f"\nAgent response:\n  {refusal or f'{ACCOUNT_ID} is already on hold. No duplicate action needed.'}")
else:
    print(f"No prior hold found")

# COMMAND ----------

# MAGIC %md-sandbox
# MAGIC **Expected result:** from a test run (the last sentence comes from the model and varies):
# MAGIC
# MAGIC ```
# MAGIC Agent reads memory: "placed hold on CTA-100240"
# MAGIC REFUSE: CTA-100240 is already on hold. No double-action.
# MAGIC
# MAGIC Agent response:
# MAGIC   A hold is already in place on CTA-100240, so no further action is needed from me at this time.
# MAGIC ```
# MAGIC
# MAGIC **What this proves:** checking memory before acting makes the agent idempotent: no second hold, no second case note.

# COMMAND ----------

# MAGIC %md-sandbox
# MAGIC ##### EXPAND FOR ADDITIONAL NOTES
# MAGIC
# MAGIC <details>
# MAGIC <summary><strong>Why write to both account.status and case_note?</strong></summary>
# MAGIC
# MAGIC They answer different questions. `account.status = 'frozen'` is what other systems check before
# MAGIC they let money move. The `case_note` row is the audit trail: who placed the hold, why, with what
# MAGIC confidence. Keep the two in one transaction in production, so you never get a frozen account with no
# MAGIC reason, or a reason with no freeze.
# MAGIC
# MAGIC </details>
# MAGIC
# MAGIC <details>
# MAGIC <summary><strong>From fixed steps to real function calling</strong></summary>
# MAGIC
# MAGIC To let the model choose, you describe each tool to the model (name, purpose, arguments) and run
# MAGIC whichever tool it asks for, in a loop, until it answers. The tools stay the same SQL as in this lab,
# MAGIC and the memory check in F becomes one more tool the model can call. The data rules (status values,
# MAGIC the `hold_placed` marker) are what keep the agent safe, whichever way the tools are chosen.
# MAGIC
# MAGIC </details>

# COMMAND ----------

# MAGIC %md-sandbox
# MAGIC ##### Check your understanding
# MAGIC
# MAGIC <details>
# MAGIC <summary><strong>1. What stopped the agent from placing a second hold?</strong></summary>
# MAGIC
# MAGIC It read `agent_memory` before acting, found "placed hold on CTA-100240", and refused.
# MAGIC
# MAGIC </details>
# MAGIC
# MAGIC <details>
# MAGIC <summary><strong>2. Which part of this lab did the model do?</strong></summary>
# MAGIC
# MAGIC It explained the hold and phrased the refusal. The tool calls themselves, reading the risk and placing the hold, are SQL run by the notebook.
# MAGIC
# MAGIC </details>
# MAGIC
# MAGIC <details>
# MAGIC <summary><strong>3. Why does the hold write a case_note row as well as changing the status?</strong></summary>
# MAGIC
# MAGIC The status is what other systems act on; the case note records why the hold was placed, for people and audits.
# MAGIC
# MAGIC </details>

# COMMAND ----------

# MAGIC %md
# MAGIC ## G. Conclusion
# MAGIC
# MAGIC In this lab an agent read an account's risk, froze it, recorded why, remembered the action, and
# MAGIC refused to do it again. Key takeaways:
# MAGIC
# MAGIC 1. **Agent tools are SQL** on your branch: one query to read state, a couple of statements to change it.
# MAGIC 2. **An action should leave a trail:** the status change for systems, the case note for people.
# MAGIC 3. **Memory makes agents idempotent:** check what you already did before you act.
# MAGIC 4. **The model explains; the data decides.** Whether the code or the model picks the tool, the database holds the truth.
# MAGIC
# MAGIC The next journey turns to AI output that needs a person: the model extracts findings from case
# MAGIC notes, and the uncertain ones go to an analyst.

# COMMAND ----------

# MAGIC %md
# MAGIC ---
# MAGIC **Next in the Agent developers track:** <a href="$../learning-loop/learning_loop_databricks">Human Review of AI Output →</a>
# MAGIC
# MAGIC <a href="$../../START_HERE">← Back to the table of contents</a>
