# Databricks notebook source
# MAGIC %md-sandbox
# MAGIC <div style="display:flex; align-items:center; gap:10px; padding:8px 16px; background:#F9F7F4; border-bottom:2px solid #E0E0E0; font-family:sans-serif; line-height:1;">
# MAGIC   <span style="display:inline-block; width:12px; height:12px; border-radius:2px; background:#FF3621;"></span>
# MAGIC   <span style="font-weight:bold; color:#0b2026;">Lakebase workshop</span>
# MAGIC   <span style="color:#999;">|</span>
# MAGIC   <span style="color:#5A6F77;">Part 1 · Journey 4 of 5 · Scale to Zero</span>
# MAGIC </div>

# COMMAND ----------

# MAGIC %md
# MAGIC # Scale to Zero
# MAGIC #### Duration: about 10 minutes
# MAGIC
# MAGIC *Journey 4 of 5. You've seen what Lakebase does with your data. This one is about cost: what your branch costs when nobody is using it.*
# MAGIC
# MAGIC ## Overview
# MAGIC
# MAGIC It's 23:00 on a Friday. The trading desks have closed, the settlement batches have run, and the
# MAGIC development and test databases each squad uses won't see a query until Monday. An always-on database
# MAGIC charges for those idle hours anyway.
# MAGIC
# MAGIC A Lakebase compute that receives no queries suspends itself after a set time, its **suspend
# MAGIC timeout**, and costs nothing for compute while it's suspended. The next query wakes it in under a
# MAGIC second. Your data isn't affected, because storage is separate from compute.
# MAGIC
# MAGIC ## Learning objectives
# MAGIC
# MAGIC By the end of this lab, you will be able to:
# MAGIC
# MAGIC 1. **Read a compute's state:** `ACTIVE` (running and billed) or `IDLE` (suspended, no compute cost).
# MAGIC 2. **Explain when a compute suspends,** and where its suspend timeout is set.
# MAGIC 3. **Wake a suspended compute** with one query, and measure how long it takes.
# MAGIC 4. **Explain why your data is unaffected:** only compute stops; storage stays.

# COMMAND ----------

# MAGIC %md
# MAGIC ## Key concepts
# MAGIC
# MAGIC - **Compute vs storage:** Lakebase separates the Postgres server that runs queries (compute) from where the data is kept (storage). Compute can stop and start without touching storage.
# MAGIC - **Capacity unit (CU):** how compute size is measured. The workshop's project uses a fixed 1 CU per branch.
# MAGIC - **ACTIVE and IDLE:** an endpoint's state. `ACTIVE` is running and billed for compute; `IDLE` is suspended, with no compute charge.
# MAGIC - **Suspend timeout:** how long an endpoint waits with no queries before it suspends: 5 minutes on the workshop's project. Storage is still billed while the endpoint is idle.
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
# MAGIC     Attach this notebook to <strong>serverless</strong> compute.
# MAGIC   </div>
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
# MAGIC ### A2. Connect
# MAGIC
# MAGIC This defines `endpoint_state()`, which asks Lakebase for a branch's compute state. That's a
# MAGIC control-plane call through the SDK, so it doesn't wake the compute.
# MAGIC
# MAGIC The timed query in D connects the same way the helpers in the other journeys do: it gets a login
# MAGIC token from your Databricks identity (valid for about an hour), then opens a standard Postgres
# MAGIC connection with `psycopg`. The `SELECT 1` it sends is the SQL shown in D.

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

# MAGIC %md-sandbox
# MAGIC **Expected result:** `connected as` your email.
# MAGIC
# MAGIC <div style="border-left:4px solid #FF9800; background:#FFF3E0; padding:12px 16px; border-radius:4px; margin:12px 0; font-family:sans-serif;">
# MAGIC   <strong style="display:block; color:#E65100; margin-bottom:6px;">Troubleshooting</strong>
# MAGIC   <div style="color:#333;">
# MAGIC     <ul style="margin:0; padding-left:20px;">
# MAGIC       <li><code>KeyError: 'LB_PROJECT'</code>: the A1 cells didn't run in this session. Run the three A1 cells, then this one.</li>
# MAGIC     </ul>
# MAGIC   </div>
# MAGIC </div>

# COMMAND ----------

# MAGIC %md
# MAGIC ## B. Check the compute's state
# MAGIC
# MAGIC `ACTIVE` means the compute is running and billed. `IDLE` means it suspended itself and costs
# MAGIC nothing for compute.

# COMMAND ----------

st, host, eid = endpoint_state(MINE)
print(f"branch {MINE}: endpoint {eid} is {st}")
print("IDLE = suspended to zero (free); ACTIVE = serving (metering).")

# COMMAND ----------

# MAGIC %md-sandbox
# MAGIC **Expected result**, depending on how long ago you last used your branch:
# MAGIC
# MAGIC ```
# MAGIC branch u-yourname: endpoint primary is ACTIVE
# MAGIC IDLE = suspended to zero (free); ACTIVE = serving (metering).
# MAGIC ```
# MAGIC
# MAGIC `ACTIVE` if you ran the previous journey in the last few minutes; `IDLE` if your branch has had no
# MAGIC queries for 5 minutes or more. Section C explains why.
# MAGIC
# MAGIC **What this proves:** you can see whether the compute is running without sending it a query, so checking doesn't wake it.
# MAGIC
# MAGIC <div style="border-left:4px solid #FF9800; background:#FFF3E0; padding:12px 16px; border-radius:4px; margin:12px 0; font-family:sans-serif;">
# MAGIC   <strong style="display:block; color:#E65100; margin-bottom:6px;">Troubleshooting</strong>
# MAGIC   <div style="color:#333;">
# MAGIC     <ul style="margin:0; padding-left:20px;">
# MAGIC       <li><code>IndexError: list index out of range</code>: the branch in <code>LB_BRANCH</code> has no compute. Check the name in the widget.</li>
# MAGIC       <li><code>NotFound: branch id not found</code>: your branch doesn't exist yet. Run <code>00-setup/setup_databricks</code>, or check the <code>LB_BRANCH</code> widget.</li>
# MAGIC     </ul>
# MAGIC   </div>
# MAGIC </div>

# COMMAND ----------

# MAGIC %md-sandbox
# MAGIC ## C. When the compute suspends
# MAGIC
# MAGIC You never stop the compute yourself. It suspends after a period with no queries: its **suspend
# MAGIC timeout**. The timeout is set per compute, so a production database can stay up all day while dev
# MAGIC and test branches suspend quickly.
# MAGIC
# MAGIC <div style="border-left:4px solid #1B5162; background:#EEF4F6; padding:12px 16px; border-radius:4px; margin:12px 0; font-family:sans-serif;">
# MAGIC   <strong style="display:block; color:#1B5162; margin-bottom:6px;">See it in the UI (optional)</strong>
# MAGIC   <div style="color:#333;">
# MAGIC     In the <strong>Lakebase Postgres</strong> app, open your project, select your branch, and choose
# MAGIC     <strong>Edit</strong> under <strong>Computes</strong>. The <strong>Scale to zero</strong> setting holds the timeout.
# MAGIC     The <strong>Monitoring</strong> tab shows the suspend and start events under <strong>System Operations</strong>.
# MAGIC   </div>
# MAGIC </div>
# MAGIC
# MAGIC **On the workshop's project the timeout is 5 minutes.** If B showed `ACTIVE`, you can still see a
# MAGIC cold wake: leave your branch alone for 5 minutes (read the notes below, or take a break), then rerun
# MAGIC the cell in B. Once it shows `IDLE`, run D. Checking the state doesn't count as a query, so it
# MAGIC doesn't keep the compute awake.

# COMMAND ----------

# MAGIC %md-sandbox
# MAGIC ##### EXPAND FOR ADDITIONAL NOTES
# MAGIC
# MAGIC <details>
# MAGIC <summary><strong>Choosing a suspend timeout</strong></summary>
# MAGIC
# MAGIC A short timeout saves the most, and suits dev, test, and per-developer branches that are idle
# MAGIC most of the day. The cost is that the first query after a quiet period waits a little longer,
# MAGIC about two thirds of a second in our test, while the compute starts.
# MAGIC
# MAGIC For a production database that serves an application all day, a long timeout, or keeping the
# MAGIC compute always on, avoids that first-query delay. Because the timeout is set per compute, each
# MAGIC branch can use the setting that fits it.
# MAGIC
# MAGIC </details>

# COMMAND ----------

# MAGIC %md
# MAGIC ## D. Wake it with one query
# MAGIC
# MAGIC A single `SELECT 1` wakes the compute. Waking is about compute, not tables, so it works on any
# MAGIC branch. The cell times the whole thing: getting a login token, connecting, and the query.
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
# MAGIC **Expected result**, depending on the state in B (numbers from our test runs):
# MAGIC
# MAGIC - **Cold wake** (it was `IDLE`):
# MAGIC   ```
# MAGIC   endpoint is IDLE; timing the wake...
# MAGIC   woke IDLE -> ACTIVE; first query answered in 865 ms
# MAGIC   ```
# MAGIC - **Warm** (it was already `ACTIVE`):
# MAGIC   ```
# MAGIC   endpoint is ACTIVE (warm, not a cold wake)
# MAGIC   ACTIVE; first query answered in 189 ms
# MAGIC   ```
# MAGIC
# MAGIC Both times include getting a login token and opening a connection. The difference, under a
# MAGIC second, is the compute starting. Your numbers will vary.
# MAGIC
# MAGIC **What this proves:** a suspended database comes back on its own with the first query. There's no start button, and the query still succeeds.

# COMMAND ----------

# MAGIC %md
# MAGIC ## E. Confirm it's serving again
# MAGIC
# MAGIC Suspending never touches your data; only the compute stopped and started.

# COMMAND ----------

st, _, _ = endpoint_state(MINE)
print(f"branch {MINE} endpoint is now {st}")

# COMMAND ----------

# MAGIC %md
# MAGIC **Expected result:** `branch u-yourname endpoint is now ACTIVE`
# MAGIC
# MAGIC **What this proves:** the first query brought the compute back. It stays `ACTIVE` until it has had no queries for 5 minutes again.

# COMMAND ----------

# MAGIC %md-sandbox
# MAGIC ##### Check your understanding
# MAGIC
# MAGIC <details>
# MAGIC <summary><strong>1. Your branch showed `ACTIVE` right after the previous journey. Why?</strong></summary>
# MAGIC
# MAGIC It had a query within the last 5 minutes, the suspend timeout.
# MAGIC
# MAGIC </details>
# MAGIC
# MAGIC <details>
# MAGIC <summary><strong>2. What do you pay for while an endpoint is `IDLE`?</strong></summary>
# MAGIC
# MAGIC Storage. Compute charges stop while the endpoint is suspended.
# MAGIC
# MAGIC </details>
# MAGIC
# MAGIC <details>
# MAGIC <summary><strong>3. Why might a production database use a longer timeout than a dev branch?</strong></summary>
# MAGIC
# MAGIC To avoid the first-query wake delay for an application that serves users all day.
# MAGIC
# MAGIC </details>

# COMMAND ----------

# MAGIC %md
# MAGIC ## F. Conclusion
# MAGIC
# MAGIC In this lab you read a compute's state, saw when it suspends, and woke it with one query. Key
# MAGIC takeaways:
# MAGIC
# MAGIC 1. **An idle compute suspends itself** after its suspend timeout, and costs nothing for compute
# MAGIC    while suspended.
# MAGIC 2. **The next query wakes it,** in under a second in our test.
# MAGIC 3. **The timeout is set per compute,** so each branch can balance cost against first-query delay.
# MAGIC 4. **Data is never affected:** storage is separate, and only compute stops and starts.
# MAGIC
# MAGIC The last journey in Part 1 shows that to your existing tools, Lakebase is standard Postgres.

# COMMAND ----------

# MAGIC %md
# MAGIC ---
# MAGIC **Next in Part 1:** <a href="$../pg-integration/pg_integration_databricks">Connecting Postgres Tools →</a>
# MAGIC
# MAGIC <a href="$../../START_HERE">← Back to the table of contents</a>
