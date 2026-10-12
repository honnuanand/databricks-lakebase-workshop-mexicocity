# Databricks notebook source
# MAGIC %md
# MAGIC # Agent memory - step by step
# MAGIC
# MAGIC A hands-on lab. Run one cell at a time, read what happened, then move on. You will demonstrate two AI agents sharing state in one governed Lakebase table. The agents read the shared memory, respond to questions, and append their turns - no message queue, no cache, just one table.
# MAGIC
# MAGIC **Before you start:** finish `00-setup/` so `LB_PROFILE`, `LB_PROJECT`, `LB_BRANCH`, `LB_SCHEMA` are set and the bank is loaded on your branch. You need FM_ENDPOINT set to a running Foundation Model endpoint (default: databricks-claude-opus-4-8).

# COMMAND ----------

# MAGIC %md
# MAGIC ## Setup - initialize

# COMMAND ----------

import os, sys
import requests
sys.path.insert(0, os.path.join(os.getcwd(), "..", "..", "common", "scripts"))
from lakebase import connect, _env, client

NAMESPACE = "default"
SESSION_ID = "sess-01"
FM_ENDPOINT = os.getenv("FM_ENDPOINT", "databricks-claude-opus-4-8")
TABLE = "bank.agent_memory"
QUESTION = "Is ACCT-100240 cleared, or do we freeze it for suspected fraud?"

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

# MAGIC %md
# MAGIC ## Step 1 - Seed shared memory
# MAGIC
# MAGIC Seed the agent_memory table with a prior fraud note. This is the shared state. The SQL:
# MAGIC
# MAGIC ```sql
# MAGIC INSERT INTO bank.agent_memory (namespace, session_id, agent_id, role, content)
# MAGIC VALUES ('default', 'sess-01', 'fraud_advisor', 'assistant', 'ACCT-100240: card-not-present spike overnight, anomaly score 8.7. Keep on watch, do not release the hold until cardholder is reached.');
# MAGIC ```

# COMMAND ----------

SEED_NOTE = ("ACCT-100240: card-not-present spike overnight, anomaly score 8.7. Keep on watch, "
             "do not release the hold until cardholder is reached.")

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

# MAGIC %md
# MAGIC ## Step 2 - Read prior memory
# MAGIC
# MAGIC Both agents read the shared memory before responding. The SQL:
# MAGIC
# MAGIC ```sql
# MAGIC SELECT agent_id, role, content FROM bank.agent_memory
# MAGIC WHERE namespace='default' AND session_id='sess-01'
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

# MAGIC %md
# MAGIC ## Step 3 - First agent (fraud advisor) responds and appends memory
# MAGIC
# MAGIC The fraud advisor reads the memory, calls the model to decide whether to clear or freeze the account, and appends its turn.

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
    response1 = ("ACCT-100240 is not cleared. An anomaly score of 8.7 on an overnight card-not-present "
                 "spike is a strong fraud signal. Keep the hold in place and verify the charges with the "
                 "cardholder before releasing any funds.")

with connect() as conn:
    with conn.cursor() as cur:
        cur.execute(f"INSERT INTO {TABLE} (namespace, session_id, agent_id, role, content) VALUES (%s,%s,%s,%s,%s)",
                    [NAMESPACE, SESSION_ID, "fraud_advisor", "user", QUESTION])
        cur.execute(f"INSERT INTO {TABLE} (namespace, session_id, agent_id, role, content) VALUES (%s,%s,%s,%s,%s)",
                    [NAMESPACE, SESSION_ID, "fraud_advisor", "assistant", response1])

print("fraud_advisor appended:")
print(f"  {response1}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 4 - Second agent (ops assistant) reads full memory and responds
# MAGIC
# MAGIC The ops assistant reads the FULL memory including the fraud advisor's determination, then appends its own turn. It defers to the fraud advisor.

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
    response2 = ("I will keep the hold on ACCT-100240 in place and not release funds, in line with the fraud "
                 "advisor's determination. I will contact the cardholder to confirm the overnight charges first.")

with connect() as conn:
    with conn.cursor() as cur:
        cur.execute(f"INSERT INTO {TABLE} (namespace, session_id, agent_id, role, content) VALUES (%s,%s,%s,%s,%s)",
                    [NAMESPACE, SESSION_ID, "ops_assistant", "user", QUESTION])
        cur.execute(f"INSERT INTO {TABLE} (namespace, session_id, agent_id, role, content) VALUES (%s,%s,%s,%s,%s)",
                    [NAMESPACE, SESSION_ID, "ops_assistant", "assistant", response2])

print(f"\nops_assistant appended:")
print(f"  {response2}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 5 - Read final memory
# MAGIC
# MAGIC Query the full conversation from the shared table.

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

# MAGIC %md
# MAGIC ## What you learned
# MAGIC
# MAGIC Two agents shared state in one governed Lakebase table without a message queue, cache, or orchestration. Each agent read the table, responded with context, and appended its turn. The pattern is: read, compute, append. Perfect for multi-agent coordination in banking: fraud advisor, operations, collections, disputes - all consulting the same governed table.
# MAGIC
# MAGIC **Next:** Agentic work - an agent that reads live account and transaction data, places a hold, and refuses to double-act based on memory.
