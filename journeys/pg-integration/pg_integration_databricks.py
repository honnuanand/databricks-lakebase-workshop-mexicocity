# Databricks notebook source
# MAGIC %md
# MAGIC # PG integration - step by step
# MAGIC
# MAGIC A hands-on lab. Run one cell at a time, read what happened, then move on. You will query the Postgres information_schema to discover tables, columns, and types, then verify that standard Postgres clients, ORMs, and BI tools work unmodified on Lakebase.
# MAGIC
# MAGIC **Before you start:** finish `00-setup/` so `LB_PROFILE`, `LB_PROJECT`, `LB_BRANCH`, `LB_SCHEMA` are set and the factory is loaded on your branch.

# COMMAND ----------

# MAGIC %md
# MAGIC ## Setup - connect to your branch

# COMMAND ----------

import os, sys
sys.path.insert(0, os.path.join(os.getcwd(), "..", "..", "common", "scripts"))
from lakebase import run_sql, _env
from collections import defaultdict

SCHEMA = os.environ.get("LB_SCHEMA", "bank")
print(f"Schema: {SCHEMA}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 1 - Discover tables via information_schema
# MAGIC
# MAGIC Standard Postgres queries work on Lakebase. Query the system catalog to discover tables. The SQL:
# MAGIC
# MAGIC ```sql
# MAGIC SELECT table_name FROM information_schema.tables
# MAGIC WHERE table_schema='factory' ORDER BY table_name;
# MAGIC ```

# COMMAND ----------

query = f"SELECT table_name FROM information_schema.tables WHERE table_schema='{SCHEMA}' ORDER BY table_name"
rows = run_sql(query)
tables = [row[0] for row in rows]
print(f"{len(tables)} tables discovered:")
for table in tables:
    print(f"  - {table}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 2 - Discover columns and types
# MAGIC
# MAGIC Query the information_schema to discover columns and their types. The SQL:
# MAGIC
# MAGIC ```sql
# MAGIC SELECT table_name, column_name, data_type
# MAGIC FROM information_schema.columns
# MAGIC WHERE table_schema='factory'
# MAGIC ORDER BY table_name, ordinal_position;
# MAGIC ```

# COMMAND ----------

query = (
    f"SELECT table_name, column_name, data_type "
    f"FROM information_schema.columns "
    f"WHERE table_schema='{SCHEMA}' "
    f"ORDER BY table_name, ordinal_position"
)
rows = run_sql(query)

# Group by table
by_table = defaultdict(list)
for table, column, dtype in rows:
    by_table[table].append((column, dtype))

print(f"{len(rows)} columns across {len(by_table)} tables")
for table in sorted(by_table.keys())[:3]:
    print(f"\n{table}:")
    for col, dtype in by_table[table][:5]:
        print(f"  {col}: {dtype}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 3 - Build a schema map (like a BI tool)
# MAGIC
# MAGIC Build a complete schema map from the information_schema. This is exactly what BI tools, ORMs, and data discovery tools do. The SQL:
# MAGIC
# MAGIC ```sql
# MAGIC SELECT table_name, column_name, data_type, is_nullable
# MAGIC FROM information_schema.columns
# MAGIC WHERE table_schema='factory'
# MAGIC ORDER BY table_name, ordinal_position;
# MAGIC ```

# COMMAND ----------

query = (
    f"SELECT table_name, column_name, data_type, is_nullable "
    f"FROM information_schema.columns "
    f"WHERE table_schema='{SCHEMA}' "
    f"ORDER BY table_name, ordinal_position"
)
rows = run_sql(query)

schema_map = defaultdict(list)
for table, column, dtype, nullable in rows:
    schema_map[table].append({
        "column": column,
        "type": dtype,
        "nullable": nullable == "YES"
    })

print(f"\n=== Factory Schema Map ===")
total_cols = 0
for table in sorted(schema_map.keys())[:3]:
    print(f"\nTABLE: {table}")
    for col_info in schema_map[table][:4]:
        col = col_info["column"]
        dtype = col_info["type"]
        null_marker = "" if col_info["nullable"] else " NOT NULL"
        print(f"  {col}: {dtype}{null_marker}")
        total_cols += 1

print(f"\n=== Statistics ===")
print(f"Total tables: {len(schema_map)}")
print(f"Total columns: {len(rows)}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 4 - Sample data to verify correctness
# MAGIC
# MAGIC Query a sample of rows from key tables to verify the schema and data match. The SQL (example for machine table):
# MAGIC
# MAGIC ```sql
# MAGIC SELECT * FROM bank.account LIMIT 3;
# MAGIC ```

# COMMAND ----------

# Sample machine table
rows = run_sql(f"SELECT * FROM {SCHEMA}.machine LIMIT 3")
print(f"Sample rows from account table:")
for row in rows:
    print(f"  {row[:3]}...")  # Show first 3 cols

# Sample work_order table
rows = run_sql(f"SELECT * FROM {SCHEMA}.work_order LIMIT 3")
print(f"\nSample rows from trade table:")
for row in rows:
    print(f"  {row[:3]}...")  # Show first 3 cols

# COMMAND ----------

# MAGIC %md
# MAGIC ## What you learned
# MAGIC
# MAGIC Lakebase is standard Postgres. You queried the system catalog (information_schema) exactly as you would on Postgres, discovered the full schema, built a schema map that a BI tool would build, and verified data correctness. Any Postgres client, ORM, or BI tool works unmodified.
# MAGIC
# MAGIC **Next:** Agent memory - two agents share state in one governed Lakebase table.
