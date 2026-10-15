# Databricks notebook source
# MAGIC %md-sandbox
# MAGIC <div style="display:flex; align-items:center; gap:10px; padding:8px 16px; background:#F9F7F4; border-bottom:2px solid #E0E0E0; font-family:sans-serif; line-height:1;">
# MAGIC   <span style="display:inline-block; width:12px; height:12px; border-radius:2px; background:#FF3621;"></span>
# MAGIC   <span style="font-weight:bold; color:#0b2026;">Lakebase workshop</span>
# MAGIC   <span style="color:#999;">|</span>
# MAGIC   <span style="color:#5A6F77;">Part 1 · Journey 1 of 5 · Database Branching</span>
# MAGIC </div>

# COMMAND ----------

# MAGIC %md
# MAGIC # Database Branching
# MAGIC #### Duration: about 15 minutes
# MAGIC
# MAGIC *Journey 1 of 5. Everything in Part 1 runs on your own branch of the bank database, the one you created in setup.*
# MAGIC
# MAGIC ## Overview
# MAGIC
# MAGIC Production says account `ACCT-100240`, a retail credit account, is on `watch` and still open for
# MAGIC spending. An overnight transaction scored high for fraud, and a fraud analyst wants to freeze the
# MAGIC account to see how the downstream flows react. Freezing a live customer account to run an
# MAGIC experiment is exactly the kind of change that pages someone at 2 a.m.
# MAGIC
# MAGIC Instead, you fork the whole database into a branch, freeze the account there, and throw the branch
# MAGIC away when you're done. The customer never sees it. Each step uses the real interface: SQL when the
# MAGIC step is a query, the Databricks SDK when it's a control-plane action like creating a branch.
# MAGIC
# MAGIC ## Learning objectives
# MAGIC
# MAGIC By the end of this lab, you will be able to:
# MAGIC
# MAGIC 1. **Fork a live Lakebase database** into a new branch, and measure how long it takes to be ready.
# MAGIC 2. **Change data on the fork** and show that the branch you forked from is unchanged.
# MAGIC 3. **Delete the fork** and confirm nothing is left behind.
# MAGIC 4. **Explain why branching is fast and nearly free:** storage is copy-on-write, so no data is copied.

# COMMAND ----------

# MAGIC %md
# MAGIC ## Key concepts
# MAGIC
# MAGIC - **Branch:** a full, independent copy of a database inside a Lakebase project, like a git branch for data. `production` is the shared original; `u-yourname` is yours.
# MAGIC - **Copy-on-write:** a new branch shares its parent's stored data and writes only the pages you change. That's why a branch can be created without copying any data.
# MAGIC - **Endpoint (compute):** the running Postgres server you connect to. A branch holds the data; its endpoint runs your queries. Each branch has its own endpoint.
# MAGIC - **Control plane vs SQL:** creating, listing, and deleting branches are management actions, done through the Lakebase API (here, with the Databricks SDK). Reading and changing data is done with SQL.
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
# MAGIC ### A2. Connect to your branch
# MAGIC
# MAGIC This loads the shared helper from `common/scripts/` and defines `connect_branch()`, which opens a
# MAGIC Postgres connection to any branch by name. You'll use it to read both your branch and the fork.
# MAGIC
# MAGIC Under the hood, `connect_branch()` asks the Lakebase API for the branch's host name, gets a login
# MAGIC token from your Databricks identity (valid for about an hour), and opens a standard Postgres
# MAGIC connection with `psycopg`, a Postgres driver for Python.
# MAGIC
# MAGIC In the steps below, the SQL block in each step is the statement that runs on the branch. The Python
# MAGIC cell under it only sends that statement and prints the result.

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

# MAGIC %md-sandbox
# MAGIC ## B. Fork your branch
# MAGIC
# MAGIC Your branch, `u-yourname`, was forked from the shared `production` branch during setup. In this
# MAGIC section you fork **your** branch into a short-lived experiment branch, `u-yourname-exp`.
# MAGIC
# MAGIC <div style="max-width:720px; margin:12px auto; font-family:sans-serif;">
# MAGIC <svg viewBox="0 0 720 230" xmlns="http://www.w3.org/2000/svg" style="width:100%; height:auto; display:block;" font-family="sans-serif">
# MAGIC   <rect x="10" y="10" width="700" height="210" rx="10" fill="#F9F7F4" stroke="#E0E0E0"/>
# MAGIC   <text x="30" y="38" font-size="15" font-weight="700" fill="#0b2026">Project: bank</text>
# MAGIC   <rect x="40" y="60" width="190" height="56" rx="8" fill="#FFFFFF" stroke="#1B5162" stroke-width="2"/>
# MAGIC   <text x="135" y="84" text-anchor="middle" font-size="14" font-weight="700" fill="#0b2026">production</text>
# MAGIC   <text x="135" y="104" text-anchor="middle" font-size="12" fill="#5A6F77">shared, never touched</text>
# MAGIC   <rect x="280" y="60" width="190" height="56" rx="8" fill="#FFFFFF" stroke="#1B5162" stroke-width="2"/>
# MAGIC   <text x="375" y="84" text-anchor="middle" font-size="14" font-weight="700" fill="#0b2026">u-yourname</text>
# MAGIC   <text x="375" y="104" text-anchor="middle" font-size="12" fill="#5A6F77">your branch, from setup</text>
# MAGIC   <rect x="280" y="146" width="190" height="56" rx="8" fill="#FFF1EE" stroke="#FF3621" stroke-width="2" stroke-dasharray="6 4"/>
# MAGIC   <text x="375" y="170" text-anchor="middle" font-size="14" font-weight="700" fill="#0b2026">u-yourname-exp</text>
# MAGIC   <text x="375" y="190" text-anchor="middle" font-size="12" fill="#5A6F77">the fork: create, change, delete</text>
# MAGIC   <line x1="230" y1="88" x2="272" y2="88" stroke="#1B5162" stroke-width="2"/>
# MAGIC   <polygon points="272,82 282,88 272,94" fill="#1B5162"/>
# MAGIC   <line x1="375" y1="116" x2="375" y2="138" stroke="#FF3621" stroke-width="2"/>
# MAGIC   <polygon points="369,138 375,148 381,138" fill="#FF3621"/>
# MAGIC   <text x="500" y="84" font-size="12" fill="#5A6F77">fork = copy-on-write:</text>
# MAGIC   <text x="500" y="102" font-size="12" fill="#5A6F77">no data is copied, only</text>
# MAGIC   <text x="500" y="120" font-size="12" fill="#5A6F77">pages you change are written</text>
# MAGIC </svg>
# MAGIC </div>

# COMMAND ----------

# MAGIC %md
# MAGIC ### B1. Look at ACCT-100240 on your branch
# MAGIC
# MAGIC `ACCT-100240` is a retail credit account at the New York Midtown branch, one of the accounts you
# MAGIC loaded in setup. This is a plain query, the same SQL you could run in any Postgres tool:
# MAGIC
# MAGIC ```sql
# MAGIC SELECT account_id, status, health_pct FROM bank.account WHERE account_id = 'ACCT-100240';
# MAGIC ```

# COMMAND ----------

with connect_branch(MINE) as c, c.cursor() as cur:
    cur.execute("SELECT account_id, status, health_pct FROM account WHERE account_id=%s", [ACCOUNT])
    print("your branch, before:", cur.fetchone())

# COMMAND ----------

# MAGIC %md-sandbox
# MAGIC **Expected result:** `your branch, before: ('ACCT-100240', 'watch', Decimal('91.00'))`
# MAGIC
# MAGIC **What this proves:** your branch has the bank you loaded in setup. This is what you'll compare the fork against.
# MAGIC
# MAGIC <div style="border-left:4px solid #FF9800; background:#FFF3E0; padding:12px 16px; border-radius:4px; margin:12px 0; font-family:sans-serif;">
# MAGIC   <strong style="display:block; color:#E65100; margin-bottom:6px;">Troubleshooting</strong>
# MAGIC   <div style="color:#333;">
# MAGIC     <ul style="margin:0; padding-left:20px;">
# MAGIC       <li><code>NotFound: branch id not found</code>: your branch doesn't exist yet. Run <code>00-setup/setup_databricks</code>, or check the <code>LB_BRANCH</code> widget.</li>
# MAGIC       <li><code>None</code> instead of a row, or <code>relation "account" does not exist</code>: the bank isn't loaded on your branch. Rerun <code>00-setup/setup_databricks</code>.</li>
# MAGIC     </ul>
# MAGIC   </div>
# MAGIC </div>

# COMMAND ----------

# MAGIC %md
# MAGIC ### B2. Create the fork
# MAGIC
# MAGIC Creating a branch is a control-plane operation, not SQL, so this step uses the SDK. The cell first
# MAGIC deletes any fork left over from an earlier run, then creates a new one and times how long it takes
# MAGIC to be ready. The same call from a terminal:
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

# MAGIC %md-sandbox
# MAGIC **Expected result:** `fork API 554 ms; endpoint ACTIVE in ~1.9s` on a test run. Your numbers will vary a little.
# MAGIC
# MAGIC **What this proves:** a complete copy of your database is ready to query in about two seconds, without copying any data.
# MAGIC
# MAGIC <div style="border-left:4px solid #1B5162; background:#EEF4F6; padding:12px 16px; border-radius:4px; margin:12px 0; font-family:sans-serif;">
# MAGIC   <strong style="display:block; color:#1B5162; margin-bottom:6px;">See it in the UI (optional)</strong>
# MAGIC   <div style="color:#333;">
# MAGIC     Open the <strong>Lakebase Postgres</strong> app, select your project, then the <strong>Branches</strong> tab.
# MAGIC     The fork, <code>u-yourname-exp</code>, is listed with your branch as its parent.
# MAGIC   </div>
# MAGIC </div>
# MAGIC
# MAGIC <div style="border-left:4px solid #FF9800; background:#FFF3E0; padding:12px 16px; border-radius:4px; margin:12px 0; font-family:sans-serif;">
# MAGIC   <strong style="display:block; color:#E65100; margin-bottom:6px;">Troubleshooting</strong>
# MAGIC   <div style="color:#333;">
# MAGIC     <ul style="margin:0; padding-left:20px;">
# MAGIC       <li><strong>Permission error:</strong> creating a branch needs <code>CAN_MANAGE</code> on the project. Ask your instructor to grant it.</li>
# MAGIC       <li><code>TimeoutError: branch ... not ACTIVE within 30s</code>: the first branch of a session can be slower. Run the cell again.</li>
# MAGIC     </ul>
# MAGIC   </div>
# MAGIC </div>

# COMMAND ----------

# MAGIC %md-sandbox
# MAGIC ##### EXPAND FOR ADDITIONAL NOTES
# MAGIC
# MAGIC <details>
# MAGIC <summary><strong>Why the fork is ready in seconds, and what the two numbers mean</strong></summary>
# MAGIC
# MAGIC A Lakebase branch is copy-on-write. Creating one doesn't copy your data: the new branch shares the
# MAGIC storage of the branch it came from, as of that moment, and only pages you change on the fork are
# MAGIC written separately. So the time to create a fork doesn't depend on how big the database is.
# MAGIC
# MAGIC The cell prints two numbers. The **API time**, well under a second, is Lakebase accepting the new
# MAGIC branch. The **ACTIVE time**, about two seconds, includes starting the compute endpoint you connect
# MAGIC to. If you hear "sub-500 ms branching", that's the first number alone, not a database you can query.
# MAGIC
# MAGIC </details>

# COMMAND ----------

# MAGIC %md
# MAGIC ## C. Freeze the account on the fork and compare
# MAGIC
# MAGIC Freeze `ACCT-100240` on the fork only, then read it from both branches. The SQL that runs on the
# MAGIC fork:
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

# MAGIC %md-sandbox
# MAGIC **Expected result:**
# MAGIC
# MAGIC ```
# MAGIC fork, after change: ('ACCT-100240', 'frozen', Decimal('70.00'))
# MAGIC your branch, still:  ('ACCT-100240', 'watch', Decimal('91.00'))
# MAGIC ```
# MAGIC
# MAGIC Two live databases, one forked from the other a minute ago, now hold different facts about the
# MAGIC same account.
# MAGIC
# MAGIC **What this proves:** a change on a branch stays on that branch. Your branch, and `production` behind it, never saw the freeze.
# MAGIC
# MAGIC <div style="border-left:4px solid #1B5162; background:#EEF4F6; padding:12px 16px; border-radius:4px; margin:12px 0; font-family:sans-serif;">
# MAGIC   <strong style="display:block; color:#1B5162; margin-bottom:6px;">A note for regulated data</strong>
# MAGIC   <div style="color:#333;">
# MAGIC     A branch of production is a full copy of production's data, customer data included. Treat it
# MAGIC     with the same access controls as production, and delete forks when the experiment is done.
# MAGIC   </div>
# MAGIC </div>

# COMMAND ----------

# MAGIC %md
# MAGIC ## D. Delete the fork
# MAGIC
# MAGIC Deleting the fork removes it and its endpoint. Your branch is unaffected, because the fork only ever
# MAGIC wrote its own changed pages.

# COMMAND ----------

w.postgres.update_branch(name=branch_name(PROJECT, EXP),
    branch=Branch(spec=BranchSpec(is_protected=False)), update_mask=FieldMask(field_mask=['spec.is_protected']))
w.postgres.delete_branch(name=branch_name(PROJECT, EXP))
print("discarded", EXP)
print("branches now:", [b.branch_id for b in w.postgres.list_branches(parent=f"projects/{PROJECT}")])

# COMMAND ----------

# MAGIC %md
# MAGIC **Expected result:** `discarded u-yourname-exp`, then a branch list that includes `production` and
# MAGIC your branch but not the fork. On a shared class project, the list also shows the other attendees'
# MAGIC branches.
# MAGIC
# MAGIC **What this proves:** the experiment is gone, and your branch is still there, unchanged.

# COMMAND ----------

# MAGIC %md-sandbox
# MAGIC ##### Check your understanding
# MAGIC
# MAGIC <details>
# MAGIC <summary><strong>1. You froze `ACCT-100240` on the fork. Why did your branch still show `watch`?</strong></summary>
# MAGIC
# MAGIC A branch is an independent copy. The fork wrote the change to its own pages, so your branch never saw it.
# MAGIC
# MAGIC </details>
# MAGIC
# MAGIC <details>
# MAGIC <summary><strong>2. Why was the fork ready in about two seconds, even though it's a full copy?</strong></summary>
# MAGIC
# MAGIC Copy-on-write: creating the branch copies no data. Most of the time is starting the fork's endpoint.
# MAGIC
# MAGIC </details>
# MAGIC
# MAGIC <details>
# MAGIC <summary><strong>3. Creating the fork used the SDK, but reading the account used SQL. Why?</strong></summary>
# MAGIC
# MAGIC Branches are managed through the Lakebase API (the control plane). Data is read and changed with SQL.
# MAGIC
# MAGIC </details>

# COMMAND ----------

# MAGIC %md
# MAGIC ## E. Conclusion
# MAGIC
# MAGIC In this lab you forked a live database, froze an account on the fork, showed your branch was
# MAGIC unchanged, and deleted the fork. Key takeaways:
# MAGIC
# MAGIC 1. **A branch is a full, isolated copy of the database** that costs almost nothing to create,
# MAGIC    because storage is copy-on-write.
# MAGIC 2. **It's ready in seconds:** the API returns in under a second, and the endpoint is ACTIVE in
# MAGIC    about two.
# MAGIC 3. **Changes on a branch never reach its parent,** and deleting a branch doesn't affect its parent.
# MAGIC 4. **Use branches the way you use git branches:** one per experiment, per pull request, or per
# MAGIC    what-if, instead of a database copy you avoid making.
# MAGIC
# MAGIC The next journey uses the same mechanism on the past: point-in-time restore is creating a branch
# MAGIC from an earlier moment.

# COMMAND ----------

# MAGIC %md
# MAGIC ---
# MAGIC **Next in Part 1:** <a href="$../break-and-rewind/break_and_rewind_databricks">Point-in-Time Restore →</a>
# MAGIC
# MAGIC <a href="$../../START_HERE">← Back to the table of contents</a>
