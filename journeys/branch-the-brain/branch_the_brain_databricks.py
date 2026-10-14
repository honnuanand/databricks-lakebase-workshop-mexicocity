# Databricks notebook source
# MAGIC %md
# MAGIC # Branch the brain, step by step
# MAGIC
# MAGIC A hands-on lab. Run one cell at a time, read what happened, then move on. You will fork your
# MAGIC bank database, change an account on the fork, prove your original is untouched, and throw
# MAGIC the fork away.
# MAGIC
# MAGIC Each step shows the real interface: SQL where the step is a query, the SDK where the step is a
# MAGIC control-plane action like forking a branch.
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
# MAGIC The shared helper lives in `common/scripts/`. We open a connection to your branch.

# COMMAND ----------

import os, sys, time
sys.path.insert(0, os.path.join(os.getcwd(), "..", "..", "common", "scripts"))
from lakebase import client, branch_name, branch_endpoint, wait_active
from databricks.sdk.service.postgres import Branch, BranchSpec
from databricks.sdk.common.types.fieldmask import FieldMask
import psycopg

PROJECT = os.environ["LB_PROJECT"]
MINE    = os.environ["LB_BRANCH"]
EXP     = MINE + "-exp"
SCHEMA  = os.environ.get("LB_SCHEMA", "bank")
ACCOUNT = "ACCT-100240"
w = client()

def connect_branch(branch):
    host, eid, state = branch_endpoint(w, PROJECT, branch)
    if not host:
        raise RuntimeError(f"branch {branch} not ready ({state})")
    cred = w.postgres.generate_database_credential(
        endpoint=f"{branch_name(PROJECT, branch)}/endpoints/{eid}")
    conn = psycopg.connect(host=host, port=5432, dbname="databricks_postgres",
                           user=w.current_user.me().user_name, password=cred.token,
                           sslmode="require", autocommit=True)
    with conn.cursor() as cur:
        cur.execute(f"SET search_path TO {SCHEMA}, public")
    return conn

print("connected as", w.current_user.me().user_name)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 1, look at ACCT-100240 on your branch
# MAGIC `ACCT-100240` is a retail Credit account at the New York Midtown branch, one of the accounts
# MAGIC in the bank you loaded in setup. It starts out on `watch` at 91% health. This step is a plain
# MAGIC query, so here is the SQL you could run in any Postgres tool:
# MAGIC
# MAGIC ```sql
# MAGIC SELECT account_id, status, health_pct FROM bank.account WHERE account_id = 'ACCT-100240';
# MAGIC ```

# COMMAND ----------

with connect_branch(MINE) as c, c.cursor() as cur:
    cur.execute("SELECT account_id, status, health_pct FROM account WHERE account_id=%s", [ACCOUNT])
    print("your branch, before:", cur.fetchone())

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 2, fork your branch (zero-copy)
# MAGIC Forking is a control-plane operation, not SQL, so this step uses the SDK. Copy-on-write:
# MAGIC no data copied, API back in under a second, endpoint connectable in about two seconds.
# MAGIC The equivalent from the terminal:
# MAGIC
# MAGIC ```bash
# MAGIC databricks postgres create-branch --profile "$LB_PROFILE" \
# MAGIC   --parent projects/$LB_PROJECT \
# MAGIC   --json '{"branch_id": "'$LB_BRANCH'-exp", "spec": {"source_branch": "projects/'$LB_PROJECT'/branches/'$LB_BRANCH'"}}'
# MAGIC ```

# COMMAND ----------

try:
    w.postgres.update_branch(name=branch_name(PROJECT, EXP),
        branch=Branch(spec=BranchSpec(is_protected=False)), update_mask=FieldMask(field_mask=['spec.is_protected']))
    w.postgres.delete_branch(name=branch_name(PROJECT, EXP)); time.sleep(2)
except Exception:
    pass

t0 = time.time()
w.postgres.create_branch(parent=f"projects/{PROJECT}",
    branch=Branch(spec=BranchSpec(source_branch=branch_name(PROJECT, MINE), no_expiry=True)),
    branch_id=EXP, replace_existing=False)
api_ms = (time.time() - t0) * 1000
waited = wait_active(w, PROJECT, EXP)
print(f"fork API {api_ms:.0f} ms; endpoint ACTIVE in ~{waited:.1f}s")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 3, diverge on the fork, prove production is untouched
# MAGIC Freeze `ACCT-100240` on the fork only, then read it from both branches. The SQL that runs on
# MAGIC the fork:
# MAGIC
# MAGIC ```sql
# MAGIC UPDATE bank.account SET status = 'frozen', health_pct = 70.0 WHERE account_id = 'ACCT-100240';
# MAGIC ```

# COMMAND ----------

with connect_branch(EXP) as c, c.cursor() as cur:
    cur.execute("UPDATE account SET status='frozen', health_pct=70.0 WHERE account_id=%s", [ACCOUNT])
    cur.execute("SELECT account_id, status, health_pct FROM account WHERE account_id=%s", [ACCOUNT])
    print("fork, after change:", cur.fetchone())

with connect_branch(MINE) as c, c.cursor() as cur:
    cur.execute("SELECT account_id, status, health_pct FROM account WHERE account_id=%s", [ACCOUNT])
    print("your branch, still: ", cur.fetchone())

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 4, throw the fork away
# MAGIC Only changed pages were ever written, so discarding leaves zero storage behind and your
# MAGIC branch is intact.

# COMMAND ----------

w.postgres.update_branch(name=branch_name(PROJECT, EXP),
    branch=Branch(spec=BranchSpec(is_protected=False)), update_mask=FieldMask(field_mask=['spec.is_protected']))
w.postgres.delete_branch(name=branch_name(PROJECT, EXP))
print("discarded", EXP)
print("branches now:", [b.branch_id for b in w.postgres.list_branches(parent=f"projects/{PROJECT}")])

# COMMAND ----------

# MAGIC %md
# MAGIC ## What you learned
# MAGIC Branching a live database is seconds-scale and near-free, because it is copy-on-write. You
# MAGIC forked, froze an account, and discarded without touching your source data. Next: **Break it,
# MAGIC then rewind** points this same machinery at the past.
