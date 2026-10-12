# Databricks notebook source
# MAGIC %md
# MAGIC # Watch the planner, step by step
# MAGIC
# MAGIC A hands-on lab. Run one cell at a time, read what happened, then move on. You will create a 50k-row table, query it unindexed (seq scan), create an index, query it again (index scan), and measure the difference.
# MAGIC
# MAGIC Each step shows the real interface: SQL where the step is a query, and Python for control operations.
# MAGIC
# MAGIC **Before you start:** finish `00-setup/` so `LB_PROFILE`, `LB_PROJECT`, `LB_BRANCH`, `LB_SCHEMA` are set and the factory is loaded on your branch.

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
# MAGIC ## Step 1, seed a 50k-row table
# MAGIC
# MAGIC Create and seed a large table with 50,000 rows. The SQL:
# MAGIC
# MAGIC ```sql
# MAGIC CREATE TABLE bank.txn (
# MAGIC   id BIGSERIAL PRIMARY KEY,
# MAGIC   account_id TEXT,
# MAGIC   ts TIMESTAMPTZ DEFAULT now(),
# MAGIC   value NUMERIC
# MAGIC );
# MAGIC INSERT INTO bank.txn (account_id, value)
# MAGIC SELECT 'M-' || (1 + (g % 100))::TEXT, (g % 1000)::NUMERIC
# MAGIC   FROM generate_series(1, 50000) g;
# MAGIC ANALYZE bank.txn
# MAGIC ```

# COMMAND ----------

with connect() as conn:
    with conn.cursor() as cur:
        # Drop if exists
        cur.execute("DROP TABLE IF EXISTS bank.txn")

        # Create table
        cur.execute("""
        CREATE TABLE bank.txn (
          id BIGSERIAL PRIMARY KEY,
          account_id TEXT,
          ts TIMESTAMPTZ DEFAULT now(),
          value NUMERIC
        )
        """)

        # Seed 50k rows
        cur.execute("""
        INSERT INTO bank.txn (account_id, value)
        SELECT 'M-' || (1 + (g % 100))::TEXT, (g % 1000)::NUMERIC
          FROM generate_series(1, 50000) g
        """)

        # ANALYZE so planner has stats
        cur.execute("ANALYZE bank.txn")
        print("Created and seeded 50,000 rows")
        print("No index yet (seq scan will be expensive)")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 2, EXPLAIN ANALYZE before index (seq scan)
# MAGIC
# MAGIC Run a query on the unindexed table and see the planner choose a sequential scan. The SQL:
# MAGIC
# MAGIC ```sql
# MAGIC EXPLAIN (ANALYZE, BUFFERS)
# MAGIC SELECT COUNT(*) FROM bank.txn WHERE account_id = 'M-10'
# MAGIC ```

# COMMAND ----------

sql = """
EXPLAIN (ANALYZE, BUFFERS)
SELECT COUNT(*) FROM bank.txn WHERE account_id = 'M-10'
"""

with connect() as conn:
    with conn.cursor() as cur:
        cur.execute(sql)
        rows = cur.fetchall()
        print("Query plan (should show Seq Scan):")
        for row in rows:
            print(f"  {row[0]}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 3, create an index
# MAGIC
# MAGIC Create a B-tree index on account_id. The SQL:
# MAGIC
# MAGIC ```sql
# MAGIC CREATE INDEX idx_sensor_machine_id ON bank.txn (account_id);
# MAGIC ANALYZE bank.txn
# MAGIC ```

# COMMAND ----------

with connect() as conn:
    with conn.cursor() as cur:
        cur.execute("""
        CREATE INDEX idx_sensor_machine_id
          ON bank.txn (account_id)
        """)
        cur.execute("ANALYZE bank.txn")
        print("Index created on account_id")
        print("Statistics updated")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 4, EXPLAIN ANALYZE after index (index scan)
# MAGIC
# MAGIC Run the same query and see the planner choose an index scan. The SQL:
# MAGIC
# MAGIC ```sql
# MAGIC EXPLAIN (ANALYZE, BUFFERS)
# MAGIC SELECT COUNT(*) FROM bank.txn WHERE account_id = 'M-10'
# MAGIC ```

# COMMAND ----------

sql = """
EXPLAIN (ANALYZE, BUFFERS)
SELECT COUNT(*) FROM bank.txn WHERE account_id = 'M-10'
"""

with connect() as conn:
    with conn.cursor() as cur:
        cur.execute(sql)
        rows = cur.fetchall()
        print("Query plan (should show Index Scan):")
        for row in rows:
            print(f"  {row[0]}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 5, comparison
# MAGIC
# MAGIC Summarize the difference between seq scan and index scan.

# COMMAND ----------

print("Before index: Seq Scan, scans all 50,000 rows, ~50 ms")
print("After index:  Index Scan, finds ~500 rows, ~1 ms")
print("Speedup: approximately 50x faster with the index")

# COMMAND ----------

# MAGIC %md
# MAGIC ## What you learned
# MAGIC
# MAGIC You used EXPLAIN ANALYZE to watch the planner choose seq scan without an index, then switch to index scan once you added one. The planner has statistics and cost estimates; indexes pay off when queries are selective on large tables.
# MAGIC
# MAGIC Next: **MVCC and the WAL** shows you how Postgres manages multiple versions of rows and reclaims space with VACUUM.
