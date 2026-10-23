# Databricks notebook source
# MAGIC %md-sandbox
# MAGIC <div style="display:flex; align-items:center; gap:10px; padding:8px 16px; background:#F9F7F4; border-bottom:2px solid #E0E0E0; font-family:sans-serif; line-height:1;">
# MAGIC   <span style="display:inline-block; width:12px; height:12px; border-radius:2px; background:#FF3621;"></span>
# MAGIC   <span style="font-weight:bold; color:#0b2026;">Lakebase workshop</span>
# MAGIC   <span style="color:#999;">|</span>
# MAGIC   <span style="color:#5A6F77;">Part 2 · App developers · Journey 4 of 6 · Preventing Overlapping Schedules</span>
# MAGIC </div>

# COMMAND ----------

# MAGIC %md
# MAGIC # Preventing Overlapping Schedules
# MAGIC #### Duration: 20 minutes
# MAGIC
# MAGIC *Journey 4 of 6 in the App developers track. Search read data; this journey has the database refuse data that breaks a rule.*
# MAGIC
# MAGIC ## Overview
# MAGIC
# MAGIC Each settlement leg books a time window on an account, and two windows on the same account must never
# MAGIC overlap. With many requests racing to book, checking in application code ("is the slot free?" then
# MAGIC "book it") leaves a gap where two requests both see the slot as free.
# MAGIC
# MAGIC Postgres can enforce the rule itself with an **exclusion constraint**: the database rejects any row
# MAGIC whose time range overlaps another row's range on the same account, atomically. In this lab you add the
# MAGIC constraint and try to break it.
# MAGIC
# MAGIC ## Learning objectives
# MAGIC
# MAGIC By the end of this lab, you will be able to:
# MAGIC
# MAGIC 1. **Describe a no-overlap rule** as an exclusion constraint on an account and a time range.
# MAGIC 2. **Add the constraint** with a GiST index and the `btree_gist` extension.
# MAGIC 3. **Watch the database reject** an overlapping settlement.
# MAGIC 4. **Explain why the database is the right place** for this rule when requests race.

# COMMAND ----------

# MAGIC %md
# MAGIC ## Key concepts
# MAGIC
# MAGIC - **Time range (`tstzrange`):** a Postgres value that holds a start and an end time. `&&` is true when two ranges overlap.
# MAGIC - **Exclusion constraint:** a rule that no two rows may match on all listed conditions, here the same account (`=`) and overlapping time ranges (`&&`). Postgres checks it when a row is written.
# MAGIC - **GiST and `btree_gist`:** GiST is the index type behind range operators; `btree_gist` lets it also compare plain values such as `account_id`, so both fit in one constraint.
# MAGIC - **Race condition:** two requests that each check, then write, can both pass the check. A constraint closes that gap, because the database checks and writes in one step.
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
# MAGIC     Needs: the <code>btree_gist</code> extension, which this notebook creates. Run it on a freshly loaded branch: it adds an exclusion constraint to <code>bank.settlement</code>.
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
# MAGIC ### A2. Load the helper
# MAGIC
# MAGIC This loads `run_sql()` and `connect()` from `common/scripts/`. `run_sql()` opens a connection to your
# MAGIC branch, runs one SQL statement, and returns any rows; `connect()` gives you the connection itself.
# MAGIC
# MAGIC Under the hood, both ask the Lakebase API for your branch's host name, get a login token from your
# MAGIC Databricks identity (valid for about an hour), and open a standard Postgres connection with `psycopg`,
# MAGIC a Postgres driver for Python.
# MAGIC
# MAGIC In the steps below, the SQL block in each step is the statement that runs on your branch. The Python
# MAGIC cell under it only sends that statement and prints the result.

# COMMAND ----------

import os, sys
sys.path.insert(0, os.path.join(os.getcwd(), "..", "..", "common", "scripts"))
from lakebase import connect, run_sql

SCHEMA = os.environ.get("LB_SCHEMA", "bank")
print("connected; schema:", SCHEMA)

# COMMAND ----------

# MAGIC %md-sandbox
# MAGIC **Expected result:** `connected; schema: bank`
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
# MAGIC ## B. The current schedule

# COMMAND ----------

# MAGIC %md
# MAGIC ### B1. Look at the settlements
# MAGIC
# MAGIC Three settlement legs, each booked on an account for a time window. The SQL:
# MAGIC
# MAGIC ```sql
# MAGIC SELECT settlement_id, account_id, starts_at, ends_at FROM bank.settlement LIMIT 3;
# MAGIC ```

# COMMAND ----------

sql = "SELECT settlement_id, account_id, starts_at, ends_at FROM bank.settlement LIMIT 3"
rows = run_sql(sql)
print("Sample settlements:")
for row in rows:
    print(f"  {row}")

# COMMAND ----------

# MAGIC %md
# MAGIC **Expected result:** three rows, `STL-1` on `CTA-100240`, `STL-2` on `CTA-100241` and `STL-3` on `CTA-200310`,
# MAGIC each with a start and end time. The times are relative to when you loaded the bank, so yours show
# MAGIC today's date.
# MAGIC
# MAGIC **What this proves:** today the only thing keeping windows apart is that nobody has booked a clash yet.

# COMMAND ----------

# MAGIC %md
# MAGIC ## C. Let the database enforce the rule

# COMMAND ----------

# MAGIC %md
# MAGIC ### C1. Add the exclusion constraint
# MAGIC
# MAGIC ```sql
# MAGIC CREATE EXTENSION IF NOT EXISTS btree_gist;
# MAGIC ALTER TABLE bank.settlement ADD CONSTRAINT no_account_overlap
# MAGIC   EXCLUDE USING gist (account_id WITH =, tstzrange(starts_at, ends_at) WITH &&);
# MAGIC ```

# COMMAND ----------

with connect() as conn:
    with conn.cursor() as cur:
        try:
            cur.execute("CREATE EXTENSION IF NOT EXISTS btree_gist")
            print("btree_gist extension created")
        except:
            pass

        # Postgres has no ADD CONSTRAINT IF NOT EXISTS; drop then add so it's idempotent.
        cur.execute("ALTER TABLE bank.settlement DROP CONSTRAINT IF EXISTS no_account_overlap")
        sql = """
        ALTER TABLE bank.settlement
          ADD CONSTRAINT no_account_overlap
          EXCLUDE USING gist (account_id WITH =,
                              tstzrange(starts_at, ends_at) WITH &&)
        """
        try:
            cur.execute(sql)
            print("Exclusion constraint created: no_account_overlap")
        except Exception as e:
            print(f"Could not create constraint: {e}")

# COMMAND ----------

# MAGIC %md-sandbox
# MAGIC **Expected result:** ```
# MAGIC btree_gist extension created
# MAGIC Exclusion constraint created: no_account_overlap
# MAGIC ```
# MAGIC
# MAGIC **What this proves:** the rule now lives in the database. The existing rows already satisfy it, or adding it would have failed.
# MAGIC
# MAGIC <div style="border-left:4px solid #FF9800; background:#FFF3E0; padding:12px 16px; border-radius:4px; margin:12px 0; font-family:sans-serif;">
# MAGIC   <strong style="display:block; color:#E65100; margin-bottom:6px;">Troubleshooting</strong>
# MAGIC   <div style="color:#333;">
# MAGIC     <ul style="margin:0; padding-left:20px;">
# MAGIC       <li><code>Could not create constraint: ... already exists</code>: you ran this cell before on this branch. That's fine; continue to C2.</li>
# MAGIC     </ul>
# MAGIC   </div>
# MAGIC </div>

# COMMAND ----------

# MAGIC %md
# MAGIC ### C2. Try to book an overlapping settlement
# MAGIC
# MAGIC The cell takes an existing settlement and inserts another one on the same account, overlapping its
# MAGIC window.

# COMMAND ----------

import datetime

# Get an existing settlement (and its trade, to satisfy the FK) to overlap.
stls = run_sql("""
SELECT settlement_id, trade_id, account_id, starts_at, ends_at
  FROM bank.settlement
 WHERE account_id IS NOT NULL AND starts_at IS NOT NULL AND ends_at IS NOT NULL
 LIMIT 1
""")

if not stls:
    print("No existing settlements found")
else:
    settlement_id, trade_id, account_id, starts_at, ends_at = stls[0]

    # Try to insert an overlapping settlement
    with connect() as conn:
        with conn.cursor() as cur:
            # Clean any prior test row so this is re-runnable
            cur.execute("DELETE FROM bank.settlement WHERE settlement_id = 'STL-OVERLAP'")
            try:
                # Create a settlement that overlaps with the existing one
                overlap_start = starts_at
                overlap_end = ends_at + datetime.timedelta(hours=1)

                cur.execute("""
                INSERT INTO bank.settlement
                  (settlement_id, trade_id, account_id, seq, status, starts_at, ends_at)
                VALUES
                  (%s, %s, %s, %s, %s, %s, %s)
                """, ('STL-OVERLAP', trade_id, account_id, 99, 'pending', overlap_start, overlap_end))
                print("ERROR: Overlap should have been rejected!")
            except Exception as e:
                error_msg = str(e)
                if "no_account_overlap" in error_msg or "conflicting key" in error_msg or "exclusion" in error_msg.lower():
                    print("Good: the database rejected the overlapping settlement.")
                    print(f"  {error_msg.splitlines()[0][:120]}")
                else:
                    print(f"Unexpected error: {error_msg[:120]}")

# COMMAND ----------

# MAGIC %md
# MAGIC **Expected result:** ```
# MAGIC Good: the database rejected the overlapping settlement.
# MAGIC   conflicting key value violates exclusion constraint "no_account_overlap"
# MAGIC ```
# MAGIC
# MAGIC **What this proves:** the overlap can't be written, whichever application, user or race tries. No app code checked anything.

# COMMAND ----------

# MAGIC %md
# MAGIC ### C3. Look at the plan for an insert
# MAGIC
# MAGIC `EXPLAIN` shows how Postgres would produce the new row. The constraint isn't in the plan: Postgres
# MAGIC checks an exclusion constraint when the row is written, using the constraint's GiST index, which is
# MAGIC why C2 failed at insert time.

# COMMAND ----------

sql = ("EXPLAIN INSERT INTO bank.settlement "
       "(settlement_id, trade_id, account_id, seq, status, starts_at, ends_at) "
       "SELECT 'stl-explain', trade_id, 'CTA-100240', 98, 'pending', now(), now() + interval '1 hour' "
       "FROM bank.settlement LIMIT 1")

with connect() as conn:
    with conn.cursor() as cur:
        cur.execute(sql)
        rows = cur.fetchall()
        print("Query plan (the exclusion check runs when the row is written, so it isn't listed here):")
        for row in rows:
            print(f"  {row[0]}")

# COMMAND ----------

# MAGIC %md
# MAGIC **Expected result:** ```
# MAGIC Query plan (the exclusion check runs when the row is written, so it isn't listed here):
# MAGIC   Insert on settlement  (cost=0.00..0.36 rows=0 width=0)
# MAGIC     ->  Subquery Scan on "*SELECT*"  (cost=0.00..0.36 rows=1 width=148)
# MAGIC           ->  Limit  (cost=0.00..0.35 rows=1 width=148)
# MAGIC                 ->  Seq Scan on settlement settlement_1  (cost=0.00..1.05 rows=3 width=148)
# MAGIC ```

# COMMAND ----------

# MAGIC %md-sandbox
# MAGIC ##### EXPAND FOR ADDITIONAL NOTES
# MAGIC
# MAGIC <details>
# MAGIC <summary><strong>Why not check in the application?</strong></summary>
# MAGIC
# MAGIC An application check is two steps: read ("is the window free?") and write ("book it"). Two requests
# MAGIC can both read before either writes, and both book. Locking in the application can fix that, but every
# MAGIC service that writes settlements must get it right. A constraint is one rule, in one place, checked
# MAGIC atomically for every writer.
# MAGIC
# MAGIC </details>

# COMMAND ----------

# MAGIC %md-sandbox
# MAGIC ##### Check your understanding
# MAGIC
# MAGIC <details>
# MAGIC <summary><strong>1. What two conditions does `no_account_overlap` combine?</strong></summary>
# MAGIC
# MAGIC The same `account_id` (`=`) and overlapping time ranges (`&&`).
# MAGIC
# MAGIC </details>
# MAGIC
# MAGIC <details>
# MAGIC <summary><strong>2. Why doesn't the constraint appear in the `EXPLAIN` output?</strong></summary>
# MAGIC
# MAGIC Postgres checks exclusion constraints when the row is written, not as part of the query plan.
# MAGIC
# MAGIC </details>
# MAGIC
# MAGIC <details>
# MAGIC <summary><strong>3. Why is a constraint safer than an application check?</strong></summary>
# MAGIC
# MAGIC The database checks and writes in one atomic step, so racing requests can't both pass.
# MAGIC
# MAGIC </details>

# COMMAND ----------

# MAGIC %md
# MAGIC ## D. Conclusion
# MAGIC
# MAGIC In this lab you added an exclusion constraint and watched the database refuse an overlapping
# MAGIC settlement. Key takeaways:
# MAGIC
# MAGIC 1. **Exclusion constraints express "no two rows may clash"** on any combination of conditions.
# MAGIC 2. **GiST and `btree_gist`** let one constraint combine an account match with a time-range overlap.
# MAGIC 3. **The database enforces the rule atomically,** for every writer, with no race window.
# MAGIC 4. **The check happens at write time,** not in the query plan.

# COMMAND ----------

# MAGIC %md
# MAGIC ---
# MAGIC **Next in the App developers track:** <a href="$../data-api/data_api_databricks">Lakebase Data API →</a>
# MAGIC
# MAGIC <a href="$../../START_HERE">← Back to the table of contents</a>
