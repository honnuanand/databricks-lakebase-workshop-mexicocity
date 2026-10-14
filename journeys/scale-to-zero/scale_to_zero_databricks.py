# Databricks notebook source
# MAGIC %md
# MAGIC # Scale to zero, step by step
# MAGIC
# MAGIC A hands-on lab. Run one cell at a time. You will see that a Lakebase Autoscaling endpoint
# MAGIC auto-suspends its compute to zero when idle (costing nothing) and wakes on the next query in
# MAGIC about two seconds. There is no stop button to press: idle is free, automatically.
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
# MAGIC ## Setup, connect

# COMMAND ----------

import os, sys, time, psycopg
sys.path.insert(0, os.path.join(os.getcwd(), "..", "..", "common", "scripts"))
from lakebase import client, branch_name, PG_PORT, DEFAULT_DB

PROJECT = os.environ["LB_PROJECT"]
MINE    = os.environ["LB_BRANCH"]
w = client()

def endpoint_state(branch):
    e = list(w.postgres.list_endpoints(parent=branch_name(PROJECT, branch)))[0]
    st = e.status.current_state.value if e.status and e.status.current_state else "?"
    host = e.status.hosts.host if e.status and e.status.hosts else None
    return st, host, (e.endpoint_id or "primary")

print("connected as", w.current_user.me().user_name)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 1, the endpoint's current state
# MAGIC
# MAGIC `ACTIVE` means compute is up and metering. `IDLE` means it auto-suspended to zero: no compute,
# MAGIC no compute cost. A branch you just used is usually ACTIVE; one you have not queried for a few
# MAGIC minutes will be IDLE. This is a control-plane read (the SDK), not SQL.

# COMMAND ----------

st, host, eid = endpoint_state(MINE)
print(f"branch {MINE}: endpoint {eid} is {st}")
print("IDLE = suspended to zero (free); ACTIVE = serving (metering).")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 2, idle scales to zero on its own
# MAGIC
# MAGIC You do not stop it. With no queries, the endpoint auto-suspends to `IDLE` and the compute is
# MAGIC released. To watch a cold wake clearly, point at a branch that has been idle (for example
# MAGIC `production` if you have not touched it): set `MINE = "production"` in the setup cell and
# MAGIC re-run, or continue on your own branch (the cell below labels whether it was a cold wake).

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 3, wake it on demand with one query, timed
# MAGIC
# MAGIC A single `SELECT 1` wakes the endpoint. Waking is about the compute, not any table, so this
# MAGIC works on any branch. The SQL:
# MAGIC
# MAGIC ```sql
# MAGIC SELECT 1;
# MAGIC ```

# COMMAND ----------

st, host, eid = endpoint_state(MINE)
cold = (st == "IDLE")
print("endpoint is IDLE; timing the wake..." if cold else f"endpoint is {st} (warm, not a cold wake)")
t0 = time.time()
cred = w.postgres.generate_database_credential(endpoint=f"{branch_name(PROJECT, MINE)}/endpoints/{eid}")
conn = psycopg.connect(host=host, port=PG_PORT, dbname=DEFAULT_DB,
                       user=w.current_user.me().user_name, password=cred.token,
                       sslmode="require", autocommit=True, connect_timeout=30)
with conn.cursor() as cur:
    cur.execute("SELECT 1"); cur.fetchone()
dt = (time.time() - t0) * 1000
conn.close()
st2, _, _ = endpoint_state(MINE)
print(f"{'woke IDLE -> ' + st2 if cold else st2}; first query answered in {dt:.0f} ms")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 4, the storage stayed, only compute went away
# MAGIC
# MAGIC Suspending compute never touches your data; only the compute is released and then restored.
# MAGIC Confirm the endpoint is serving again.

# COMMAND ----------

st, _, _ = endpoint_state(MINE)
print(f"branch {MINE} endpoint is now {st}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## What you learned
# MAGIC
# MAGIC Idle Lakebase compute costs nothing, automatically, and wakes on demand in about two seconds
# MAGIC (a cold wake measured about 1.7s on a live run; a warm query is faster). You pay only when you
# MAGIC serve.

# COMMAND ----------

# MAGIC %md
# MAGIC ---
# MAGIC **Next in Part 1:** <a href="$../pg-integration/pg_integration_databricks">Connecting Postgres Tools →</a>
# MAGIC
# MAGIC <a href="$../../START_HERE">← Back to the table of contents</a>
