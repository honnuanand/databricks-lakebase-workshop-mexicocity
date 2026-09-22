# Databricks notebook source
# MAGIC %md
# MAGIC # Capstone: build a manufacturing dashboard, guided checklist
# MAGIC
# MAGIC This journey walks you through building and deploying a React+FastAPI app on Databricks Apps that reads from Lakebase. It is a guided checklist notebook: most steps are configuration and setup; code cells show how to grant permissions and verify connectivity.
# MAGIC
# MAGIC **Before you start:** finish `00-setup/` so `LB_PROFILE`, `LB_PROJECT`, `LB_BRANCH`, `LB_SCHEMA` are set and the factory is loaded on your branch. You should also be familiar with `branch-the-brain` or similar journey so you understand Lakebase branching.

# COMMAND ----------

# MAGIC %md
# MAGIC ## The app you are building
# MAGIC
# MAGIC A React dashboard deployed on Databricks Apps with a FastAPI backend that queries Lakebase. It has three tabs:
# MAGIC
# MAGIC 1. **Machines:** list all machines, fetch via direct SQL.
# MAGIC 2. **BOM search:** search for products and see their part trees.
# MAGIC 3. **Maintenance logs:** search maintenance records with full-text search.
# MAGIC
# MAGIC The app lives in `../../common/capstone-app/` and is ready to customize. Here we set up permissions, develop locally, and deploy.

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 1, Understand the object model
# MAGIC
# MAGIC A Databricks App is a container that runs your code. It has an auto-created Service Principal (SP). That SP needs to connect to Lakebase to query the factory data.
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
print("    --lakebase-schema factory")
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
# MAGIC ## Step 3, Set up local environment

# COMMAND ----------

print("Set up your local development environment:")
print()
print("1. Navigate to the app folder:")
print("   cd ../../common/capstone-app")
print()
print("2. Install backend dependencies:")
print("   cd backend && pip install -r requirements.txt")
print()
print("3. Install frontend dependencies:")
print("   cd ../frontend && npm install")
print()
print("4. Set environment variables (from 00-setup):")
print("   export LB_PROFILE=<your-profile>")
print("   export LB_PROJECT=<project-id>")
print("   export LB_BRANCH=<branch-id>")
print("   export LB_SCHEMA=factory")
print()
print("5. Start the backend (from backend/ directory):")
print("   python -m uvicorn main:app --reload --port 8000")
print()
print("6. In another terminal, start the frontend (from frontend/ directory):")
print("   npm start")
print()
print("7. Open http://localhost:3000 in your browser.")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 4, Test the app locally

# COMMAND ----------

print("Test the app locally before deploying:")
print()
print("1. Go to the Machines tab. You should see a list of all machines.")
print("   The backend is making a SQL query:")
print("     SELECT machine_id, status, health_pct FROM factory.machine")
print()
print("2. Click a machine to see its details.")
print()
print("3. Go to the BOM tab. Search for 'PRD-GEARBOX' and hit Enter.")
print("   You should see a tree of parts.")
print()
print("4. Go to the Maintenance tab. Search for 'bearing'.")
print("   Results should show maintenance logs matching the search.")
print()
print("If a query fails, check:")
print("  - Are environment variables set? (echo $LB_PROFILE, etc.)")
print("  - Is the backend running? (check http://localhost:8000/docs)")
print("  - Did the grant script succeed? (re-run it if not)")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 5, Update app configuration

# COMMAND ----------

print("Before deploying, update app.yaml with your workspace details:")
print()
print("Open ../../common/capstone-app/app.yaml and set:")
print()
print("  name: capstone-dashboard")
print("  host: <workspace-host>  # e.g., my-workspace.cloud.databricks.com")
print()
print("Also verify the environment variables match your setup:")
print()
print("  env:")
print("    LAKEBASE_PROFILE: <your-profile>")
print("    LAKEBASE_PROJECT: <project-id>")
print("    LAKEBASE_SCHEMA: factory")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 6, Deploy to Databricks Apps

# COMMAND ----------

print("Deploy the app from the capstone-app/ directory:")
print()
print("Option 1 (recommended): use the deploy script:")
print("  bash deploy.sh")
print()
print("Option 2 (manual): use deploy_to_databricks.py:")
print("  cd backend")
print("  python deploy_to_databricks.py --app-name capstone-dashboard --skip-secrets")
print()
print("Deployment takes 1-2 minutes. Watch the output for errors.")
print()
print("The deploy script:")
print("  1. Builds the React frontend (npm run build).")
print("  2. Packages the FastAPI backend with the built frontend.")
print("  3. Pushes to Databricks Apps.")

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
print("    --lakebase-schema factory")
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
print("  1. Machines tab: you should see a list of machines.")
print("  2. BOM tab: search for a product (e.g., 'PRD-GEARBOX').")
print("  3. Maintenance tab: search for maintenance logs.")
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

print("After local testing, make a small change in the frontend or backend:")
print()
print("For example, add a new column to the machines table in frontend/src/Machines.tsx.")
print()
print("Then redeploy:")
print("  bash deploy.sh")
print()
print("The app updates live. Refresh your browser and see the change.")

# COMMAND ----------

# MAGIC %md
# MAGIC ## What you learned
# MAGIC
# MAGIC You built a full-stack app (React + FastAPI) on Databricks Apps that queries Lakebase directly. The app's Service Principal connects to your Lakebase instance using OAuth credentials. You set up permissions at the app, project, schema, and branch levels, which is the same permission model as the production lakebase-pitch app. You deployed the app, iterated locally, and pushed changes live in minutes.
# MAGIC
# MAGIC Key takeaways:
# MAGIC
# MAGIC - Databricks Apps handle deployment, scaling, and networking. You just provide code.
# MAGIC - Service Principal auth (SP-auth) is the right choice for app-to-Lakebase calls (vs OBO, which is for user-level queries).
# MAGIC - Grant the app SP permissions before first deploy (or re-grant after deploy if it is the first time).
# MAGIC - Redeploy with `bash deploy.sh` after making changes.
# MAGIC
# MAGIC For production apps, you would add error handling, monitoring, logging, and role-based feature flags. The capstone-app is your template.
