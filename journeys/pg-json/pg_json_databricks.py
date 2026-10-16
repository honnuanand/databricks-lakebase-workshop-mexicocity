# Databricks notebook source
# MAGIC %md-sandbox
# MAGIC <div style="display:flex; align-items:center; gap:10px; padding:8px 16px; background:#F9F7F4; border-bottom:2px solid #E0E0E0; font-family:sans-serif; line-height:1;">
# MAGIC   <span style="display:inline-block; width:12px; height:12px; border-radius:2px; background:#FF3621;"></span>
# MAGIC   <span style="font-weight:bold; color:#0b2026;">Lakebase workshop</span>
# MAGIC   <span style="color:#999;">|</span>
# MAGIC   <span style="color:#5A6F77;">Part 2 · App developers · Journey 1 of 6 · JSON Data with JSONB</span>
# MAGIC </div>

# COMMAND ----------

# MAGIC %md
# MAGIC # JSON Data with JSONB
# MAGIC #### Duration: 20 minutes
# MAGIC
# MAGIC *Journey 1 of 6 in the App developers track. Part 1 used fixed columns; this journey stores data whose shape varies from row to row.*
# MAGIC
# MAGIC ## Overview
# MAGIC
# MAGIC The bank's product team keeps a spec sheet for every instrument: an equity has a ticker, a sector and
# MAGIC a beta; a bond has a tenor, a coupon and a rating; cash just has a currency. A new product type would
# MAGIC normally mean a schema change, and an `ALTER TABLE` on a busy table is never fun.
# MAGIC
# MAGIC Postgres stores those sheets as **JSONB**, structured JSON inside a regular column, and lets you query
# MAGIC and index them with plain SQL. In this lab you look at the specs, search inside them, pull fields out
# MAGIC like columns, and add an index that keeps those searches fast as the table grows.
# MAGIC
# MAGIC ## Learning objectives
# MAGIC
# MAGIC By the end of this lab, you will be able to:
# MAGIC
# MAGIC 1. **Store documents with varying fields** in a JSONB column, next to regular columns.
# MAGIC 2. **Find rows by what their document contains** with the containment operator `@>`.
# MAGIC 3. **Extract a field as a value** with `#>>` and check for a key with `?`.
# MAGIC 4. **Index a JSONB column** with GIN so containment searches stay fast at scale.

# COMMAND ----------

# MAGIC %md
# MAGIC ## Key concepts
# MAGIC
# MAGIC - **JSONB:** Postgres's binary JSON type. It stores a JSON document in a column and lets SQL query inside it; keys can differ from row to row.
# MAGIC - **Containment (`@>`):** "does the document on the left contain this piece?" `spec @> '{"sector": "tech"}'` matches every spec with that key and value, whatever else it holds.
# MAGIC - **Path extraction (`#>>`) and key exists (`?`):** `spec #>> '{sector}'` returns the sector as text; `spec ? 'sector'` is true when the key exists.
# MAGIC - **GIN index:** a Generalized Inverted Index: it indexes the keys and values inside each document, so containment searches don't have to read every row.
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
# MAGIC     Needs: nothing beyond setup (JSONB and GIN are built into Postgres).
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
# MAGIC ## B. Look inside the documents

# COMMAND ----------

# MAGIC %md
# MAGIC ### B1. See the specs
# MAGIC
# MAGIC Each instrument has a `spec` column of type JSONB, and its fields differ by kind. The SQL:
# MAGIC
# MAGIC ```sql
# MAGIC SELECT instrument_id, name, spec FROM bank.instrument LIMIT 3;
# MAGIC ```

# COMMAND ----------

sql = "SELECT instrument_id, name, spec FROM bank.instrument LIMIT 3"
rows = run_sql(sql)
print("Sample instrument specs (JSONB, varying fields):")
for row in rows:
    print(f"  {row[0]}: {row[1]}")
    print(f"    spec: {row[2]}")

# COMMAND ----------

# MAGIC %md
# MAGIC **Expected result:** three instruments and their specs, for example:
# MAGIC
# MAGIC ```
# MAGIC Sample instrument specs (JSONB, varying fields):
# MAGIC   INS-CASH-MXN: Mexican Peso Cash
# MAGIC     spec: {'ccy': 'MXN'}
# MAGIC   INS-SLEEVE-EQ: Equity Sleeve
# MAGIC     spec: {'theme': 'large-cap'}
# MAGIC   INS-QTZL: Quetzal Tecnologia
# MAGIC     spec: {'beta': 1.2, 'sector': 'tech', 'ticker': 'QTZL'}
# MAGIC ```
# MAGIC
# MAGIC Without an `ORDER BY`, the three rows you see may differ.
# MAGIC
# MAGIC **What this proves:** one column holds documents of different shapes. Nobody had to add a `beta` or `ccy` column.

# COMMAND ----------

# MAGIC %md
# MAGIC ### B2. Search by what a document contains
# MAGIC
# MAGIC `@>` asks whether the document on the left contains the piece on the right. Find the tech
# MAGIC instruments. The SQL:
# MAGIC
# MAGIC ```sql
# MAGIC SELECT instrument_id, name, spec FROM bank.instrument
# MAGIC  WHERE spec @> '{"sector": "tech"}' LIMIT 5;
# MAGIC ```

# COMMAND ----------

sql = """
SELECT instrument_id, name, spec
  FROM bank.instrument
 WHERE spec @> '{"sector": "tech"}'
 LIMIT 5
"""
rows = run_sql(sql)
print("Instruments with sector='tech' (using @> containment):")
for row in rows:
    print(f"  {row[0]}: {row[1]}")
    print(f"    spec: {row[2]}")

# COMMAND ----------

# MAGIC %md
# MAGIC **Expected result:** the two tech equities:
# MAGIC
# MAGIC ```
# MAGIC Instruments with sector='tech' (using @> containment):
# MAGIC   INS-QTZL: Quetzal Tecnologia
# MAGIC     spec: {'beta': 1.2, 'sector': 'tech', 'ticker': 'QTZL'}
# MAGIC   INS-ZAFR: Zafiro Software
# MAGIC     spec: {'beta': 0.9, 'sector': 'tech', 'ticker': 'ZAFR'}
# MAGIC ```
# MAGIC
# MAGIC **What this proves:** you can filter on a field inside the document, and rows without that field simply don't match.

# COMMAND ----------

# MAGIC %md
# MAGIC ### B3. Pull a field out like a column
# MAGIC
# MAGIC `#>>` extracts the value at a path as text; `?` keeps only rows that have the key. The SQL:
# MAGIC
# MAGIC ```sql
# MAGIC SELECT instrument_id, name, spec #>> '{sector}' AS sector FROM bank.instrument
# MAGIC  WHERE spec ? 'sector' LIMIT 5;
# MAGIC ```

# COMMAND ----------

sql = """
SELECT instrument_id, name, spec #>> '{sector}' as sector
  FROM bank.instrument
 WHERE spec ? 'sector'
 LIMIT 5
"""
rows = run_sql(sql)
print("Extracted sector field from JSONB spec:")
for row in rows:
    print(f"  {row[0]}: sector={row[2]}")

# COMMAND ----------

# MAGIC %md
# MAGIC **Expected result:** ```
# MAGIC Extracted sector field from JSONB spec:
# MAGIC   INS-QTZL: sector=tech
# MAGIC   INS-ZAFR: sector=tech
# MAGIC ```
# MAGIC
# MAGIC **What this proves:** a JSON field can be used like a regular column in a result. Only the two equities have a `sector` key.

# COMMAND ----------

# MAGIC %md
# MAGIC ## C. Make it fast

# COMMAND ----------

# MAGIC %md
# MAGIC ### C1. Add a GIN index
# MAGIC
# MAGIC Searches are fast on five rows anyway. On millions, a GIN index on the JSONB column lets `@>` use the
# MAGIC index instead of reading every row. The SQL:
# MAGIC
# MAGIC ```sql
# MAGIC CREATE INDEX IF NOT EXISTS idx_instrument_spec_gin ON bank.instrument USING gin(spec jsonb_path_ops);
# MAGIC ```

# COMMAND ----------

sql = "CREATE INDEX IF NOT EXISTS idx_instrument_spec_gin ON bank.instrument USING gin(spec jsonb_path_ops)"
with connect() as conn:
    with conn.cursor() as cur:
        cur.execute(sql)
print("GIN index created on bank.instrument(spec)")
print("(Queries will use the index if beneficial)")

# COMMAND ----------

# MAGIC %md-sandbox
# MAGIC **Expected result:** ```
# MAGIC GIN index created on bank.instrument(spec)
# MAGIC (Queries will use the index if beneficial)
# MAGIC ```
# MAGIC
# MAGIC **What this proves:** JSONB columns can be indexed like any other column. On a table this small the planner may still choose a plain scan; the index pays off as the table grows.
# MAGIC
# MAGIC <div style="border-left:4px solid #1B5162; background:#EEF4F6; padding:12px 16px; border-radius:4px; margin:12px 0; font-family:sans-serif;">
# MAGIC   <strong style="display:block; color:#1B5162; margin-bottom:6px;">See it in the UI (optional)</strong>
# MAGIC   <div style="color:#333;">
# MAGIC     In the <strong>Lakebase Postgres</strong> app, open your branch's <strong>Tables</strong> tab and select <code>instrument</code> to see its columns, including <code>spec</code>, and its indexes.
# MAGIC   </div>
# MAGIC </div>

# COMMAND ----------

# MAGIC %md
# MAGIC ### C2. A screening query
# MAGIC
# MAGIC Combine a JSONB condition with a regular column: tech-sector equities. The SQL:
# MAGIC
# MAGIC ```sql
# MAGIC SELECT instrument_id, name, spec FROM bank.instrument
# MAGIC  WHERE spec @> '{"sector": "tech"}' AND kind = 'equity' LIMIT 10;
# MAGIC ```

# COMMAND ----------

sql = """
SELECT instrument_id, name, spec
  FROM bank.instrument
 WHERE spec @> '{"sector": "tech"}'
    AND kind = 'equity'
 LIMIT 10
"""
rows = run_sql(sql)
print("Equities in tech sector:")
for row in rows:
    print(f"  {row[0]}: {row[1]}")
    if row[2]:
        print(f"    {row[2]}")

# COMMAND ----------

# MAGIC %md
# MAGIC **Expected result:** ```
# MAGIC Equities in tech sector:
# MAGIC   INS-QTZL: Quetzal Tecnologia
# MAGIC     {'beta': 1.2, 'sector': 'tech', 'ticker': 'QTZL'}
# MAGIC   INS-ZAFR: Zafiro Software
# MAGIC     {'beta': 0.9, 'sector': 'tech', 'ticker': 'ZAFR'}
# MAGIC ```
# MAGIC
# MAGIC **What this proves:** JSONB and regular columns mix in one `WHERE`, so flexible specs don't cost you plain SQL.

# COMMAND ----------

# MAGIC %md-sandbox
# MAGIC ##### EXPAND FOR ADDITIONAL NOTES
# MAGIC
# MAGIC <details>
# MAGIC <summary><strong>When to use JSONB, and when not to</strong></summary>
# MAGIC
# MAGIC Use JSONB for attributes that vary by type or change often: product specs, mandates, settings. Keep
# MAGIC fields you join on, sum, or constrain (ids, amounts, dates) as regular columns: they're smaller, typed,
# MAGIC and easier to validate.
# MAGIC
# MAGIC `jsonb_path_ops`, used here, makes a smaller and faster index for `@>`, but doesn't support the `?`
# MAGIC key-exists operator; the default `jsonb_ops` supports both.
# MAGIC
# MAGIC </details>

# COMMAND ----------

# MAGIC %md-sandbox
# MAGIC ##### Check your understanding
# MAGIC
# MAGIC <details>
# MAGIC <summary><strong>1. What does `spec @> '{"sector": "tech"}'` match?</strong></summary>
# MAGIC
# MAGIC Every row whose spec contains the key `sector` with the value `tech`, whatever other keys it has.
# MAGIC
# MAGIC </details>
# MAGIC
# MAGIC <details>
# MAGIC <summary><strong>2. Why didn't the Bono M show up in B3?</strong></summary>
# MAGIC
# MAGIC Its spec has no `sector` key, so `spec ? 'sector'` is false for it.
# MAGIC
# MAGIC </details>
# MAGIC
# MAGIC <details>
# MAGIC <summary><strong>3. When does the GIN index help?</strong></summary>
# MAGIC
# MAGIC On large tables, for containment searches: the planner can use it instead of reading every row.
# MAGIC
# MAGIC </details>

# COMMAND ----------

# MAGIC %md
# MAGIC ## D. Conclusion
# MAGIC
# MAGIC In this lab you stored documents of different shapes in one column, searched inside them, pulled
# MAGIC fields out, and indexed them. Key takeaways:
# MAGIC
# MAGIC 1. **JSONB holds varying fields** in one column, with no schema change per product type.
# MAGIC 2. **`@>` finds rows by what their document contains;** `#>>` and `?` read and check single fields.
# MAGIC 3. **GIN indexes** keep containment searches fast as tables grow.
# MAGIC 4. **JSONB and regular columns work together** in the same SQL.
# MAGIC
# MAGIC The next journey stores a different kind of value on the row: a vector, for similarity search.

# COMMAND ----------

# MAGIC %md
# MAGIC ---
# MAGIC **Next in the App developers track:** <a href="$../pg-vector/pg_vector_databricks">Vector Similarity Search →</a>
# MAGIC
# MAGIC <a href="$../../START_HERE">← Back to the table of contents</a>
