# Databricks notebook source
# MAGIC %md
# MAGIC # No double-booking, step by step
# MAGIC
# MAGIC A hands-on lab. Run one cell at a time, read what happened, then move on. You will create a GiST exclusion constraint to prevent overlapping operations on the same machine, then prove it works by attempting a conflicting insert.
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

SCHEMA = os.environ.get("LB_SCHEMA", "factory")
print("connected; schema:", SCHEMA)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 1, inspect the operation table
# MAGIC
# MAGIC See the structure of operations (work routing on machines). The SQL:
# MAGIC
# MAGIC ```sql
# MAGIC SELECT op_id, machine_id, starts_at, ends_at FROM factory.operation LIMIT 3
# MAGIC ```

# COMMAND ----------

sql = "SELECT op_id, machine_id, starts_at, ends_at FROM factory.operation LIMIT 3"
rows = run_sql(sql)
print("Sample operations:")
for row in rows:
    print(f"  {row}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 2, create GiST exclusion constraint
# MAGIC
# MAGIC Enable the btree_gist extension, then add an exclusion constraint that prevents overlapping time ranges for the same machine. The SQL:
# MAGIC
# MAGIC ```sql
# MAGIC CREATE EXTENSION IF NOT EXISTS btree_gist;
# MAGIC ALTER TABLE factory.operation
# MAGIC   ADD CONSTRAINT IF NOT EXISTS no_machine_overlap
# MAGIC   EXCLUDE USING gist (machine_id WITH =,
# MAGIC                       tstzrange(starts_at, ends_at) WITH &&)
# MAGIC ```

# COMMAND ----------

with connect() as conn:
    with conn.cursor() as cur:
        try:
            cur.execute("CREATE EXTENSION IF NOT EXISTS btree_gist")
            print("btree_gist extension created")
        except:
            pass

        sql = """
        ALTER TABLE factory.operation
          ADD CONSTRAINT IF NOT EXISTS no_machine_overlap
          EXCLUDE USING gist (machine_id WITH =,
                              tstzrange(starts_at, ends_at) WITH &&)
        """
        try:
            cur.execute(sql)
            print("Exclusion constraint created: no_machine_overlap")
        except Exception as e:
            print(f"Constraint may already exist: {e}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 3, attempt an overlapping insert
# MAGIC
# MAGIC Try to insert an operation that overlaps with an existing one on the same machine. The constraint should reject it.

# COMMAND ----------

import datetime

# Get an existing operation to create an overlap
ops = run_sql("""
SELECT op_id, machine_id, starts_at, ends_at
  FROM factory.operation
 WHERE machine_id IS NOT NULL AND starts_at IS NOT NULL AND ends_at IS NOT NULL
 LIMIT 1
""")

if not ops:
    print("No existing operations found")
else:
    op_id, machine_id, starts_at, ends_at = ops[0]

    # Try to insert an overlapping operation
    with connect() as conn:
        with conn.cursor() as cur:
            try:
                # Create an operation that overlaps
                overlap_start = starts_at
                overlap_end = ends_at + datetime.timedelta(hours=1)

                cur.execute("""
                INSERT INTO factory.operation
                  (op_id, wo_id, machine_id, seq, starts_at, ends_at, status)
                VALUES
                  (%s, %s, %s, %s, %s, %s, %s)
                """, ('OP-OVERLAP', 'WO-TEST', machine_id, 1, overlap_start, overlap_end, 'pending'))
                print("ERROR: Overlap should have been rejected!")
            except Exception as e:
                error_msg = str(e)
                if "no_machine_overlap" in error_msg:
                    print("Good: Overlap rejected by constraint")
                    print(f"  {error_msg[:100]}...")
                else:
                    print(f"Error: {error_msg[:100]}...")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 4, EXPLAIN shows constraint check
# MAGIC
# MAGIC Run EXPLAIN to see the constraint check in the query plan.

# COMMAND ----------

sql = "EXPLAIN INSERT INTO factory.operation VALUES ('test', 'wo', 'M-204', 1, now(), now() + interval '1 hour', 'pending')"

with connect() as conn:
    with conn.cursor() as cur:
        cur.execute(sql)
        rows = cur.fetchall()
        print("Query plan (should mention constraint):")
        for row in rows:
            print(f"  {row[0]}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## What you learned
# MAGIC
# MAGIC You created a GiST exclusion constraint that prevents overlapping time ranges for the same machine. This constraint is checked at the database level, not the application level, so no double-booking is possible.
# MAGIC
# MAGIC Next: **Watch the planner** uses EXPLAIN ANALYZE to understand when indexes matter.
