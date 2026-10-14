# Databricks notebook source
# MAGIC %md
# MAGIC # PG integration - step by step
# MAGIC
# MAGIC A hands-on lab. Run one cell at a time, read what happened, then move on. You will query the Postgres information_schema to discover tables, columns, and types, then verify that standard Postgres clients, ORMs, and BI tools work unmodified on Lakebase.
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
# MAGIC WHERE table_schema='bank' ORDER BY table_name;
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
# MAGIC WHERE table_schema='bank'
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
# MAGIC WHERE table_schema='bank'
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

print(f"\n=== Bank Schema Map ===")
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
# MAGIC Query a sample of rows from key tables to verify the schema and data match. The SQL (example for account table):
# MAGIC
# MAGIC ```sql
# MAGIC SELECT * FROM bank.account LIMIT 3;
# MAGIC ```

# COMMAND ----------

# Sample account table
rows = run_sql(f"SELECT * FROM {SCHEMA}.account LIMIT 3")
print(f"Sample rows from account table:")
for row in rows:
    print(f"  {row[:3]}...")  # Show first 3 cols

# Sample trade table
rows = run_sql(f"SELECT * FROM {SCHEMA}.trade LIMIT 3")
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
