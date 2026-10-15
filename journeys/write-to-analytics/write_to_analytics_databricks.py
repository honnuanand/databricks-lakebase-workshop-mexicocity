# Databricks notebook source
# MAGIC %md-sandbox
# MAGIC <div style="display:flex; align-items:center; gap:10px; padding:8px 16px; background:#F9F7F4; border-bottom:2px solid #E0E0E0; font-family:sans-serif; line-height:1;">
# MAGIC   <span style="display:inline-block; width:12px; height:12px; border-radius:2px; background:#FF3621;"></span>
# MAGIC   <span style="font-weight:bold; color:#0b2026;">Lakebase workshop</span>
# MAGIC   <span style="color:#999;">|</span>
# MAGIC   <span style="color:#5A6F77;">Part 1 · Journey 3 of 5 · Lakebase Data in the Lakehouse</span>
# MAGIC </div>

# COMMAND ----------

# MAGIC %md
# MAGIC # Lakebase Data in the Lakehouse
# MAGIC #### Duration: about 20 minutes
# MAGIC
# MAGIC *Journey 3 of 5. The first two journeys changed your branch through Postgres. This one looks at the same rows from the analytics side.*
# MAGIC
# MAGIC ## Overview
# MAGIC
# MAGIC A $2,200 cash withdrawal lands overnight on account `ACCT-100240`, whose credit utilization is
# MAGIC already running hot. The authorization path has milliseconds to decide, while the fraud team's
# MAGIC analytics run in the lakehouse. In the usual architecture, transactions are copied to an analytics
# MAGIC store on a schedule, so the fraud score the operational side sees is always a little stale.
# MAGIC
# MAGIC With Lakebase, the operational rows and the analytics work on the same copy. In this lab you write
# MAGIC the transaction through Postgres, compute a fraud-risk score from it, and write the score back onto
# MAGIC the same row. Then you see how the lakehouse reads those rows through Unity Catalog, with no pipeline.
# MAGIC
# MAGIC ## Learning objectives
# MAGIC
# MAGIC By the end of this lab, you will be able to:
# MAGIC
# MAGIC 1. **Write an operational row** through Postgres, the way an application does.
# MAGIC 2. **Compute an analytics value** from that row and store it on the same row.
# MAGIC 3. **Read the score back** at operational speed, with no copy in between.
# MAGIC 4. **Explain how the lakehouse reads Lakebase tables** through a Unity Catalog catalog.

# COMMAND ----------

# MAGIC %md
# MAGIC ## Key concepts
# MAGIC
# MAGIC - **Operational vs analytical work:** operational (OLTP) work is many small, fast reads and writes, like recording one transaction. Analytical work scans many rows to find patterns, like scoring fraud across all transactions.
# MAGIC - **Lakehouse:** Databricks' analytics platform: tables in cloud storage, queried with SQL warehouses and Spark.
# MAGIC - **Unity Catalog:** Databricks' governance layer: one place to name, secure, and audit data across the platform. Tables are named `catalog.schema.table`.
# MAGIC - **Foreign catalog:** a Unity Catalog catalog whose tables live in another database, here Lakebase. Queries read the data where it is; nothing is copied.
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
# MAGIC     If you just did Point-in-Time Restore, make sure you ran its reset cell.
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
# MAGIC ### A2. Load the helper
# MAGIC
# MAGIC This loads `run_sql()` from `common/scripts/`. It opens a connection to your branch, runs one SQL
# MAGIC statement, and returns any rows.
# MAGIC
# MAGIC Under the hood, `run_sql()` asks the Lakebase API for your branch's host name, gets a login token
# MAGIC from your Databricks identity (valid for about an hour), and opens a standard Postgres connection
# MAGIC with `psycopg`, a Postgres driver for Python.
# MAGIC
# MAGIC In the steps below, the SQL block in each step is the statement that runs on your branch. The Python
# MAGIC cell under it only sends that statement and prints the result.

# COMMAND ----------

import os, sys
sys.path.insert(0, os.path.join(os.getcwd(), "..", "..", "common", "scripts"))
from lakebase import run_sql
print("ready")

# COMMAND ----------

# MAGIC %md
# MAGIC **Expected result:** `ready`

# COMMAND ----------

# MAGIC %md
# MAGIC ## B. Write a transaction through Postgres
# MAGIC
# MAGIC First add a column to hold the score, then write the new transaction for `ACCT-100240`: $2,200,
# MAGIC merchant category 6011 (cash withdrawal), anomaly score 8.7 out of 10, and the account at 92%
# MAGIC utilization. This is an ordinary operational write, the kind an application makes all day:
# MAGIC
# MAGIC ```sql
# MAGIC ALTER TABLE bank.txn ADD COLUMN IF NOT EXISTS fraud_risk NUMERIC(5,1);
# MAGIC INSERT INTO bank.txn (account_id, ts, amount_usd, anomaly_score, mcc, util_pct)
# MAGIC VALUES ('ACCT-100240', now(), 2200.00, 8.7, 6011, 92.0) RETURNING txn_id;
# MAGIC ```

# COMMAND ----------

run_sql("ALTER TABLE bank.txn ADD COLUMN IF NOT EXISTS fraud_risk NUMERIC(5,1)")
r = run_sql("""INSERT INTO bank.txn
  (account_id, ts, amount_usd, anomaly_score, mcc, util_pct)
  VALUES ('ACCT-100240', now(), 2200.00, 8.7, 6011, 92.0)
  RETURNING txn_id, amount_usd, anomaly_score""")
rid = r[0][0]
print("inserted txn_id", r[0])

# COMMAND ----------

# MAGIC %md-sandbox
# MAGIC **Expected result:** `inserted txn_id (6, Decimal('2200.00'), Decimal('8.70'))`. The first number is
# MAGIC the new row's `txn_id`: 6 on a freshly loaded branch, one higher each time you run the cell.
# MAGIC
# MAGIC **What this proves:** the transaction is an ordinary Postgres row, written the way any application writes one.
# MAGIC
# MAGIC <div style="border-left:4px solid #FF9800; background:#FFF3E0; padding:12px 16px; border-radius:4px; margin:12px 0; font-family:sans-serif;">
# MAGIC   <strong style="display:block; color:#E65100; margin-bottom:6px;">Troubleshooting</strong>
# MAGIC   <div style="color:#333;">
# MAGIC     <ul style="margin:0; padding-left:20px;">
# MAGIC       <li><code>Missing required env var LB_PROJECT</code>: the A1 cells didn't run in this session. Run the three A1 cells, then A2 and this one.</li>
# MAGIC       <li><code>relation "bank.txn" does not exist</code>: the bank isn't loaded on this branch. Run <code>00-setup/setup_databricks</code>, then come back.</li>
# MAGIC     </ul>
# MAGIC   </div>
# MAGIC </div>

# COMMAND ----------

# MAGIC %md
# MAGIC ## C. Score the transaction and write the score back
# MAGIC
# MAGIC Compute a fraud-risk score from the row and store it on the same row. In a real system the score
# MAGIC would come from a model; here it's a simple formula so you can check the number by hand. It adds two
# MAGIC parts, each worth up to 100: the anomaly score (out of 10) and the utilization (out of 100). The total
# MAGIC runs from 0 to 200.
# MAGIC
# MAGIC ```sql
# MAGIC UPDATE bank.txn
# MAGIC SET fraud_risk = ROUND(100 * (anomaly_score / 10.0 + util_pct / 100.0), 1)
# MAGIC WHERE txn_id = <rid>;
# MAGIC ```

# COMMAND ----------

run_sql(f"UPDATE bank.txn SET fraud_risk = "
        f"ROUND(100*(anomaly_score/10.0 + util_pct/100.0),1) WHERE txn_id={rid}")
row = run_sql(f"SELECT txn_id, account_id, amount_usd, anomaly_score, util_pct, fraud_risk "
              f"FROM bank.txn WHERE txn_id={rid}")[0]
print("scored + wrote back:", row)

# COMMAND ----------

# MAGIC %md
# MAGIC **Expected result:**
# MAGIC `scored + wrote back: (6, 'ACCT-100240', Decimal('2200.00'), Decimal('8.70'), Decimal('92.00'), Decimal('179.0'))`
# MAGIC
# MAGIC The score is `ROUND(100 × (8.7 / 10 + 92 / 100), 1)` = `ROUND(100 × 1.79, 1)` = **179.0** out of
# MAGIC 200, close to the top. It's stored on the row you wrote in B, so the authorization path can read it
# MAGIC with its next query.
# MAGIC
# MAGIC **What this proves:** the analytics value lives on the operational row. Nothing copied the transaction somewhere else to score it, and nothing has to copy the score back.

# COMMAND ----------

# MAGIC %md-sandbox
# MAGIC ## D. Read the same rows from the lakehouse
# MAGIC
# MAGIC <div style="border-left:4px solid #1B5162; background:#EEF4F6; padding:12px 16px; border-radius:4px; margin:12px 0; font-family:sans-serif;">
# MAGIC   <strong style="display:block; color:#1B5162; margin-bottom:6px;">Explainer: this step doesn't run in this notebook</strong>
# MAGIC   <div style="color:#333;">
# MAGIC     Reading Lakebase from a SQL warehouse needs the database registered as a catalog in Unity
# MAGIC     Catalog, which needs permission to create a catalog. Workshop accounts usually don't have it,
# MAGIC     so this section shows the steps and the query instead of faking the output. Everything in B and
# MAGIC     C ran for real on your branch.
# MAGIC   </div>
# MAGIC </div>
# MAGIC
# MAGIC **1. Register the database** (once, by someone with permission to create a catalog): in
# MAGIC **Catalog Explorer**, choose **Create catalog**, set the type to **Lakebase Postgres**, and pick
# MAGIC the project, the branch, and the database `databricks_postgres`. Unity Catalog then exposes the
# MAGIC database's schemas and tables, including `bank.txn`.
# MAGIC
# MAGIC **2. Query it from a SQL warehouse:**
# MAGIC
# MAGIC ```sql
# MAGIC SELECT account_id, ts, amount_usd, anomaly_score, fraud_risk
# MAGIC FROM <your_catalog>.bank.txn
# MAGIC WHERE account_id = 'ACCT-100240'
# MAGIC ORDER BY ts DESC
# MAGIC LIMIT 1;
# MAGIC ```
# MAGIC
# MAGIC **What you'd expect to see:** the transaction you wrote in B, with the 179.0 score from C, because
# MAGIC the catalog reads the Lakebase table where it is. This query wasn't run in the workshop's workspace,
# MAGIC for the permission reason above.

# COMMAND ----------

# MAGIC %md-sandbox
# MAGIC ##### EXPAND FOR ADDITIONAL NOTES
# MAGIC
# MAGIC <details>
# MAGIC <summary><strong>How the lakehouse reads Lakebase without a copy</strong></summary>
# MAGIC
# MAGIC The registered catalog is a **foreign catalog**: Unity Catalog knows the database's schemas and
# MAGIC tables, but the data stays in Lakebase. When you query it, Databricks sends the parts of the query
# MAGIC that Postgres can run, such as filters and aggregations, to Lakebase, and gets back only the
# MAGIC results.
# MAGIC
# MAGIC That's why there's no lag to wait for: nothing is copied. The trade-off is that the query's speed
# MAGIC depends on the Lakebase compute. For large, repeated analytics, a copy in the lakehouse can still
# MAGIC be the better choice; for fresh operational data, a direct read avoids a pipeline entirely.
# MAGIC
# MAGIC Access to the catalog is governed by Unity Catalog like any other catalog: grants, lineage, and
# MAGIC audit logs.
# MAGIC
# MAGIC </details>

# COMMAND ----------

# MAGIC %md-sandbox
# MAGIC ##### Check your understanding
# MAGIC
# MAGIC <details>
# MAGIC <summary><strong>1. Where is the fraud score stored?</strong></summary>
# MAGIC
# MAGIC On the same `txn` row as the transaction, in the `fraud_risk` column.
# MAGIC
# MAGIC </details>
# MAGIC
# MAGIC <details>
# MAGIC <summary><strong>2. What does the lakehouse need before it can query these rows?</strong></summary>
# MAGIC
# MAGIC The Lakebase database registered in Unity Catalog as a catalog. Then a SQL warehouse or Spark can query `<catalog>.bank.txn`.
# MAGIC
# MAGIC </details>
# MAGIC
# MAGIC <details>
# MAGIC <summary><strong>3. Why does avoiding a copy matter for fraud scoring?</strong></summary>
# MAGIC
# MAGIC A copied score is only as fresh as the last copy. With one copy, the operational path always reads the latest score.
# MAGIC
# MAGIC </details>

# COMMAND ----------

# MAGIC %md
# MAGIC ## E. Conclusion
# MAGIC
# MAGIC In this lab you wrote a transaction through Postgres, scored it, wrote the score back onto the same
# MAGIC row, and saw how the lakehouse reads it. Key takeaways:
# MAGIC
# MAGIC 1. **One copy serves both sides:** the operational write and the analytics-derived score live on
# MAGIC    the same row.
# MAGIC 2. **No pipeline between them:** nothing copies the transaction to an analytics store and back.
# MAGIC 3. **The operational path reads the score at database speed,** with its next query.
# MAGIC 4. **The lakehouse can read the same tables** once the database is registered in Unity Catalog as a
# MAGIC    foreign catalog, governed like any other catalog.
# MAGIC
# MAGIC The next journey is about cost: what this database costs when nobody is using it.

# COMMAND ----------

# MAGIC %md
# MAGIC ---
# MAGIC **Next in Part 1:** <a href="$../scale-to-zero/scale_to_zero_databricks">Scale to Zero →</a>
# MAGIC
# MAGIC <a href="$../../START_HERE">← Back to the table of contents</a>
