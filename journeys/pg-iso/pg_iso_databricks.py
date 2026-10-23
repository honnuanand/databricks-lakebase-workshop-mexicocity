# Databricks notebook source
# COMMAND ----------

# MAGIC # Isolation & locking, step by step
# MAGIC
# MAGIC A hands-on lab. Run one cell at a time. You will open two connections, hold a transaction and lock on one, show the block on the other, then commit and proceed.
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

# MAGIC ## Setup, connect
# COMMAND ----------

import os, sys, time
sys.path.insert(0, os.path.join(os.getcwd(), '..', '..', 'common', 'scripts'))
from lakebase import connect, _env, branch_endpoint, branch_name
from databricks.sdk import WorkspaceClient
import psycopg

DEMO_TABLE = 'account_isolation_demo'
SCHEMA = _env('LB_SCHEMA', 'bank')
ACCOUNT_ID = 'CTA-TEST-ISOLATION'

def connect_branch():
    w = WorkspaceClient()
    proj = os.environ['LB_PROJECT']
    br = os.environ['LB_BRANCH']
    host, eid, state = branch_endpoint(w, proj, br)
    if not host:
        raise RuntimeError(f'branch {br} not ready ({state})')
    cred = w.postgres.generate_database_credential(
        endpoint=f'{branch_name(proj, br)}/endpoints/{eid}')
    conn = psycopg.connect(host=host, port=5432, dbname='databricks_postgres',
                           user=w.current_user.me().user_name, password=cred.token,
                           sslmode='require', autocommit=True)
    with conn.cursor() as cur:
        cur.execute(f'SET search_path TO {SCHEMA}, public')
    return conn

print('Ready to demonstrate locking.')

# COMMAND ----------

# MAGIC ## Step 1, Create demo table and row
# MAGIC
# MAGIC ```sql
# MAGIC CREATE TABLE account_isolation_demo (
# MAGIC     account_id TEXT PRIMARY KEY,
# MAGIC     available_credit INT
# MAGIC );
# MAGIC INSERT INTO account_isolation_demo VALUES ('CTA-TEST-ISOLATION', 10000);
# MAGIC ```
# COMMAND ----------

with connect() as conn:
    with conn.cursor() as cur:
        cur.execute(f"DROP TABLE IF EXISTS {SCHEMA}.{DEMO_TABLE}")
        cur.execute(f"""
            CREATE TABLE {SCHEMA}.{DEMO_TABLE} (
                account_id TEXT PRIMARY KEY,
                available_credit INT
            )
        """)
        cur.execute(f"INSERT INTO {SCHEMA}.{DEMO_TABLE} VALUES ('{ACCOUNT_ID}', 10000)")
        print(f'✓ Created demo table and row: {ACCOUNT_ID} has 10000 available credit')

# COMMAND ----------

# MAGIC ## Step 2, Session A: BEGIN + UPDATE (hold transaction)
# MAGIC
# MAGIC Open Connection A, start transaction, update the row, but do NOT commit yet.
# MAGIC
# MAGIC ```sql
# MAGIC BEGIN;
# MAGIC UPDATE account_isolation_demo SET available_credit = available_credit - 500
# MAGIC WHERE account_id = 'CTA-TEST-ISOLATION';
# MAGIC ```
# COMMAND ----------

# Session A: hold a transaction and lock
conn_a = connect_branch()
cur_a = conn_a.cursor()
cur_a.execute(f"SET search_path TO {SCHEMA}, public")
cur_a.execute("BEGIN")
cur_a.execute(f"UPDATE {SCHEMA}.{DEMO_TABLE} SET available_credit = available_credit - 500 WHERE account_id = '{ACCOUNT_ID}'")
print(f'✓ Session A: began transaction, updated row (lock held, NOT committed)')
print(f'  Available credit now 9500 (locally to Session A)')

# COMMAND ----------

# MAGIC ## Step 3, Session B: UPDATE (will block)
# MAGIC
# MAGIC Open Connection B and try to update the same row. Session B blocks on Session A's lock.
# MAGIC
# MAGIC ```sql
# MAGIC UPDATE account_isolation_demo SET available_credit = available_credit - 2500
# MAGIC WHERE account_id = 'CTA-TEST-ISOLATION';
# MAGIC ```
# COMMAND ----------

import threading

# Session B: try to update (will block)
result_b = {'done': False, 'blocked_until': None}

def session_b_update():
    conn_b = connect_branch()
    cur_b = conn_b.cursor()
    cur_b.execute(f"SET search_path TO {SCHEMA}, public")
    t0 = time.time()
    try:
        cur_b.execute(f"UPDATE {SCHEMA}.{DEMO_TABLE} SET available_credit = available_credit - 2500 WHERE account_id = '{ACCOUNT_ID}'")
        result_b['blocked_until'] = time.time() - t0
        result_b['done'] = True
        cur_b.close()
        conn_b.close()
    except Exception as e:
        result_b['error'] = str(e)

print(f'✓ Session B: UPDATE blocked (waiting for Session A\'s lock)...')
thread_b = threading.Thread(target=session_b_update)
thread_b.start()
time.sleep(1)  # Let B block
print(f'  Session B still blocked: {not result_b["done"]}')

# COMMAND ----------

# MAGIC ## Step 4, Session A: COMMIT (release lock)
# MAGIC
# MAGIC Commit the transaction on Session A, releasing the lock.
# MAGIC
# MAGIC ```sql
# MAGIC COMMIT;
# MAGIC ```
# COMMAND ----------

cur_a.execute("COMMIT")
print(f'✓ Session A: committed')
print(f'  Lock released. Session B now proceeds...')
thread_b.join(timeout=5)
if result_b['done']:
    print(f'✓ Session B: unblocked and updated in {result_b["blocked_until"]:.2f}s')
else:
    print(f'✗ Session B: still waiting or failed')

cur_a.close()
conn_a.close()

# COMMAND ----------

# MAGIC ## Step 5, Confirm both updates landed
# MAGIC
# MAGIC ```sql
# MAGIC SELECT account_id, available_credit FROM account_isolation_demo
# MAGIC WHERE account_id = 'CTA-TEST-ISOLATION';
# MAGIC ```
# COMMAND ----------

with connect() as conn:
    with conn.cursor() as cur:
        cur.execute(f"SET search_path TO {SCHEMA}, public")
        cur.execute(f"SELECT account_id, available_credit FROM {SCHEMA}.{DEMO_TABLE} WHERE account_id = '{ACCOUNT_ID}'")
        row = cur.fetchone()
        if row:
            account_id, credit = row
            print(f'✓ Final state: {account_id} has {credit} available credit')
            print(f'  Started with 10000, Session A subtracted 500, Session B subtracted 2500 = {credit}')
            if credit == 7000:
                print(f'✓ Both updates landed; neither was lost')
        else:
            print(f'✗ Row not found')

# COMMAND ----------

# MAGIC ## What you learned
# MAGIC
# MAGIC Postgres row-level locking prevents concurrent updates from corrupting data. Session B blocked while Session A held its lock. When A committed, the lock released and B proceeded. Same data, same table, no application-level lock code. Isolation works.