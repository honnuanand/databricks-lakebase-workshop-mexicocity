# Databricks notebook source
# MAGIC %md
# MAGIC # Agentic work - step by step
# MAGIC
# MAGIC A hands-on lab. Run one cell at a time, read what happened, then move on. You will demonstrate an agent with real function calling that reads account risk, decides to place a hold on a flagged account, and remembers what it did in a table. On the second call, the agent refuses to double-hold based on memory.
# MAGIC
# MAGIC **Before you start:** run `00-setup/setup_databricks` once to create your branch, then run the setup cells below.

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
sys.path.insert(0, os.path.join(os.getcwd(), "..", "..", "common", "scripts"))
from lakebase import connect, _env, client

NAMESPACE = "default"
SESSION_ID = "sess-01"
ACCOUNT_ID = "ACCT-100240"
TABLE_MEMORY = "bank.agent_memory"
TABLE_ACCOUNT = "bank.account"
TABLE_TXN = "bank.txn"
TABLE_CASE = "bank.case_note"

print(f"Account under review: {ACCOUNT_ID}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 0 - Setup: reset the flagged account
# MAGIC
# MAGIC Put ACCT-100240 back on 'watch' and clear any prior hold flag / memory, so the first review places the hold and the second refuses.

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
# MAGIC SELECT account_id, line, type, status, health_pct FROM bank.account WHERE account_id='ACCT-100240';
# MAGIC SELECT MAX(anomaly_score) FROM bank.txn WHERE account_id='ACCT-100240';
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
# MAGIC SELECT status FROM bank.account WHERE account_id='ACCT-100240';
# MAGIC SELECT MAX(anomaly_score) FROM bank.txn WHERE account_id='ACCT-100240';
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
# MAGIC The agent freezes the account and writes a flag row to case_note. One logical action, two writes. The SQL:
# MAGIC
# MAGIC ```sql
# MAGIC UPDATE bank.account SET status='frozen' WHERE account_id='ACCT-100240';
# MAGIC INSERT INTO bank.case_note (account_id, writeup, category, finding, action, confidence)
# MAGIC VALUES ('ACCT-100240', '...', 'fraud', '...', 'hold_placed', 0.95);
# MAGIC ```

# COMMAND ----------

with connect() as conn:
    with conn.cursor() as cur:
        cur.execute(f"UPDATE {TABLE_ACCOUNT} SET status='frozen' WHERE account_id=%s", [ACCOUNT_ID])
        cur.execute(
            f"""INSERT INTO {TABLE_CASE} (account_id, writeup, category, finding, action, confidence)
               VALUES (%s, %s, 'fraud', %s, 'hold_placed', 0.95)""",
            [ACCOUNT_ID,
             f"Automated hold: anomaly_score {top_score} on a card-not-present charge.",
             f"card_not_present_anomaly_{top_score}"]
        )

print(f"Placed hold on {ACCOUNT_ID}: account frozen, case_note flag written")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 4 - Agent remembers what it did
# MAGIC
# MAGIC The agent appends its action to the memory table. The SQL:
# MAGIC
# MAGIC ```sql
# MAGIC INSERT INTO bank.agent_memory (namespace, session_id, agent_id, role, content)
# MAGIC VALUES ('default', 'sess-01', 'fraud_advisor', 'assistant', 'placed hold on ACCT-100240');
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
# MAGIC On a second call, the agent reads memory, finds the hold already exists, and refuses to double-hold.

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
