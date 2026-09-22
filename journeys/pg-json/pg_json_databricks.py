# Databricks notebook source
# MAGIC %md
# MAGIC # JSON documents, step by step
# MAGIC
# MAGIC A hands-on lab. Run one cell at a time, read what happened, then move on. You will query JSONB specs with containment, path extraction, and GIN indexes.
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
# MAGIC ## Step 1, inspect JSONB specs on parts
# MAGIC
# MAGIC Each part has a `spec` column (JSONB). The contents vary: one part might have `{"load_capacity_kg": 500, "material": "steel"}`, another might have `{"tensile_strength_mpa": 1200, "coating": "zinc"}`. No schema migration needed when a new part type arrives with new fields. The SQL:
# MAGIC
# MAGIC ```sql
# MAGIC SELECT part_id, name, spec FROM factory.part LIMIT 3
# MAGIC ```

# COMMAND ----------

sql = "SELECT part_id, name, spec FROM factory.part LIMIT 3"
rows = run_sql(sql)
print("Sample part specs (JSONB, varying fields):")
for row in rows:
    print(f"  {row[0]}: {row[1]}")
    print(f"    spec: {row[2]}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 2, use containment operator (@>)
# MAGIC
# MAGIC The `@>` operator asks "does the JSON document on the left contain the JSON sub-document on the right?" This is the workhorse for spec matching. Find parts that match a spec. The SQL:
# MAGIC
# MAGIC ```sql
# MAGIC SELECT part_id, name, spec
# MAGIC   FROM factory.part
# MAGIC  WHERE spec @> '{"material": "steel"}'
# MAGIC  LIMIT 5
# MAGIC ```

# COMMAND ----------

sql = """
SELECT part_id, name, spec
  FROM factory.part
 WHERE spec @> '{"material": "steel"}'
 LIMIT 5
"""
rows = run_sql(sql)
print("Parts with material='steel' (using @> containment):")
for row in rows:
    print(f"  {row[0]}: {row[1]}")
    print(f"    spec: {row[2]}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 3, use path extraction (#>>) and key exists (?)
# MAGIC
# MAGIC The `#>>` operator extracts a value from a path in the JSON. Use it to extract a field for filtering or display. The `?` operator checks if a key exists. Together, they let you filter and display JSON fields like columns. The SQL:
# MAGIC
# MAGIC ```sql
# MAGIC SELECT part_id, name, spec #>> '{material}' as material
# MAGIC   FROM factory.part
# MAGIC  WHERE spec ? 'material'
# MAGIC  LIMIT 5
# MAGIC ```

# COMMAND ----------

sql = """
SELECT part_id, name, spec #>> '{material}' as material
  FROM factory.part
 WHERE spec ? 'material'
 LIMIT 5
"""
rows = run_sql(sql)
print("Extracted material field from JSONB spec:")
for row in rows:
    print(f"  {row[0]}: material={row[2]}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 4, create a GIN index on JSONB
# MAGIC
# MAGIC JSONB queries are fast even without an index. With a GIN (Generalized Inverted Index) on the JSONB column, they are faster. The SQL:
# MAGIC
# MAGIC ```sql
# MAGIC CREATE INDEX IF NOT EXISTS idx_part_spec_gin ON factory.part
# MAGIC   USING gin(spec jsonb_path_ops)
# MAGIC ```

# COMMAND ----------

sql = "CREATE INDEX IF NOT EXISTS idx_part_spec_gin ON factory.part USING gin(spec jsonb_path_ops)"
with connect() as conn:
    with conn.cursor() as cur:
        cur.execute(sql)
print("GIN index created on factory.part(spec)")
print("(Queries will use the index if beneficial)")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 5, realistic compliance query: parts for harsh environment
# MAGIC
# MAGIC Find parts suitable for a harsh environment (must be steel or stainless). The SQL:
# MAGIC
# MAGIC ```sql
# MAGIC SELECT part_id, name, spec
# MAGIC   FROM factory.part
# MAGIC  WHERE spec @> '{"material": "steel"}'
# MAGIC     OR spec @> '{"material": "stainless"}'
# MAGIC  LIMIT 10
# MAGIC ```

# COMMAND ----------

sql = """
SELECT part_id, name, spec
  FROM factory.part
 WHERE spec @> '{"material": "steel"}'
    OR spec @> '{"material": "stainless"}'
 LIMIT 10
"""
rows = run_sql(sql)
print("Parts suitable for harsh environment (steel or stainless):")
for row in rows:
    print(f"  {row[0]}: {row[1]}")
    if row[2]:
        print(f"    {row[2]}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## What you learned
# MAGIC
# MAGIC You mastered JSONB: the containment operator (@>) for semantic matching, path extraction (#>>) and key checks (?) for drill-down, and GIN indexes for speed. Postgres gives you flexibility of schema-less storage with the power of a relational query engine.
# MAGIC
# MAGIC Next: **Geospatial queries** use PostGIS to find locations within a distance, nearest neighbors, and spatial indexes.
