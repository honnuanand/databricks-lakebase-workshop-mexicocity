# Databricks notebook source
# MAGIC %md-sandbox
# MAGIC <div style="display:flex; align-items:center; gap:10px; padding:8px 16px; background:#F9F7F4; border-bottom:2px solid #E0E0E0; font-family:sans-serif; line-height:1;">
# MAGIC   <span style="display:inline-block; width:12px; height:12px; border-radius:2px; background:#FF3621;"></span>
# MAGIC   <span style="font-weight:bold; color:#0b2026;">Lakebase workshop</span>
# MAGIC   <span style="color:#999;">|</span>
# MAGIC   <span style="color:#5A6F77;">Setup · Create Your Project and Branch</span>
# MAGIC </div>

# COMMAND ----------

# MAGIC %md
# MAGIC # Setup: Create Your Project and Branch
# MAGIC
# MAGIC Run this notebook once, top to bottom, before any journey. It does the attendee part of
# MAGIC `00-setup/` inside the workspace, with no laptop and no CLI:
# MAGIC
# MAGIC 1. Installs the Postgres driver.
# MAGIC 2. Sets your project and branch names from the widgets at the top of the notebook.
# MAGIC 3. Creates your own Lakebase project, `bank-<your email name>`, which comes with a `production` branch.
# MAGIC 4. Loads the bank into `production`.
# MAGIC 5. Sets up the Data API on `production`, for the Lakebase Data API journey.
# MAGIC 6. Creates your zero-copy branch, `u-<your email name>`, off `production`. Every journey runs on it.
# MAGIC 7. Runs `SELECT 1` and a real query to prove it works.
# MAGIC
# MAGIC Every step checks first and skips what's already done, so rerunning the notebook is safe.

# COMMAND ----------

# MAGIC %md-sandbox
# MAGIC <div style="border-left:4px solid #1B5162; background:#EEF4F6; padding:12px 16px; border-radius:4px; margin:12px 0; font-family:sans-serif;">
# MAGIC   <strong style="display:block; color:#1B5162; margin-bottom:6px;">Before you start</strong>
# MAGIC   <div style="color:#333;">
# MAGIC     Attach this notebook to <strong>serverless</strong> compute. You need permission to create Lakebase
# MAGIC     projects in this workspace. For the Data API journey, your instructor also creates a workshop
# MAGIC     service principal before the session and stores its client id and secret in the
# MAGIC     <code>lakebase-workshop</code> secret scope. Without that scope, step 5 is skipped and every other
# MAGIC     journey still works.
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
# MAGIC This adds three widgets at the top of the notebook. The names come from the part of your email
# MAGIC before the `@`: `alex.kim@example.com` gets the project `bank-alex-kim` and the branch `u-alex-kim`.
# MAGIC Change a widget only if your instructor gave you different names, then rerun from here.

# COMMAND ----------

import os, sys
sys.path.insert(0, os.path.join(os.getcwd(), "..", "common", "scripts"))
from lakebase import client, connect, run_sql, notebook_env

env = notebook_env(dbutils)   # defaults: project=bank-<email name>, schema=bank
w = client()

# COMMAND ----------

# MAGIC %md
# MAGIC ## 3. Create your project
# MAGIC A Lakebase project is a Postgres database with its own branches and compute. Yours runs Postgres 17,
# MAGIC and its compute suspends itself after 5 minutes without queries, which you'll see in Scale to Zero.
# MAGIC It's ready in a few seconds. If it already exists, this cell just confirms it's running.

# COMMAND ----------

import project
project.create()

# COMMAND ----------

# MAGIC %md
# MAGIC ## 4. Load the bank into `production`
# MAGIC Schema + seed data. `production` keeps this clean copy, and your branch starts from it. If the
# MAGIC bank is already there, this skips the load and just shows the row counts, so rerunning the
# MAGIC notebook doesn't add duplicate transactions.

# COMMAND ----------

import load_bank
with connect(branch="production") as conn:
    loaded = load_bank.is_loaded(conn)
os.environ["LB_BRANCH"] = "production"   # load_bank works on LB_BRANCH
try:
    if loaded:
        print("The bank is already loaded in production, so the load was skipped.")
        load_bank.main(["--check"])
    else:
        load_bank.main([])
finally:
    os.environ["LB_BRANCH"] = env["LB_BRANCH"]

# COMMAND ----------

# MAGIC %md
# MAGIC ## 5. Set up the Data API
# MAGIC The Data API serves your tables over HTTPS. It refuses requests from the project owner (you), so the
# MAGIC Lakebase Data API journey calls it as the workshop service principal instead. This cell turns the Data
# MAGIC API on for `production` and gives the service principal read-only access to the `bank` schema. Your
# MAGIC branch inherits both when it's created in the next step.

# COMMAND ----------

try:
    sp_app_id = dbutils.secrets.get("lakebase-workshop", "sp-client-id")
except Exception:
    sp_app_id = None
    print("No lakebase-workshop secret scope, so the Data API setup was skipped. "
          "Every journey except the Lakebase Data API journey works without it.")
if sp_app_id:
    project.enable_data_api(branch="production")
    project.grant_data_api(sp_app_id)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 6. Create your branch
# MAGIC A copy-on-write fork of `production`: no data is copied, the API returns in under a second, and
# MAGIC the endpoint you connect to is `ACTIVE` in about two seconds. It starts with the bank you just
# MAGIC loaded. If the branch already exists, this just confirms it's running.

# COMMAND ----------

import branch
branch.create()

# COMMAND ----------

# MAGIC %md
# MAGIC ## 7. Prove it works

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
# MAGIC the project and branch you just created.
