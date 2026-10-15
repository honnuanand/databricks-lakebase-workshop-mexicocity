# Databricks notebook source
# MAGIC %md-sandbox
# MAGIC <div style="display:flex; align-items:center; gap:10px; padding:8px 16px; background:#F9F7F4; border-bottom:2px solid #E0E0E0; font-family:sans-serif; line-height:1;">
# MAGIC   <span style="display:inline-block; width:12px; height:12px; border-radius:2px; background:#FF3621;"></span>
# MAGIC   <span style="font-weight:bold; color:#0b2026;">Lakebase workshop</span>
# MAGIC   <span style="color:#999;">|</span>
# MAGIC   <span style="color:#5A6F77;">Part 1 · Journey 2 of 5 · Point-in-Time Restore</span>
# MAGIC </div>

# COMMAND ----------

# MAGIC %md
# MAGIC # Point-in-Time Restore
# MAGIC #### Duration: about 15 minutes
# MAGIC
# MAGIC *Journey 2 of 5. In Database Branching you forked your branch as it is now. Here you fork it as it was a moment ago.*
# MAGIC
# MAGIC ## Overview
# MAGIC
# MAGIC You're the DBA for the bank's trading platform. Late in the day, someone runs a cleanup query with
# MAGIC the wrong `WHERE` clause, and the whole trade book disappears: no open trades, no pending
# MAGIC settlements. On most databases, that means restoring last night's backup and losing hours.
# MAGIC
# MAGIC On Lakebase, the database's history is kept in storage, so you can create a branch of the database
# MAGIC as it was a moment before the mistake, in seconds. In this lab you make that mistake on your own
# MAGIC branch, on purpose, and get the data back.
# MAGIC
# MAGIC ## Learning objectives
# MAGIC
# MAGIC By the end of this lab, you will be able to:
# MAGIC
# MAGIC 1. **Capture a log position (LSN)** that marks the state of the database before a change.
# MAGIC 2. **Recover deleted data** by creating a branch at that earlier LSN.
# MAGIC 3. **Read the recovered rows** from the recovery branch and confirm they're complete.
# MAGIC 4. **Explain how far back you can restore:** the project's history window, 7 days by default.

# COMMAND ----------

# MAGIC %md
# MAGIC ## Key concepts
# MAGIC
# MAGIC - **Write-ahead log (WAL):** Postgres records every change in a log before applying it. Lakebase keeps that history in its storage.
# MAGIC - **LSN (log sequence number):** a position in the write-ahead log, like a timestamp for the state of the database. `pg_current_wal_lsn()` returns the current one.
# MAGIC - **Point-in-time restore:** creating a branch of the database as it was at an earlier LSN or time.
# MAGIC - **History window:** how far back you can restore. It's set per project; 7 days by default.
# MAGIC - **Recovery branch:** the branch you create at the earlier point. It's separate from your branch, so you can look at the old data before deciding what to do with it.
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
# MAGIC Postgres connection to any branch by name. You'll use it on your branch and on the recovery branch.
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

# MAGIC %md-sandbox
# MAGIC **Expected result:**
# MAGIC
# MAGIC ```
# MAGIC connected as alex.kim@example.com
# MAGIC project=bank, your branch=u-alex-kim, recovery branch will be u-alex-kim-restore
# MAGIC ```
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
# MAGIC ## B. Before the mistake
# MAGIC
# MAGIC Every change to the database is written to the write-ahead log, and every position in that log
# MAGIC has a number, the **LSN** (log sequence number). In this section you look at the data and record
# MAGIC the current LSN. Later you'll create a branch at that LSN to get the data back.
# MAGIC
# MAGIC <div style="max-width:720px; margin:12px auto; font-family:sans-serif;">
# MAGIC <svg viewBox="0 0 720 230" xmlns="http://www.w3.org/2000/svg" style="width:100%; height:auto; display:block;" font-family="sans-serif">
# MAGIC   <rect x="10" y="10" width="700" height="210" rx="10" fill="#F9F7F4" stroke="#E0E0E0"/>
# MAGIC   <text x="30" y="95" font-size="14" font-weight="700" fill="#0b2026">u-yourname</text>
# MAGIC   <line x1="140" y1="90" x2="680" y2="90" stroke="#1B5162" stroke-width="3"/>
# MAGIC   <polygon points="680,84 692,90 680,96" fill="#1B5162"/>
# MAGIC   <text x="686" y="114" text-anchor="end" font-size="12" fill="#5A6F77">time</text>
# MAGIC   <text x="260" y="48" text-anchor="middle" font-size="12" font-weight="700" fill="#0b2026">B2. LSN captured</text>
# MAGIC   <text x="260" y="66" text-anchor="middle" font-size="12" fill="#5A6F77">2 trades</text>
# MAGIC   <circle cx="260" cy="90" r="8" fill="#1B5162"/>
# MAGIC   <text x="470" y="48" text-anchor="middle" font-size="12" font-weight="700" fill="#0b2026">C. DELETE</text>
# MAGIC   <text x="470" y="66" text-anchor="middle" font-size="12" fill="#5A6F77">0 trades</text>
# MAGIC   <circle cx="470" cy="90" r="8" fill="#FF3621"/>
# MAGIC   <path d="M 260 98 L 260 180 L 300 180" fill="none" stroke="#FF3621" stroke-width="2"/>
# MAGIC   <polygon points="300,174 310,180 300,186" fill="#FF3621"/>
# MAGIC   <rect x="312" y="155" width="290" height="50" rx="8" fill="#FFF1EE" stroke="#FF3621" stroke-width="2" stroke-dasharray="6 4"/>
# MAGIC   <text x="457" y="177" text-anchor="middle" font-size="14" font-weight="700" fill="#0b2026">u-yourname-restore</text>
# MAGIC   <text x="457" y="195" text-anchor="middle" font-size="12" fill="#5A6F77">D. created at the captured LSN: 2 trades</text>
# MAGIC </svg>
# MAGIC </div>

# COMMAND ----------

# MAGIC %md
# MAGIC ### B1. Look at the trades
# MAGIC
# MAGIC Confirm the trades exist on your branch. The SQL:
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

# MAGIC %md-sandbox
# MAGIC **Expected result:**
# MAGIC
# MAGIC ```
# MAGIC Trades on your branch (2 total):
# MAGIC   ('TRD-8821', 'FUND-GROWTH-A', 50, 'placed')
# MAGIC   ('TRD-8822', 'FUND-INCOME-B', 120, 'executing')
# MAGIC ```
# MAGIC
# MAGIC **What this proves:** your branch has two trades. Remember them: you'll delete them, then get them back.
# MAGIC
# MAGIC <div style="border-left:4px solid #FF9800; background:#FFF3E0; padding:12px 16px; border-radius:4px; margin:12px 0; font-family:sans-serif;">
# MAGIC   <strong style="display:block; color:#E65100; margin-bottom:6px;">Troubleshooting</strong>
# MAGIC   <div style="color:#333;">
# MAGIC     <ul style="margin:0; padding-left:20px;">
# MAGIC       <li><code>Trades on your branch (0 total)</code>: you already ran this journey, and the trades are still deleted. Run the reset cell in section E, then start again from B1.</li>
# MAGIC       <li><code>NotFound: branch id not found</code>: your branch doesn't exist yet. Run <code>00-setup/setup_databricks</code>, or check the <code>LB_BRANCH</code> widget.</li>
# MAGIC     </ul>
# MAGIC   </div>
# MAGIC </div>

# COMMAND ----------

# MAGIC %md
# MAGIC ### B2. Capture the LSN
# MAGIC
# MAGIC Record the log position now, before the mistake. The SQL:
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
# MAGIC **Expected result:** `LSN captured: 0/1BE6B80` on a test run, then the explanation line. Your LSN
# MAGIC will be a different value in the same format.
# MAGIC
# MAGIC **What this proves:** you now have a marker for "the database before the mistake". D1 needs it, so don't rerun this cell after section C.

# COMMAND ----------

# MAGIC %md-sandbox
# MAGIC ## C. Make the mistake
# MAGIC
# MAGIC <div style="border-left:4px solid #FF3621; background:#FFF1EE; padding:12px 16px; border-radius:4px; margin:12px 0; font-family:sans-serif;">
# MAGIC   <strong style="display:block; color:#C4200F; margin-bottom:6px;">Warning: this deletes data on your branch</strong>
# MAGIC   <div style="color:#333;">
# MAGIC     The next cell deletes every trade and settlement on <strong>your</strong> branch, on purpose.
# MAGIC     It never touches <code>production</code> or anyone else's branch. The rows stay deleted on your
# MAGIC     branch until you run the reset cell in section E.
# MAGIC   </div>
# MAGIC </div>
# MAGIC
# MAGIC The over-broad cleanup. `settlement` rows reference `trade` through a foreign key, so the
# MAGIC settlements go first:
# MAGIC
# MAGIC ```sql
# MAGIC DELETE FROM bank.settlement;
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
# MAGIC **Expected result:**
# MAGIC
# MAGIC ```
# MAGIC Delete complete. Trades remaining: 0, settlements remaining: 0
# MAGIC All trades and their settlements have been deleted from your branch.
# MAGIC ```
# MAGIC
# MAGIC **What this proves:** the mistake is real. Your branch has no trades or settlements left.

# COMMAND ----------

# MAGIC %md
# MAGIC ## D. Recover with point-in-time restore
# MAGIC
# MAGIC ### D1. Create a branch at the captured LSN
# MAGIC
# MAGIC Create a recovery branch from your branch, but as it was at the LSN you captured in B2. This is a
# MAGIC control-plane operation, so it uses the SDK. The cell first deletes any recovery branch left over
# MAGIC from an earlier run. The key call:
# MAGIC
# MAGIC ```python
# MAGIC w.postgres.create_branch(
# MAGIC     parent=f"projects/{PROJECT}",
# MAGIC     branch=Branch(spec=BranchSpec(
# MAGIC         source_branch=branch_name(PROJECT, MINE),
# MAGIC         source_branch_lsn=lsn,
# MAGIC         no_expiry=True)),
# MAGIC     branch_id=RESTORE)
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

# MAGIC %md-sandbox
# MAGIC **Expected result** (from a test run; your numbers will vary a little):
# MAGIC
# MAGIC ```
# MAGIC PITR branch u-yourname-restore created
# MAGIC   create_branch API returned in 436 ms
# MAGIC   endpoint reached ACTIVE in ~1.9s
# MAGIC ```
# MAGIC
# MAGIC **What this proves:** going back in time is just creating a branch at an earlier LSN, so it takes
# MAGIC about as long as creating any other branch.
# MAGIC
# MAGIC <div style="border-left:4px solid #1B5162; background:#EEF4F6; padding:12px 16px; border-radius:4px; margin:12px 0; font-family:sans-serif;">
# MAGIC   <strong style="display:block; color:#1B5162; margin-bottom:6px;">See it in the UI (optional)</strong>
# MAGIC   <div style="color:#333;">
# MAGIC     In the <strong>Lakebase Postgres</strong> app, open your project. The <strong>Branches</strong> tab lists
# MAGIC     <code>u-yourname-restore</code>, and the <strong>Backup &amp; Restore</strong> tab is where you can do the
# MAGIC     same restore without code, picking a point in time instead of an LSN.
# MAGIC   </div>
# MAGIC </div>
# MAGIC
# MAGIC <div style="border-left:4px solid #FF9800; background:#FFF3E0; padding:12px 16px; border-radius:4px; margin:12px 0; font-family:sans-serif;">
# MAGIC   <strong style="display:block; color:#E65100; margin-bottom:6px;">Troubleshooting</strong>
# MAGIC   <div style="color:#333;">
# MAGIC     <ul style="margin:0; padding-left:20px;">
# MAGIC       <li><strong>Permission error:</strong> creating a branch needs <code>CAN_MANAGE</code> on the project. Ask your instructor to grant it.</li>
# MAGIC       <li><code>TimeoutError: branch ... not ACTIVE within 30s</code>: the first branch of a session can be slower. Run the cell again.</li>
# MAGIC       <li><code>NameError: name 'lsn' is not defined</code>: the notebook restarted after B2, so the LSN from before the delete is lost. Don't rerun B2: it would capture a point <em>after</em> the delete. Restore by time instead, from the <strong>Backup &amp; Restore</strong> tab, or run the reset cell in section E and start again from B1.</li>
# MAGIC     </ul>
# MAGIC   </div>
# MAGIC </div>

# COMMAND ----------

# MAGIC %md
# MAGIC ### D2. Read the recovered trades
# MAGIC
# MAGIC The recovery branch holds the database as it was before the DELETE, so the trades are there. The
# MAGIC same query as B1, on the recovery branch:
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
# MAGIC **Expected result:**
# MAGIC
# MAGIC ```
# MAGIC Recovered trades from PITR branch (2 total):
# MAGIC   ('TRD-8821', 'FUND-GROWTH-A', 50, 'placed')
# MAGIC   ('TRD-8822', 'FUND-INCOME-B', 120, 'executing')
# MAGIC
# MAGIC The deleted data is intact. Every byte is as it was before the mistake.
# MAGIC ```
# MAGIC
# MAGIC **What this proves:** these are the same two trades as in B1, read from a branch created after
# MAGIC they were deleted. The recovery branch holds your whole database as it was at the LSN from B2.

# COMMAND ----------

# MAGIC %md
# MAGIC ### D3. Getting the data back onto your branch
# MAGIC
# MAGIC This journey stops at reading the recovered rows. In practice you'd choose one of two ways to get
# MAGIC them back:
# MAGIC
# MAGIC - **Copy the rows back.** Read them from the recovery branch and insert them into your branch, for
# MAGIC   example with a script that opens a connection to each branch, as D2 does. Use this when only some
# MAGIC   data was lost and the rest of your branch has moved on since the mistake.
# MAGIC - **Switch to the recovery branch.** Point your application at the recovery branch and treat it as
# MAGIC   the new working branch. Use this when everything written after the mistake can be discarded.
# MAGIC
# MAGIC Either way, check the recovered data first. That's why the recovery branch is separate.

# COMMAND ----------

# MAGIC %md-sandbox
# MAGIC ##### EXPAND FOR ADDITIONAL NOTES
# MAGIC
# MAGIC <details>
# MAGIC <summary><strong>How this differs from a traditional Postgres restore, and how far back you can go</strong></summary>
# MAGIC
# MAGIC On a traditional Postgres, point-in-time recovery means restoring a base backup onto a new server
# MAGIC and replaying the write-ahead log up to the moment you want. That takes minutes to hours, depending
# MAGIC on the size of the database and how old the backup is.
# MAGIC
# MAGIC Lakebase keeps the history in its storage layer, so restoring is creating a copy-on-write branch at
# MAGIC an earlier LSN: no backup to copy and nothing to replay. It takes the same couple of seconds as any
# MAGIC branch.
# MAGIC
# MAGIC How far back you can go is set by the project's **history window** (project **Settings** in the
# MAGIC Lakebase Postgres app). The workshop's project uses the default, 7 days.
# MAGIC
# MAGIC </details>

# COMMAND ----------

# MAGIC %md
# MAGIC ## E. Clean up
# MAGIC
# MAGIC ### E1. Delete the recovery branch
# MAGIC
# MAGIC You've seen the recovered data, so delete the recovery branch. Deleting it doesn't affect your
# MAGIC branch.

# COMMAND ----------

w.postgres.update_branch(name=branch_name(PROJECT, RESTORE),
    branch=Branch(spec=BranchSpec(is_protected=False)), update_mask=FieldMask(field_mask=['spec.is_protected']))
w.postgres.delete_branch(name=branch_name(PROJECT, RESTORE))
print(f"Discarded {RESTORE}")
print("\nRecovery complete. The PITR branch is gone and left no storage behind. Your branch still has the trades deleted.")

# COMMAND ----------

# MAGIC %md
# MAGIC **Expected result:**
# MAGIC
# MAGIC ```
# MAGIC Discarded u-yourname-restore
# MAGIC
# MAGIC Recovery complete. The PITR branch is gone and left no storage behind. Your branch still has the trades deleted.
# MAGIC ```

# COMMAND ----------

# MAGIC %md
# MAGIC ### E2. Rebuild your branch
# MAGIC
# MAGIC **Your branch still has no trades.** You read the recovered rows from the recovery branch; you
# MAGIC didn't copy them back. The next cell rebuilds your branch so the next journeys start with a
# MAGIC complete bank: it deletes your branch, creates it again from `production`, and reloads the bank.
# MAGIC It touches only your branch.

# COMMAND ----------

import branch
branch.reset()

# COMMAND ----------

# MAGIC %md
# MAGIC **Expected result:** `deleted branch u-yourname`, the new branch going `ACTIVE`, then
# MAGIC `Loading schema ...`, `Seeding data ...`, and row counts that include `trade 2 rows` and
# MAGIC `settlement 3 rows`. It takes about 15 seconds.

# COMMAND ----------

# MAGIC %md-sandbox
# MAGIC ##### Check your understanding
# MAGIC
# MAGIC <details>
# MAGIC <summary><strong>1. Why did you capture the LSN before the DELETE, not after?</strong></summary>
# MAGIC
# MAGIC The recovery branch is created at that LSN. An LSN from after the DELETE would give you a copy without the trades.
# MAGIC
# MAGIC </details>
# MAGIC
# MAGIC <details>
# MAGIC <summary><strong>2. After this journey, does your own branch have the trades?</strong></summary>
# MAGIC
# MAGIC Not until E2. You only read the trades from the recovery branch; the reset in E2 rebuilds your branch with a fresh bank.
# MAGIC
# MAGIC </details>
# MAGIC
# MAGIC <details>
# MAGIC <summary><strong>3. Could you restore to a moment from two weeks ago?</strong></summary>
# MAGIC
# MAGIC Not with the default settings: the history window is 7 days. It's a project setting.
# MAGIC
# MAGIC </details>

# COMMAND ----------

# MAGIC %md
# MAGIC ## F. Conclusion
# MAGIC
# MAGIC In this lab you deleted live data, created a branch at an LSN from before the delete, and read
# MAGIC every row back. Key takeaways:
# MAGIC
# MAGIC 1. **Point-in-time restore is branching at an earlier LSN,** the same copy-on-write mechanism as
# MAGIC    the last journey.
# MAGIC 2. **It takes seconds,** with no backup to restore and no log to replay.
# MAGIC 3. **The recovery branch is separate from your branch,** so you can inspect the old data before
# MAGIC    deciding what to copy back.
# MAGIC 4. **How far back you can go** is the project's history window, 7 days by default, set in project
# MAGIC    Settings.
# MAGIC
# MAGIC The next journey looks at the same data from the analytics side: one copy of the data, used both
# MAGIC for operations and for analytics.

# COMMAND ----------

# MAGIC %md
# MAGIC ---
# MAGIC **Next in Part 1:** <a href="$../write-to-analytics/write_to_analytics_databricks">Lakebase Data in the Lakehouse →</a>
# MAGIC
# MAGIC <a href="$../../START_HERE">← Back to the table of contents</a>
