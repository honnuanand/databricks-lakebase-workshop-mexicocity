# Databricks notebook source
# COMMAND ----------

# MAGIC # Isolation & locking, step by step
# MAGIC
# MAGIC A hands-on lab. Run one cell at a time. You will open two connections, hold a transaction and lock on one, show the block on the other, then commit and proceed.
# MAGIC
# MAGIC **Before you start:** finish `00-setup/`.
# COMMAND ----------

# MAGIC ## Setup, connect
# COMMAND ----------

import os, sys, time
sys.path.insert(0, os.path.join(os.getcwd(), '..', '..', 'common', 'scripts'))
from lakebase import connect, _env, branch_endpoint, branch_name
from databricks.sdk import WorkspaceClient
import psycopg

DEMO_TABLE = 'machine_isolation_demo'
SCHEMA = _env('LB_SCHEMA', 'factory')
MACHINE_ID = 'M-TEST-ISOLATION'

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
# MAGIC CREATE TABLE machine_isolation_demo (
# MAGIC     machine_id TEXT PRIMARY KEY,
# MAGIC     maintenance_slots INT
# MAGIC );
# MAGIC INSERT INTO machine_isolation_demo VALUES ('M-TEST-ISOLATION', 10);
# MAGIC ```
# COMMAND ----------

with connect() as conn:
    with conn.cursor() as cur:
        cur.execute(f"DROP TABLE IF EXISTS {SCHEMA}.{DEMO_TABLE}")
        cur.execute(f"""
            CREATE TABLE {SCHEMA}.{DEMO_TABLE} (
                machine_id TEXT PRIMARY KEY,
                maintenance_slots INT
            )
        """)
        cur.execute(f"INSERT INTO {SCHEMA}.{DEMO_TABLE} VALUES ('{MACHINE_ID}', 10)")
        print(f'✓ Created demo table and row: {MACHINE_ID} has 10 slots')

# COMMAND ----------

# MAGIC ## Step 2, Session A: BEGIN + UPDATE (hold transaction)
# MAGIC
# MAGIC Open Connection A, start transaction, update the row, but do NOT commit yet.
# MAGIC
# MAGIC ```sql
# MAGIC BEGIN;
# MAGIC UPDATE machine_isolation_demo SET maintenance_slots = maintenance_slots - 1
# MAGIC WHERE machine_id = 'M-TEST-ISOLATION';
# MAGIC ```
# COMMAND ----------

# Session A: hold a transaction and lock
conn_a = connect_branch()
cur_a = conn_a.cursor()
cur_a.execute(f"SET search_path TO {SCHEMA}, public")
cur_a.execute("BEGIN")
cur_a.execute(f"UPDATE {SCHEMA}.{DEMO_TABLE} SET maintenance_slots = maintenance_slots - 1 WHERE machine_id = '{MACHINE_ID}'")
print(f'✓ Session A: began transaction, updated row (lock held, NOT committed)')
print(f'  Rows now have 9 slots (locally to Session A)')

# COMMAND ----------

# MAGIC ## Step 3, Session B: UPDATE (will block)
# MAGIC
# MAGIC Open Connection B and try to update the same row. Session B blocks on Session A's lock.
# MAGIC
# MAGIC ```sql
# MAGIC UPDATE machine_isolation_demo SET maintenance_slots = maintenance_slots - 5
# MAGIC WHERE machine_id = 'M-TEST-ISOLATION';
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
        cur_b.execute(f"UPDATE {SCHEMA}.{DEMO_TABLE} SET maintenance_slots = maintenance_slots - 5 WHERE machine_id = '{MACHINE_ID}'")
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
# MAGIC SELECT machine_id, maintenance_slots FROM machine_isolation_demo
# MAGIC WHERE machine_id = 'M-TEST-ISOLATION';
# MAGIC ```
# COMMAND ----------

with connect() as conn:
    with conn.cursor() as cur:
        cur.execute(f"SET search_path TO {SCHEMA}, public")
        cur.execute(f"SELECT machine_id, maintenance_slots FROM {SCHEMA}.{DEMO_TABLE} WHERE machine_id = '{MACHINE_ID}'")
        row = cur.fetchone()
        if row:
            machine_id, slots = row
            print(f'✓ Final state: {machine_id} has {slots} slots')
            print(f'  Started with 10, Session A subtracted 1, Session B subtracted 5 = {slots}')
            if slots == 4:
                print(f'✓ Both updates landed; neither was lost')
        else:
            print(f'✗ Row not found')

# COMMAND ----------

# MAGIC ## What you learned
# MAGIC
# MAGIC Postgres row-level locking prevents concurrent updates from corrupting data. Session B blocked while Session A held its lock. When A committed, the lock released and B proceeded. Same data, same table, no application-level lock code. Isolation works.