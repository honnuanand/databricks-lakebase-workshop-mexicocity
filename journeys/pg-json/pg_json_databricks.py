# Databricks notebook source
# MAGIC %md
# MAGIC # JSON documents, step by step
# MAGIC
# MAGIC A hands-on lab. Run one cell at a time, read what happened, then move on. You will query JSONB specs with containment, path extraction, and GIN indexes.
# MAGIC
# MAGIC Each step shows the real interface: SQL where the step is a query, and Python for control operations.
# MAGIC
# MAGIC **Before you start:** run `00-setup/setup_databricks` once to create your branch, then run the setup cells below.

# COMMAND ----------

# MAGIC %md
# MAGIC ## Run first: install the driver and pick your branch
# MAGIC Run the next three cells before anything else. They install the Postgres driver, upgrade the
# MAGIC Databricks SDK if your environment's version predates the Lakebase API, and set `LB_PROJECT`,
# MAGIC `LB_BRANCH`, and `LB_SCHEMA` from the widgets at the top of this notebook.
# MAGIC `LB_BRANCH` defaults to the branch `00-setup/setup_databricks` created for you. Change a widget
# MAGIC only if you used a different project or branch name.

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

# MAGIC %md
# MAGIC ## Setup, connect to your branch

# COMMAND ----------

import os, sys
sys.path.insert(0, os.path.join(os.getcwd(), "..", "..", "common", "scripts"))
from lakebase import connect, run_sql

SCHEMA = os.environ.get("LB_SCHEMA", "bank")
print("connected; schema:", SCHEMA)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 1, inspect JSONB specs on instruments
# MAGIC
# MAGIC Each instrument has a `spec` column (JSONB). The contents vary: one instrument might have `{"ticker": "QTZL", "sector": "tech", "beta": 1.2}`, another might have `{"tenor": "10Y", "coupon": 4.0, "rating": "AAA"}`. No schema migration needed when a new instrument type arrives with new fields. The SQL:
# MAGIC
# MAGIC ```sql
# MAGIC SELECT instrument_id, name, spec FROM bank.instrument LIMIT 3
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
# MAGIC ## Step 2, use containment operator (@>) to find instruments matching a spec
# MAGIC
# MAGIC The `@>` operator asks "does the JSON document on the left contain the JSON sub-document on the right?" This is the workhorse for spec matching. Find instruments that match a spec. The SQL:
# MAGIC
# MAGIC ```sql
# MAGIC SELECT instrument_id, name, spec
# MAGIC   FROM bank.instrument
# MAGIC  WHERE spec @> '{"sector": "tech"}'
# MAGIC  LIMIT 5
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
# MAGIC ## Step 3, use path extraction (#>>) and key exists (?) operators
# MAGIC
# MAGIC The `#>>` operator extracts a value from a path in the JSON. Use it to extract a field for filtering or display. The `?` operator checks if a key exists. Together, they let you filter and display JSON fields like columns. The SQL:
# MAGIC
# MAGIC ```sql
# MAGIC SELECT instrument_id, name, spec #>> '{sector}' as sector
# MAGIC   FROM bank.instrument
# MAGIC  WHERE spec ? 'sector'
# MAGIC  LIMIT 5
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
# MAGIC ## Step 4, create a GIN index on JSONB
# MAGIC
# MAGIC JSONB queries are fast even without an index. With a GIN (Generalized Inverted Index) on the JSONB column, they are faster. The SQL:
# MAGIC
# MAGIC ```sql
# MAGIC CREATE INDEX IF NOT EXISTS idx_instrument_spec_gin ON bank.instrument
# MAGIC   USING gin(spec jsonb_path_ops)
# MAGIC ```

# COMMAND ----------

sql = "CREATE INDEX IF NOT EXISTS idx_instrument_spec_gin ON bank.instrument USING gin(spec jsonb_path_ops)"
with connect() as conn:
    with conn.cursor() as cur:
        cur.execute(sql)
print("GIN index created on bank.instrument(spec)")
print("(Queries will use the index if beneficial)")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 5, realistic screening query: equities in tech sector
# MAGIC
# MAGIC Find instruments that are equities in the tech sector. The SQL:
# MAGIC
# MAGIC ```sql
# MAGIC SELECT instrument_id, name, spec
# MAGIC   FROM bank.instrument
# MAGIC  WHERE spec @> '{"sector": "tech"}'
# MAGIC    AND kind = 'equity'
# MAGIC  LIMIT 10
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
# MAGIC ## What you learned
# MAGIC
# MAGIC You mastered JSONB: the containment operator (@>) for semantic matching, path extraction (#>>) and key checks (?) for drill-down, and GIN indexes for speed. Postgres gives you flexibility of schema-less storage with the power of a relational query engine.

# COMMAND ----------

# MAGIC %md
# MAGIC ---
# MAGIC **Next in the App developers track:** <a href="$../pg-vector/pg_vector_databricks">Vector Similarity Search →</a>
# MAGIC
# MAGIC <a href="$../../START_HERE">← Back to the table of contents</a>
