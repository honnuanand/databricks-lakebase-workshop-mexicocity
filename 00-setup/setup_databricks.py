# Databricks notebook source
# MAGIC %md-sandbox
# MAGIC <div style="display:flex; align-items:center; gap:10px; padding:8px 16px; background:#F9F7F4; border-bottom:2px solid #E0E0E0; font-family:sans-serif; line-height:1;">
# MAGIC   <span style="display:inline-block; width:12px; height:12px; border-radius:2px; background:#FF3621;"></span>
# MAGIC   <span style="font-weight:bold; color:#0b2026;">Lakebase workshop</span>
# MAGIC   <span style="color:#999;">|</span>
# MAGIC   <span style="color:#5A6F77;">Setup · Create Your Branch</span>
# MAGIC </div>

# COMMAND ----------

# MAGIC %md
# MAGIC # Setup: Create Your Branch
# MAGIC
# MAGIC Run this notebook once, top to bottom, before any journey. It does the attendee part of
# MAGIC `00-setup/` inside the workspace, with no laptop and no CLI:
# MAGIC
# MAGIC 1. Installs the Postgres driver.
# MAGIC 2. Sets your project and branch name from the widgets at the top of the notebook.
# MAGIC 3. Creates your zero-copy branch, `u-<your email name>`, off `production`.
# MAGIC 4. Loads the bank onto it. This is skipped if the data is already there, so rerunning is safe.
# MAGIC 5. Runs `SELECT 1` and a real query to prove it works.

# COMMAND ----------

# MAGIC %md-sandbox
# MAGIC <div style="border-left:4px solid #1B5162; background:#EEF4F6; padding:12px 16px; border-radius:4px; margin:12px 0; font-family:sans-serif;">
# MAGIC   <strong style="display:block; color:#1B5162; margin-bottom:6px;">Before you start</strong>
# MAGIC   <div style="color:#333;">
# MAGIC     Attach this notebook to <strong>serverless</strong> compute. Your instructor does the rest once,
# MAGIC     before the session: creates the Lakebase project (default <code>bank</code>) and grants your group
# MAGIC     <code>CAN_MANAGE</code> on it so you can create a branch (see <code>provision.md</code> and
# MAGIC     <code>grants.md</code>). On your own, create the project in the UI first:
# MAGIC     <strong>Compute → Lakebase Postgres → Create</strong>, named <code>bank</code>, Postgres 17.
# MAGIC   </div>
# MAGIC </div>

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1. Install the Postgres driver
# MAGIC `psycopg` is the Postgres driver the workshop uses to run SQL. The Databricks SDK is upgraded only
# MAGIC if your environment's version predates the Lakebase API (0.120.0); a newer one is left as is.
# MAGIC The second cell restarts Python so the install takes effect.

# COMMAND ----------

# MAGIC %pip install "databricks-sdk>=0.120.0" "psycopg[binary]==3.3.4"

# COMMAND ----------

dbutils.library.restartPython()

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2. Your project and branch
# MAGIC This adds three widgets at the top of the notebook. `LB_BRANCH` defaults to `u-` plus the part of
# MAGIC your email before the `@`, so `alex.kim@example.com` gets `u-alex-kim`. Change a widget only if
# MAGIC your instructor gave you a different project or branch name, then rerun from here.

# COMMAND ----------

import os, sys
sys.path.insert(0, os.path.join(os.getcwd(), "..", "common", "scripts"))
from lakebase import client, connect, run_sql, notebook_env

env = notebook_env(dbutils)   # defaults: project=bank, schema=bank
w = client()

# COMMAND ----------

# MAGIC %md
# MAGIC ## 3. Check the project exists

# COMMAND ----------

try:
    w.postgres.get_project(name=f"projects/{env['LB_PROJECT']}")
except Exception as e:
    raise SystemExit(
        f"Can't find Lakebase project '{env['LB_PROJECT']}' ({str(e)[:120]}). Ask your instructor for "
        f"the project name and put it in the LB_PROJECT widget, or create the project first.") from e
print(f"project {env['LB_PROJECT']} found")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 4. Create your branch
# MAGIC A copy-on-write fork of `production`: no data is copied, the API returns in under a second, and
# MAGIC the endpoint you connect to is `ACTIVE` in about two seconds. If the branch already exists, this
# MAGIC just confirms it's running.

# COMMAND ----------

import branch
branch.create()

# COMMAND ----------

# MAGIC %md
# MAGIC ## 5. Load the bank onto your branch
# MAGIC Schema + seed data. If your branch already has the bank, this skips the load and just shows
# MAGIC the row counts, so rerunning the notebook doesn't add duplicate transactions.

# COMMAND ----------

import load_bank
with connect() as conn:
    loaded = load_bank.is_loaded(conn)
if loaded:
    print("The bank is already loaded on your branch, so the load was skipped.")
    load_bank.main(["--check"])
else:
    load_bank.main([])

# COMMAND ----------

# MAGIC %md
# MAGIC ## 6. Prove it works

# COMMAND ----------

print("SELECT 1 ->", run_sql("SELECT 1")[0][0])
print("accounts by branch:")
for row in run_sql("SELECT branch_id, count(*) FROM bank.account GROUP BY branch_id ORDER BY branch_id"):
    print("  ", row)

# COMMAND ----------

# MAGIC %md
# MAGIC ---
# MAGIC You're set. **Next in Part 1:** <a href="$../journeys/branch-the-brain/branch_the_brain_databricks">Database Branching →</a>
# MAGIC
# MAGIC Or open the <a href="$../START_HERE">table of contents</a> to see Part 1 and both Part 2 tracks.
# MAGIC Every journey notebook begins with the same install and widget cells, and the widgets default to
# MAGIC the branch you just created.
