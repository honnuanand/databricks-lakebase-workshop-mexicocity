# Databricks notebook source
# MAGIC %md
# MAGIC # Break it, then rewind, step by step
# MAGIC
# MAGIC A hands-on lab. Run one cell at a time, read what happened, then move on. You will delete trades from your branch, capture the write-ahead log position (LSN) that marks "before the mistake," then recover by branching at that LSN.
# MAGIC
# MAGIC Each step shows the real interface: SQL for queries, the SDK for control-plane operations like creating a recovery branch.
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
# MAGIC ## Setup, connect to your branch

# COMMAND ----------

import os, sys, time
sys.path.insert(0, os.path.join(os.getcwd(), "..", "..", "common", "scripts"))
from lakebase import client, branch_name, branch_endpoint, wait_active, _env, PG_PORT, DEFAULT_DB
from databricks.sdk.service.postgres import Branch, BranchSpec
from databricks.sdk.common.types.fieldmask import FieldMask
import psycopg

PROJECT = os.environ["LB_PROJECT"]
MINE    = os.environ["LB_BRANCH"]
RESTORE = MINE + "-restore"
SCHEMA  = os.environ.get("LB_SCHEMA", "bank")
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
# MAGIC ## Step 1, look at the trades
# MAGIC
# MAGIC First, confirm trades exist on your branch. The SQL:
# MAGIC
# MAGIC ```sql
# MAGIC SELECT trade_id, fund_id, qty, status FROM bank.trade ORDER BY trade_id;
# MAGIC ```

# COMMAND ----------

with connect_branch(MINE) as conn:
    with conn.cursor() as cur:
        cur.execute("SELECT trade_id, fund_id, qty, status FROM trade ORDER BY trade_id")
        rows = cur.fetchall()
print(f"Trades on your branch ({len(rows)} total):")
for row in rows:
    print(f"  {row}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 2, capture the LSN (before the mistake)
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
# MAGIC ## Step 3, make the mistake (DELETE all trades)
# MAGIC
# MAGIC Simulate a bad query: delete all trades on your branch. Settlements reference trades by a foreign key, so we remove the settlement legs first, then the trades. The SQL:
# MAGIC
# MAGIC ```sql
# MAGIC DELETE FROM bank.settlement;   -- children first (FK to trade)
# MAGIC DELETE FROM bank.trade;
# MAGIC ```

# COMMAND ----------

# The fat-fingered cleanup: settlement rows reference trade (a foreign key),
# so we remove the child settlements first, then the trades.
with connect_branch(MINE) as conn:
    with conn.cursor() as cur:
        cur.execute("DELETE FROM settlement")    # children first (FK to trade)
        cur.execute("DELETE FROM trade")
    with conn.cursor() as cur:
        cur.execute("SELECT count(*) FROM trade")
        tr = cur.fetchone()[0]
        cur.execute("SELECT count(*) FROM settlement")
        stl = cur.fetchone()[0]
print(f"Delete complete. Trades remaining: {tr}, settlements remaining: {stl}")
if tr == 0 and stl == 0:
    print("All trades and their settlements have been deleted from your branch.")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 4, recover via point-in-time restore (PITR)
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
        branch=Branch(spec=BranchSpec(is_protected=False)), update_mask=FieldMask(field_mask=['spec.is_protected']))
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
# MAGIC ## Step 5, read the recovered data from the PITR branch
# MAGIC
# MAGIC The PITR branch was created at the LSN before the DELETE, so the deleted rows are back. Query them:
# MAGIC
# MAGIC ```sql
# MAGIC SELECT trade_id, fund_id, qty, status FROM bank.trade ORDER BY trade_id;
# MAGIC ```

# COMMAND ----------

with connect_branch(RESTORE) as conn:
    with conn.cursor() as cur:
        cur.execute("SELECT trade_id, fund_id, qty, status FROM trade ORDER BY trade_id")
        rows = cur.fetchall()
print(f"Recovered trades from PITR branch ({len(rows)} total):")
for row in rows:
    print(f"  {row}")
print("\nThe deleted data is intact. Every byte is as it was before the mistake.")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 6, discard the recovery branch
# MAGIC
# MAGIC Delete the PITR branch. Only changed pages (if any) were written, so discarding leaves zero storage behind. Your original branch is untouched.

# COMMAND ----------

w.postgres.update_branch(name=branch_name(PROJECT, RESTORE),
    branch=Branch(spec=BranchSpec(is_protected=False)), update_mask=FieldMask(field_mask=['spec.is_protected']))
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

# COMMAND ----------

# MAGIC %md
# MAGIC ---
# MAGIC **Next in Part 1:** <a href="$../write-to-analytics/write_to_analytics_databricks">Lakebase Data in the Lakehouse →</a>
# MAGIC
# MAGIC <a href="$../../START_HERE">← Back to the table of contents</a>
