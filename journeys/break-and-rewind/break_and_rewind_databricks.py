# Databricks notebook source
# MAGIC %md
# MAGIC # Break it, then rewind - step by step
# MAGIC
# MAGIC A hands-on lab. Run one cell at a time, read what happened, then move on. You will delete work orders from your branch, capture the write-ahead log position (LSN) that marks "before the mistake," then recover by branching at that LSN.
# MAGIC
# MAGIC Each step shows the real interface: SQL for queries, the SDK for control-plane operations like creating a recovery branch.
# MAGIC
# MAGIC **Before you start:** finish `00-setup/` so `LB_PROFILE`, `LB_PROJECT`, `LB_BRANCH`, `LB_SCHEMA` are set and the factory is loaded on your branch.

# COMMAND ----------

# MAGIC %md
# MAGIC ## Setup - connect to your branch

# COMMAND ----------

import os, sys, time
sys.path.insert(0, os.path.join(os.getcwd(), "..", "..", "common", "scripts"))
from lakebase import client, branch_name, branch_endpoint, wait_active, _env, PG_PORT, DEFAULT_DB
from databricks.sdk.service.postgres import Branch, BranchSpec
import psycopg

PROJECT = os.environ["LB_PROJECT"]
MINE    = os.environ["LB_BRANCH"]
RESTORE = MINE + "-restore"
SCHEMA  = os.environ.get("LB_SCHEMA", "factory")
w = client()

def connect_branch(branch):
    host, eid, state = branch_endpoint(w, PROJECT, branch)
    if not host:
        raise RuntimeError(f"branch {branch} not ready ({state})")
    cred = w.postgres.generate_database_credential(endpoint=f"{branch_name(PROJECT, branch)}/endpoints/{eid}")
    conn = psycopg.connect(host=host, port=PG_PORT, dbname=DEFAULT_DB,
                           user=w.current_user.me().user_name, password=cred.token,
                           sslmode="require", autocommit=True, connect_timeout=20)
    with conn.cursor() as cur:
        cur.execute(f"SET search_path TO {SCHEMA}, public")
    return conn

print("connected as", w.current_user.me().user_name)
print(f"project={PROJECT}, your branch={MINE}, recovery branch will be {RESTORE}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 1 - Look at the work orders
# MAGIC
# MAGIC First, confirm work orders exist on your branch. The SQL:
# MAGIC
# MAGIC ```sql
# MAGIC SELECT wo_id, product_id, qty, status FROM factory.work_order ORDER BY wo_id;
# MAGIC ```

# COMMAND ----------

with connect_branch(MINE) as conn:
    with conn.cursor() as cur:
        cur.execute("SELECT wo_id, product_id, qty, status FROM work_order ORDER BY wo_id")
        rows = cur.fetchall()
print(f"Work orders on your branch ({len(rows)} total):")
for row in rows:
    print(f"  {row}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 2 - Capture the LSN (before the mistake)
# MAGIC
# MAGIC The LSN is the write-ahead log position that marks the state of the database right now. We capture it before the DELETE so we can branch to this exact point later.
# MAGIC
# MAGIC The SQL:
# MAGIC
# MAGIC ```sql
# MAGIC SELECT pg_current_wal_lsn();
# MAGIC ```

# COMMAND ----------

with connect_branch(MINE) as conn:
    with conn.cursor() as cur:
        cur.execute("SELECT pg_current_wal_lsn()")
        lsn = cur.fetchone()[0]
print(f"LSN captured: {lsn}")
print(f"This LSN marks the moment before we delete. We will use it to recover the data.")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 3 - Make the mistake (DELETE all work orders)
# MAGIC
# MAGIC Simulate a bad query: delete all work orders on your branch. The SQL:
# MAGIC
# MAGIC ```sql
# MAGIC DELETE FROM factory.work_order;
# MAGIC ```

# COMMAND ----------

# The fat-fingered cleanup: operation rows reference work_order (a foreign key),
# so we remove the child operations first, then the work orders.
with connect_branch(MINE) as conn:
    with conn.cursor() as cur:
        cur.execute("DELETE FROM operation")     # children first (FK to work_order)
        cur.execute("DELETE FROM work_order")
    with conn.cursor() as cur:
        cur.execute("SELECT count(*) FROM work_order")
        wo = cur.fetchone()[0]
        cur.execute("SELECT count(*) FROM operation")
        ops = cur.fetchone()[0]
print(f"Delete complete. Work orders remaining: {wo}, operations remaining: {ops}")
if wo == 0 and ops == 0:
    print("All work orders and their operations have been deleted from your branch.")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 4 - Recover via point-in-time restore (PITR)
# MAGIC
# MAGIC Create a recovery branch at the LSN we captured before the DELETE. This is a control-plane operation (SDK), not SQL. Copy-on-write means the API returns in under a second, and the recovery branch is connectable in about two seconds.
# MAGIC
# MAGIC The Python SDK call:
# MAGIC
# MAGIC ```python
# MAGIC w.postgres.create_branch(
# MAGIC     parent=f"projects/{project}",
# MAGIC     branch=Branch(spec=BranchSpec(
# MAGIC         source_branch=branch_name(project, mine),
# MAGIC         source_branch_lsn=lsn,
# MAGIC         no_expiry=True)),
# MAGIC     branch_id=restore)
# MAGIC ```

# COMMAND ----------

# Clean up any stale recovery branch from a prior run
try:
    w.postgres.update_branch(name=branch_name(PROJECT, RESTORE),
        branch=Branch(spec=BranchSpec(is_protected=False)), update_mask="spec.is_protected")
    w.postgres.delete_branch(name=branch_name(PROJECT, RESTORE))
    time.sleep(2)
except Exception:
    pass

# Create recovery branch at the captured LSN
t0 = time.time()
w.postgres.create_branch(
    parent=f"projects/{PROJECT}",
    branch=Branch(spec=BranchSpec(
        source_branch=branch_name(PROJECT, MINE),
        source_branch_lsn=lsn,
        no_expiry=True)),
    branch_id=RESTORE, replace_existing=False)
api_ms = (time.time() - t0) * 1000
waited = wait_active(w, PROJECT, RESTORE)
print(f"PITR branch {RESTORE} created")
print(f"  create_branch API returned in {api_ms:.0f} ms")
print(f"  endpoint reached ACTIVE in ~{waited:.1f}s")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 5 - Read the recovered data from the PITR branch
# MAGIC
# MAGIC The PITR branch was created at the LSN before the DELETE, so the deleted rows are back. Query them:
# MAGIC
# MAGIC ```sql
# MAGIC SELECT wo_id, product_id, qty, status FROM factory.work_order ORDER BY wo_id;
# MAGIC ```

# COMMAND ----------

with connect_branch(RESTORE) as conn:
    with conn.cursor() as cur:
        cur.execute("SELECT wo_id, product_id, qty, status FROM work_order ORDER BY wo_id")
        rows = cur.fetchall()
print(f"Recovered work orders from PITR branch ({len(rows)} total):")
for row in rows:
    print(f"  {row}")
print("\nThe deleted data is intact. Every byte is as it was before the mistake.")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 6 - Discard the recovery branch
# MAGIC
# MAGIC Delete the PITR branch. Only changed pages (if any) were written, so discarding leaves zero storage behind. Your original branch is untouched.

# COMMAND ----------

w.postgres.update_branch(name=branch_name(PROJECT, RESTORE),
    branch=Branch(spec=BranchSpec(is_protected=False)), update_mask="spec.is_protected")
w.postgres.delete_branch(name=branch_name(PROJECT, RESTORE))
print(f"Discarded {RESTORE}")
print("\nRecovery complete. The PITR branch is gone, your original branch is unchanged, and recovery data left zero storage behind.")

# COMMAND ----------

# MAGIC %md
# MAGIC ## What you learned
# MAGIC
# MAGIC Point-in-time restore on Lakebase is seconds-scale and copy-on-write. You deleted live data, branched at a past LSN to recover it, read the unchanged rows back, and discarded the recovery branch without touching production or leaving recovery storage behind.
# MAGIC
# MAGIC The key insight: traditional Postgres PITR means base backups and WAL replay, taking minutes to hours. Lakebase PITR is branching, so it is seconds. The page server holds about 30 days of history, so you can recover from mistakes days ago, not just seconds ago.
# MAGIC
# MAGIC **Next:** Scale to zero - stop and start database compute on demand, dropping cost to 0/hr when idle.
