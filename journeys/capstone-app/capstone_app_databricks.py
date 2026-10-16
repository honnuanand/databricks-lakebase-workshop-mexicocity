# Databricks notebook source
# MAGIC %md-sandbox
# MAGIC <div style="display:flex; align-items:center; gap:10px; padding:8px 16px; background:#F9F7F4; border-bottom:2px solid #E0E0E0; font-family:sans-serif; line-height:1;">
# MAGIC   <span style="display:inline-block; width:12px; height:12px; border-radius:2px; background:#FF3621;"></span>
# MAGIC   <span style="font-weight:bold; color:#0b2026;">Lakebase workshop</span>
# MAGIC   <span style="color:#999;">|</span>
# MAGIC   <span style="color:#5A6F77;">Part 2 · App developers · Journey 6 of 6 · Building a Databricks App on Lakebase</span>
# MAGIC </div>

# COMMAND ----------

# MAGIC %md
# MAGIC # Building a Databricks App on Lakebase
# MAGIC #### Duration: 45 minutes
# MAGIC
# MAGIC *Journey 6 of 6 in the App developers track. The earlier journeys used Lakebase from a notebook. This one puts a real web app in front of your branch.*
# MAGIC
# MAGIC ## Overview
# MAGIC
# MAGIC The fraud team wants a small dashboard: accounts and their status, an account's recent
# MAGIC transactions, a fund's look-through holdings, and a search over case notes. It has to read live data
# MAGIC from Lakebase and run inside Databricks, with no separate server to manage.
# MAGIC
# MAGIC The workshop already includes that app: a FastAPI backend and a single-page UI in this journey's
# MAGIC `app/` folder. In this lab you deploy it to **Databricks Apps** from this notebook, give the app its
# MAGIC own access to your branch, and open it to see it read the bank. You don't write any app code.
# MAGIC
# MAGIC ## Learning objectives
# MAGIC
# MAGIC By the end of this lab, you will be able to:
# MAGIC
# MAGIC 1. **Create a Databricks App** and find the service principal it runs as.
# MAGIC 2. **Give the app access to Lakebase:** project permission plus a Postgres role on your branch.
# MAGIC 3. **Deploy the app from a workspace folder**, passing it which project and branch to serve.
# MAGIC 4. **Explain how an app authenticates to Lakebase** with short-lived credentials, without a password.

# COMMAND ----------

# MAGIC %md
# MAGIC ## Key concepts
# MAGIC
# MAGIC - **Databricks App:** a web app (here FastAPI) that Databricks hosts and runs for you, with its own URL. Only signed-in workspace users can open it.
# MAGIC - **Service principal:** a non-human identity. Each app gets one when it's created, and the app runs as it, so it needs its own permissions, separate from yours.
# MAGIC - **Two layers of access:** a workspace permission on the Lakebase project (`CAN_USE`, so the app can find your branch and get credentials) and a Postgres role on the branch (so the database lets it read the `bank` tables).
# MAGIC - **Deployment:** a snapshot of the app's source folder, started on Databricks compute. Redeploying picks up changes.
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
# MAGIC     You need permission to create Databricks Apps in this workspace, and <code>CAN_MANAGE</code> on the
# MAGIC     Lakebase project (the class setup gives you both). Creating the app and its first deployment take a few minutes.
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
# MAGIC ### A2. Name your app and find its source
# MAGIC
# MAGIC Your app is named after your branch, so every attendee gets their own. Its source is the `app/`
# MAGIC folder next to this notebook in the workspace: `app.yaml` (how to start it), `requirements.txt`, and
# MAGIC `backend/` (the FastAPI code and the UI).

# COMMAND ----------

import os, sys, re, time
sys.path.insert(0, os.path.join(os.getcwd(), "..", "..", "common", "scripts"))
from lakebase import client, branch_name, branch_endpoint
from databricks.sdk.service.apps import App, AppDeployment, EnvVar
from databricks.sdk.service.iam import AccessControlRequest, PermissionLevel
import psycopg

PROJECT = os.environ["LB_PROJECT"]
MINE    = os.environ["LB_BRANCH"]
SCHEMA  = os.environ.get("LB_SCHEMA", "bank")
w = client()

# App names: lowercase letters, digits and hyphens, up to 30 characters.
APP_NAME = re.sub(r"[^a-z0-9-]+", "-", ("bank-dash-" + MINE.removeprefix("u-")).lower())[:30].strip("-")
SOURCE = os.path.join(os.getcwd(), "app")
if not SOURCE.startswith("/Workspace"):
    SOURCE = "/Workspace" + SOURCE

print("app name:   ", APP_NAME)
print("serves:     ", f"project {PROJECT}, branch {MINE}, schema {SCHEMA}")
print("source path:", SOURCE)

# COMMAND ----------

# MAGIC %md-sandbox
# MAGIC **Expected result:** your app name, the project and branch it will serve, and its source path:
# MAGIC
# MAGIC ```
# MAGIC app name:    bank-dash-alex-kim
# MAGIC serves:      project bank, branch u-alex-kim, schema bank
# MAGIC source path: /Workspace/Users/alex.kim@example.com/<folder>/journeys/capstone-app/app
# MAGIC ```
# MAGIC
# MAGIC <div style="border-left:4px solid #FF9800; background:#FFF3E0; padding:12px 16px; border-radius:4px; margin:12px 0; font-family:sans-serif;">
# MAGIC   <strong style="display:block; color:#E65100; margin-bottom:6px;">Troubleshooting</strong>
# MAGIC   <div style="color:#333;">
# MAGIC     <ul style="margin:0; padding-left:20px;">
# MAGIC       <li><code>Missing required env var LB_PROJECT</code> or <code>KeyError: 'LB_PROJECT'</code>: the A1 cells didn't run in this session. Run the three A1 cells, then this one.</li>
# MAGIC     </ul>
# MAGIC   </div>
# MAGIC </div>

# COMMAND ----------

# MAGIC %md
# MAGIC ## B. Create the app

# COMMAND ----------

# MAGIC %md
# MAGIC ### B1. Create the app
# MAGIC
# MAGIC Creating an app reserves its name and URL, starts its compute, and creates the **service principal**
# MAGIC the app will run as. If your app already exists from an earlier run, the cell reuses it.

# COMMAND ----------

try:
    app = w.apps.get(APP_NAME)
    print(f"app {APP_NAME} already exists, reusing it")
except Exception:
    t0 = time.time()
    app = w.apps.create_and_wait(App(name=APP_NAME, description="Lakebase workshop: bank dashboard"))
    print(f"created app {APP_NAME} in {time.time() - t0:.0f}s")

SP = app.service_principal_client_id
print("service principal:", SP)
print("app URL:          ", app.url)

# COMMAND ----------

# MAGIC %md-sandbox
# MAGIC **Expected result:** `created app bank-dash-alex-kim in 135s` on a test run (about two minutes), then the app's service
# MAGIC principal id (a UUID) and its URL, like `https://bank-dash-alex-kim-<workspace id>.aws.databricksapps.com`.
# MAGIC
# MAGIC **What this proves:** the app exists and has its own identity. Nothing can read your data yet: the service principal has no permissions.
# MAGIC
# MAGIC <div style="border-left:4px solid #FF9800; background:#FFF3E0; padding:12px 16px; border-radius:4px; margin:12px 0; font-family:sans-serif;">
# MAGIC   <strong style="display:block; color:#E65100; margin-bottom:6px;">Troubleshooting</strong>
# MAGIC   <div style="color:#333;">
# MAGIC     <ul style="margin:0; padding-left:20px;">
# MAGIC       <li><strong>Permission error:</strong> you can't create apps in this workspace. Ask your instructor.</li>
# MAGIC       <li><strong>Name already taken:</strong> someone else has an app with this name. Set <code>APP_NAME</code> to something unique in A2 and rerun.</li>
# MAGIC     </ul>
# MAGIC   </div>
# MAGIC </div>

# COMMAND ----------

# MAGIC %md
# MAGIC ## C. Give the app access to your branch

# COMMAND ----------

# MAGIC %md
# MAGIC ### C1. Project permission
# MAGIC
# MAGIC The app looks up your branch and asks for a short-lived database credential, both through the
# MAGIC Lakebase API. That needs `CAN_USE` on the project, the least privilege that allows it.

# COMMAND ----------

w.permissions.update("database-projects", PROJECT, access_control_list=[
    AccessControlRequest(service_principal_name=SP, permission_level=PermissionLevel.CAN_USE)])
print(f"granted CAN_USE on project {PROJECT} to the app's service principal")

# COMMAND ----------

# MAGIC %md
# MAGIC **Expected result:** `granted CAN_USE on project bank to the app's service principal`

# COMMAND ----------

# MAGIC %md
# MAGIC ### C2. A Postgres role on your branch
# MAGIC
# MAGIC The database also has to know the app. `databricks_create_role()` creates a Postgres role linked to
# MAGIC the service principal, so it can log in with Databricks credentials; then it gets read access to
# MAGIC the `bank` tables. The SQL that runs on your branch:
# MAGIC
# MAGIC ```sql
# MAGIC CREATE EXTENSION IF NOT EXISTS databricks_auth;
# MAGIC SELECT databricks_create_role('<service principal id>', 'SERVICE_PRINCIPAL');
# MAGIC GRANT USAGE ON SCHEMA bank TO "<service principal id>";
# MAGIC GRANT SELECT ON ALL TABLES IN SCHEMA bank TO "<service principal id>";
# MAGIC ```

# COMMAND ----------

host, eid, _ = branch_endpoint(w, PROJECT, MINE)
cred = w.postgres.generate_database_credential(endpoint=f"{branch_name(PROJECT, MINE)}/endpoints/{eid}")
with psycopg.connect(host=host, port=5432, dbname="databricks_postgres", user=w.current_user.me().user_name,
                     password=cred.token, sslmode="require", autocommit=True) as conn, conn.cursor() as cur:
    cur.execute("CREATE EXTENSION IF NOT EXISTS databricks_auth")
    cur.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", [SP])
    if cur.fetchone():
        print("Postgres role for the app already exists")
    else:
        cur.execute("SELECT databricks_create_role(%s, 'SERVICE_PRINCIPAL')", [SP])
        print("created Postgres role for the app")
    cur.execute(f'GRANT USAGE ON SCHEMA {SCHEMA} TO "{SP}"')
    cur.execute(f'GRANT SELECT ON ALL TABLES IN SCHEMA {SCHEMA} TO "{SP}"')
    print(f"granted read access to schema {SCHEMA}")

# COMMAND ----------

# MAGIC %md
# MAGIC **Expected result:** ```
# MAGIC created Postgres role for the app
# MAGIC granted read access to schema bank
# MAGIC ```
# MAGIC
# MAGIC **What this proves:** access is granted in two places, the workspace and the database, and both are scoped: the app can read your branch's `bank` tables, and nothing else.

# COMMAND ----------

# MAGIC %md
# MAGIC ## D. Deploy the app

# COMMAND ----------

# MAGIC %md
# MAGIC ### D1. Deploy
# MAGIC
# MAGIC Deploying takes a snapshot of the `app/` folder and starts it. The cell passes the project, branch and
# MAGIC schema as environment variables, so the app serves **your** branch.

# COMMAND ----------

t0 = time.time()
dep = w.apps.deploy_and_wait(APP_NAME, AppDeployment(
    source_code_path=SOURCE,
    env_vars=[EnvVar(name="LAKEBASE_PROJECT", value=PROJECT),
              EnvVar(name="LAKEBASE_BRANCH", value=MINE),
              EnvVar(name="LAKEBASE_SCHEMA", value=SCHEMA)]))
print(f"deployment {dep.deployment_id}: {dep.status.state.value} in {time.time() - t0:.0f}s")
print(dep.status.message)

# COMMAND ----------

# MAGIC %md-sandbox
# MAGIC **Expected result:** `deployment ...: SUCCEEDED in 16s` on a test run, then `App started successfully`.
# MAGIC
# MAGIC <div style="border-left:4px solid #1B5162; background:#EEF4F6; padding:12px 16px; border-radius:4px; margin:12px 0; font-family:sans-serif;">
# MAGIC   <strong style="display:block; color:#1B5162; margin-bottom:6px;">See it in the UI (optional)</strong>
# MAGIC   <div style="color:#333;">
# MAGIC     Open <strong>Compute</strong> → <strong>Apps</strong> and select your app. The <strong>Deployments</strong> tab shows this deployment, and <strong>Logs</strong> shows the app starting up.
# MAGIC   </div>
# MAGIC </div>
# MAGIC
# MAGIC <div style="border-left:4px solid #FF9800; background:#FFF3E0; padding:12px 16px; border-radius:4px; margin:12px 0; font-family:sans-serif;">
# MAGIC   <strong style="display:block; color:#E65100; margin-bottom:6px;">Troubleshooting</strong>
# MAGIC   <div style="color:#333;">
# MAGIC     <ul style="margin:0; padding-left:20px;">
# MAGIC       <li><code>FAILED</code>: open the app's <strong>Logs</strong> in the UI. A missing package or a typo in <code>app.yaml</code> shows up there.</li>
# MAGIC     </ul>
# MAGIC   </div>
# MAGIC </div>

# COMMAND ----------

# MAGIC %md
# MAGIC ## E. Open the app

# COMMAND ----------

# MAGIC %md
# MAGIC ### E1. Open the app
# MAGIC
# MAGIC Databricks Apps only accept a signed-in user's browser session (or an OAuth token), so you open the
# MAGIC app in a new browser tab rather than from this notebook. The cell prints the links. The app also has
# MAGIC a small JSON API next to its UI, which is handy for seeing exactly what it reads.

# COMMAND ----------

app = w.apps.get(APP_NAME)
print("app status:", app.app_status.state.value if app.app_status else "?",
      "| compute:", app.compute_status.state.value if app.compute_status else "?")
print()
print("Open in a new browser tab:")
for path, what in [("/", "the dashboard UI"),
                   ("/api/health", "who the app is and which branch it serves"),
                   ("/api/accounts", "every account, read from your branch"),
                   ("/api/accounts/CTA-100240", "one account and its recent transactions"),
                   ("/api/holdings/FUND-GROWTH-A", "a fund's look-through holdings (recursive SQL)"),
                   ("/api/casenotes?q=SPEI", "full-text search over case notes")]:
    print(f"  {app.url}{path}")
    print(f"      {what}")

# COMMAND ----------

# MAGIC %md-sandbox
# MAGIC **Expected result:** `app status: RUNNING | compute: ACTIVE`, then six links. Opened in the browser, a test run returned:
# MAGIC
# MAGIC - `/api/health`: `{"ok":true,"identity":"<the app's service principal id>","project":"bank","branch":"u-yourname","schema":"bank"}`
# MAGIC - `/api/accounts`: the 8 accounts, starting `{"account_id":"CTA-100234","branch_id":"BR-CDMX","line":"Checking",...}`
# MAGIC - `/api/accounts/CTA-100240`: the account with its CLABE (`999180000001002407`) and its recent transactions, including the MXN 38,500 SPEI transfer
# MAGIC - `/api/holdings/FUND-GROWTH-A`: the fund's cash, equity sleeve and Zafiro Software at depth 1, and the sleeve's holdings at depth 2
# MAGIC - `/api/casenotes?q=SPEI`: the two case notes that mention SPEI
# MAGIC
# MAGIC **What this proves:** the app reads your branch as its own identity: `/api/health` shows the service principal, not you, and the data is your bank.
# MAGIC
# MAGIC <div style="border-left:4px solid #FF9800; background:#FFF3E0; padding:12px 16px; border-radius:4px; margin:12px 0; font-family:sans-serif;">
# MAGIC   <strong style="display:block; color:#E65100; margin-bottom:6px;">Troubleshooting</strong>
# MAGIC   <div style="color:#333;">
# MAGIC     <ul style="margin:0; padding-left:20px;">
# MAGIC       <li><strong>An error mentioning <code>permission denied</code> or <code>password authentication failed</code>:</strong> rerun C1 and C2, then reload the page.</li>
# MAGIC       <li><strong><code>503</code> with "has no host yet":</strong> your branch isn't ready. Check it in setup, then reload.</li>
# MAGIC     </ul>
# MAGIC   </div>
# MAGIC </div>

# COMMAND ----------

# MAGIC %md
# MAGIC ## F. Clean up (optional)

# COMMAND ----------

# MAGIC %md
# MAGIC ### F1. Delete the app when you're done
# MAGIC
# MAGIC A running app keeps its compute on. When you're done, delete it: this removes the app, its URL and its
# MAGIC service principal. Remove the `#` in the next cell and run it only when you no longer need the dashboard.

# COMMAND ----------

# w.apps.delete(APP_NAME); print(f"deleted app {APP_NAME}")

# COMMAND ----------

# MAGIC %md
# MAGIC **Expected result:** nothing while the line is commented out; with the `#` removed, `deleted app bank-dash-...`.

# COMMAND ----------

# MAGIC %md-sandbox
# MAGIC ##### Check your understanding
# MAGIC
# MAGIC <details>
# MAGIC <summary><strong>1. Which identity does the app use to read your branch?</strong></summary>
# MAGIC
# MAGIC Its own service principal, created with the app; not yours.
# MAGIC
# MAGIC </details>
# MAGIC
# MAGIC <details>
# MAGIC <summary><strong>2. Which two permissions does the app need?</strong></summary>
# MAGIC
# MAGIC `CAN_USE` on the Lakebase project, and a Postgres role on the branch with read access to `bank`.
# MAGIC
# MAGIC </details>
# MAGIC
# MAGIC <details>
# MAGIC <summary><strong>3. Why is there no password anywhere?</strong></summary>
# MAGIC
# MAGIC The app asks Lakebase for a short-lived credential each time it connects, using its Databricks identity.
# MAGIC
# MAGIC </details>

# COMMAND ----------

# MAGIC %md
# MAGIC ## G. Conclusion
# MAGIC
# MAGIC In this lab you created a Databricks App, gave it access to your branch, deployed it, and opened it.
# MAGIC Key takeaways:
# MAGIC
# MAGIC 1. **An app runs as its own service principal,** so it gets exactly the access you grant it.
# MAGIC 2. **Access has two layers:** `CAN_USE` on the Lakebase project and a Postgres role on the branch.
# MAGIC 3. **No passwords:** the app asks Lakebase for a short-lived credential each time it connects.
# MAGIC 4. **Deploying is one call** from a workspace folder; the same app can serve any branch you point it at.
# MAGIC
# MAGIC That's the end of the App developers track.

# COMMAND ----------

# MAGIC %md
# MAGIC ---
# MAGIC **You've finished the App developers track.**
# MAGIC
# MAGIC <a href="$../../START_HERE">← Back to the table of contents</a>
