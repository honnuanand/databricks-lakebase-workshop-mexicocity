# Databricks notebook source
# MAGIC %md
# MAGIC # Capstone: build a bank dashboard, guided checklist
# MAGIC
# MAGIC This journey walks you through running and deploying a FastAPI app on Databricks Apps that reads from Lakebase. It is a guided checklist notebook: most steps are configuration and setup; code cells show how to grant permissions and verify connectivity.
# MAGIC
# MAGIC **Before you start:** finish `00-setup/` so `LB_PROFILE`, `LB_PROJECT`, `LB_BRANCH`, `LB_SCHEMA` are set and the bank is loaded on your branch. You should also be familiar with `branch-the-brain` or similar journey so you understand Lakebase branching.

# COMMAND ----------

# MAGIC %md
# MAGIC ## The app you are building
# MAGIC
# MAGIC A single-page dashboard deployed on Databricks Apps with a FastAPI backend that queries Lakebase. The UI is a static `index.html` the backend serves directly (no Node, no build step). It has three tabs:
# MAGIC
# MAGIC 1. **Accounts:** list all accounts, fetched via direct SQL.
# MAGIC 2. **Holdings look-through:** explode a fund's holdings tree with a recursive CTE (through sleeves).
# MAGIC 3. **Case notes:** search analyst case notes with full-text search.
# MAGIC
# MAGIC The app lives in `./app/` and is ready to customize. Here we set up permissions, run it locally, and deploy.

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 1, Understand the object model
# MAGIC
# MAGIC A Databricks App is a container that runs your code. It has an auto-created Service Principal (SP). That SP needs to connect to Lakebase to query the bank data.
# MAGIC
# MAGIC Permission chain:
# MAGIC 1. App SP exists (created automatically on first deploy).
# MAGIC 2. Create a PostgreSQL role on Lakebase with the SP's client ID.
# MAGIC 3. Set the `databricks_auth` security label (tells Lakebase to auth as the SP).
# MAGIC 4. Grant project CAN_MANAGE (so the app can list branches).
# MAGIC 5. Create a role on your branch so the app can connect and query.

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 2, Grant the app's Service Principal permissions (before deploy)

# COMMAND ----------

import os, sys
sys.path.insert(0, os.path.join(os.getcwd(), "..", "..", "common", "scripts"))

print("Grant the app SP permissions before first deploy.")
print()
print("Run this command from the journeys/capstone-app/ directory:")
print()
print("  python capstone_grant_sp.py --app-name capstone-dashboard \\")
print("    --lakebase-profile <LB_PROFILE> \\")
print("    --lakebase-project <LB_PROJECT> \\")
print("    --lakebase-schema bank")
print()
print("Replace <LB_PROFILE> and <LB_PROJECT> with your values from 00-setup.")
print()
print("The script:")
print("  1. Looks up the app's Service Principal (by app name).")
print("  2. Creates a PostgreSQL role for the SP.")
print("  3. Sets the databricks_auth security label (auth via OAuth).")
print("  4. Grants project CAN_MANAGE permission (list branches).")
print("  5. Creates a role on your branch (for connections).")
print()
print("If the app does not exist yet (first time), the script notes that and")
print("asks you to re-run it after deploying the app.")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 3, Run the app locally

# COMMAND ----------

print("Run the dashboard on your own machine, against your Lakebase branch:")
print()
print("1. Make sure your workshop env vars are set (from 00-setup):")
print("   export LB_PROFILE=<your-profile>")
print("   export LB_PROJECT=<project-id>")
print("   export LB_BRANCH=<branch-id>")
print("   export LB_SCHEMA=bank")
print()
print("2. From journeys/capstone-app/app/, start it (installs deps on first run):")
print("   bash run_local.sh")
print()
print("   run_local.sh maps LB_* -> LAKEBASE_* and starts uvicorn on port 8000.")
print()
print("3. Open http://localhost:8000 in your browser. The FastAPI backend serves")
print("   the static index.html UI and the /api/* endpoints from one process.")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 4, Test the app locally

# COMMAND ----------

print("Test the app locally before deploying:")
print()
print("1. Go to the Accounts tab. You should see a list of all accounts.")
print("   The backend is making a SQL query:")
print("     SELECT account_id, branch_id, line, type, status, health_pct FROM account")
print()
print("2. Go to the Holdings look-through tab. Enter 'FUND-GROWTH-A' and hit Look through.")
print("   You should see a tree of instruments, including the ones held through a sleeve")
print("   at depth 2 (a recursive CTE walked the holdings tree).")
print()
print("3. Go to the Case notes tab. Search for 'wire'.")
print("   Results should show case notes matching the full-text search.")
print()
print("If a query fails, check:")
print("  - Are environment variables set? (echo $LB_PROFILE, etc.)")
print("  - Is the backend running? (check http://localhost:8000/docs)")
print("  - Did the grant script succeed? (re-run it if not)")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 5, Update app configuration

# COMMAND ----------

print("Before deploying, verify app/app.yaml has your values:")
print()
print("  env:")
print("    LAKEBASE_PROJECT: <project-id>")
print("    LAKEBASE_BRANCH:  <branch the app serves>")
print("    LAKEBASE_SCHEMA:  bank")
print()
print("Note: app.yaml has NO LAKEBASE_PROFILE; on Databricks Apps the runtime injects")
print("the app's Service Principal credentials, so the same code authenticates as the SP.")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 6, Deploy to Databricks Apps

# COMMAND ----------

print("Deploy the app from the journeys/capstone-app/app/ directory:")
print()
print("  bash deploy.sh")
print()
print("Deployment takes 1-2 minutes. Watch the output for errors.")
print()
print("The deploy script packages the FastAPI backend (with its static index.html)")
print("and pushes it to Databricks Apps. There is no separate frontend build step.")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 7, Re-grant the app SP after first deploy

# COMMAND ----------

print("If this is your first deploy, the app was just created with a new Service Principal.")
print()
print("Re-run the grant script to give the SP full permissions:")
print()
print("  python capstone_grant_sp.py --app-name capstone-dashboard \\")
print("    --lakebase-profile <LB_PROFILE> \\")
print("    --lakebase-project <LB_PROJECT> \\")
print("    --lakebase-schema bank")
print()
print("The script is idempotent; re-running is safe.")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 8, Test the deployed app

# COMMAND ----------

print("Log into your Databricks workspace and navigate to Apps.")
print("You should see 'capstone-dashboard'. Click it to open.")
print()
print("Test each tab:")
print("  1. Accounts tab: you should see a list of accounts.")
print("  2. Holdings look-through tab: enter 'FUND-GROWTH-A'.")
print("  3. Case notes tab: search for case notes.")
print()
print("The app is now running on Databricks Apps, querying Lakebase directly.")
print()
print("If the app fails to start or queries return errors:")
print("  - Check that the grant script ran successfully.")
print("  - Verify app.yaml has the correct environment variables.")
print("  - Redeploy: bash deploy.sh")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 9, Make changes and redeploy

# COMMAND ----------

print("After local testing, make a small change in the backend or the static UI:")
print()
print("For example, add a new column to the Accounts table in app/backend/static/index.html,")
print("or add a new /api/ endpoint in app/backend/main.py.")
print()
print("Then redeploy:")
print("  bash deploy.sh")
print()
print("The app updates live. Refresh your browser and see the change.")

# COMMAND ----------

# MAGIC %md
# MAGIC ## What you learned
# MAGIC
# MAGIC You ran and deployed a FastAPI app on Databricks Apps that queries Lakebase directly, serving a single-page dashboard UI from the same process. The app's Service Principal connects to your Lakebase instance using OAuth credentials. You set up permissions at the app, project, schema, and branch levels, which is the same permission model as the production lakebase-pitch app. You ran the app locally, then deployed it in minutes.
# MAGIC
# MAGIC Key takeaways:
# MAGIC
# MAGIC - Databricks Apps handle deployment, scaling, and networking. You just provide code.
# MAGIC - Service Principal auth (SP-auth) is the right choice for app-to-Lakebase calls (vs OBO, which is for user-level queries).
# MAGIC - Grant the app SP permissions before first deploy (or re-grant after deploy if it is the first time).
# MAGIC - A recursive CTE (holdings look-through) and full-text search (case notes) run as plain SQL on Lakebase, no extra services.
# MAGIC - Redeploy with `bash deploy.sh` after making changes.
# MAGIC
# MAGIC For production apps, you would add error handling, monitoring, logging, and role-based feature flags. The capstone-app is your template.

# COMMAND ----------

# MAGIC %md
# MAGIC ---
# MAGIC **You've finished the App developers track.**
# MAGIC
# MAGIC <a href="$../../START_HERE">← Back to the table of contents</a>
