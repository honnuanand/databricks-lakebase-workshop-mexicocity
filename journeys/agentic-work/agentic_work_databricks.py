# Databricks notebook source
# MAGIC %md
# MAGIC # Agentic work - step by step
# MAGIC
# MAGIC A hands-on lab. Run one cell at a time, read what happened, then move on. You will demonstrate an agent with real function calling that reads account risk, decides to place a hold on a flagged account, and remembers what it did in a table. On the second call, the agent refuses to double-hold based on memory.
# MAGIC
# MAGIC **Before you start:** run `00-setup/setup_databricks` once to create your branch, then run the setup cells below. The agent's explanations come from a Foundation Model endpoint (FM_ENDPOINT, default: databricks-claude-opus-4-8); if it is unavailable, the notebook prints a fixed line instead.

# COMMAND ----------

# MAGIC %md
# MAGIC ## Run first: install the driver and pick your branch
# MAGIC Run the next three cells before anything else. They install the Postgres driver, upgrade the
# MAGIC Databricks SDK if your environment's version predates the Lakebase API, and set `LB_PROJECT`,
# MAGIC `LB_BRANCH`, and `LB_SCHEMA` from the widgets at the top of this notebook.
# MAGIC `LB_BRANCH` defaults to the branch `00-setup/setup_databricks` created for you. Change a widget
# MAGIC only if you used a different project or branch name.

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

# MAGIC %md
# MAGIC ## Setup - initialize

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

# MAGIC %md
# MAGIC ## Step 0 - Setup: reset the flagged account
# MAGIC
# MAGIC Put CTA-100240 back on 'watch' and clear any prior hold flag / memory, so the first review places the hold and the second refuses.

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
# MAGIC ## Step 1 - Show initial state
# MAGIC
# MAGIC Check the account status and its riskiest transaction. The SQL:
# MAGIC
# MAGIC ```sql
# MAGIC SELECT account_id, line, type, status, health_pct FROM bank.account WHERE account_id='CTA-100240';
# MAGIC SELECT MAX(anomaly_score) FROM bank.txn WHERE account_id='CTA-100240';
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

# MAGIC %md
# MAGIC ## Step 2 - Agent's function call 1: read account risk
# MAGIC
# MAGIC The agent reads the account status and its top anomaly score. The SQL:
# MAGIC
# MAGIC ```sql
# MAGIC SELECT status FROM bank.account WHERE account_id='CTA-100240';
# MAGIC SELECT MAX(anomaly_score) FROM bank.txn WHERE account_id='CTA-100240';
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
# MAGIC ## Step 3 - Agent's function call 2: place the hold
# MAGIC
# MAGIC The agent freezes the account and writes a flag row to case_note. One logical action, two writes. Then the model explains the action in a sentence or two. The SQL:
# MAGIC
# MAGIC ```sql
# MAGIC UPDATE bank.account SET status='frozen' WHERE account_id='CTA-100240';
# MAGIC INSERT INTO bank.case_note (account_id, writeup, category, finding, action, confidence)
# MAGIC VALUES ('CTA-100240', '...', 'fraud', '...', 'hold_placed', 0.95);
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

# MAGIC %md
# MAGIC ## Step 4 - Agent remembers what it did
# MAGIC
# MAGIC The agent appends its action to the memory table. The SQL:
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
# MAGIC ## Step 5 - Agent called again: refuses duplicate
# MAGIC
# MAGIC On a second call, the agent reads memory, finds the hold already exists, and refuses to double-hold. The model phrases the refusal.

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

# MAGIC %md
# MAGIC ## What you learned
# MAGIC
# MAGIC An agent with function calling used a Lakebase table as its memory: read account risk, place a hold, remember the action. On the second call, it read its prior memory and refused to double-hold. This pattern scales to complex workflows: fraud, AML, collections, disputes - all agents consulting the same table for idempotent, coordinated action.

# COMMAND ----------

# MAGIC %md
# MAGIC ---
# MAGIC **Next in the Agent developers track:** <a href="$../learning-loop/learning_loop_databricks">Human Review of AI Output →</a>
# MAGIC
# MAGIC <a href="$../../START_HERE">← Back to the table of contents</a>
