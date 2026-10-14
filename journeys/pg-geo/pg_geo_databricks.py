# Databricks notebook source
# MAGIC %md
# MAGIC # Geospatial, step by step
# MAGIC
# MAGIC A hands-on lab. Run one cell at a time, read what happened, then move on. You will enable PostGIS, store locations as geographic points, query within distances, find nearest neighbors, and index spatial data.
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
# MAGIC ## Step 1, enable PostGIS and add geography columns
# MAGIC
# MAGIC PostGIS is a spatial extension for Postgres. Enable it, then add geography columns (POINT type) to branch, custodian, and counterparty tables. The SQL:
# MAGIC
# MAGIC ```sql
# MAGIC CREATE EXTENSION IF NOT EXISTS postgis CASCADE
# MAGIC ```

# COMMAND ----------

with connect() as conn:
    with conn.cursor() as cur:
        try:
            cur.execute("CREATE EXTENSION IF NOT EXISTS postgis CASCADE")
            print("PostGIS extension enabled")
        except Exception as e:
            print(f"Warning: PostGIS may not be available: {e}")

# Add geography columns to branch, custodian, counterparty if missing
tables = [
    ("bank.branch", "geo"),
    ("bank.custodian", "geo"),
    ("bank.counterparty", "geo")
]

with connect() as conn:
    with conn.cursor() as cur:
        for table, col in tables:
            try:
                cur.execute(f"ALTER TABLE {table} ADD COLUMN {col} GEOGRAPHY(POINT) DEFAULT NULL")
                print(f"Added {col} column to {table}")
            except:
                pass  # Column may already exist

        # Populate geography columns from lat/lon
        for table, col in tables:
            try:
                cur.execute(f"UPDATE {table} SET {col} = ST_SetSRID(ST_MakePoint(lon, lat), 4326)::geography WHERE {col} IS NULL AND lat IS NOT NULL AND lon IS NOT NULL")
                print(f"Populated {col} on {table}")
            except:
                pass

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 2, query custodians within 100 km of a branch
# MAGIC
# MAGIC Use ST_DWithin() to find all custodians within a distance (in meters) of a branch. The SQL:
# MAGIC
# MAGIC ```sql
# MAGIC SELECT custodian_id, branch_id,
# MAGIC        ROUND((ST_Distance(geo, geography(POINT(lon, lat))) / 1000.0)::NUMERIC, 2) as distance_km
# MAGIC   FROM bank.custodian
# MAGIC  WHERE ST_DWithin(geo, geography(POINT(lon, lat)), 100000)
# MAGIC  ORDER BY distance_km
# MAGIC  LIMIT 10
# MAGIC ```

# COMMAND ----------

# Get a sample branch
branches = run_sql("SELECT branch_id, lat, lon FROM bank.branch LIMIT 1")
if not branches:
    print("No branches found")
else:
    branch_id, branch_lat, branch_lon = branches[0]

    sql = f"""
    SELECT custodian_id, branch_id,
           ROUND((ST_Distance(geo, ST_SetSRID(ST_MakePoint({branch_lon}, {branch_lat}), 4326)::geography) / 1000.0)::NUMERIC, 2) as distance_km
      FROM bank.custodian
     WHERE ST_DWithin(geo, ST_SetSRID(ST_MakePoint({branch_lon}, {branch_lat}), 4326)::geography, 100000)
     ORDER BY distance_km
     LIMIT 10
    """
    rows = run_sql(sql)
    print(f"Custodians within 100 km of {branch_id}:")
    for row in rows:
        print(f"  {row[0]} (distance: {row[2]} km)")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 3, find nearest counterparties to a branch
# MAGIC
# MAGIC Use the `<->` operator for nearest-neighbor queries (without a distance limit). The SQL:
# MAGIC
# MAGIC ```sql
# MAGIC SELECT counterparty_id, name,
# MAGIC        ROUND((geo <-> geography(POINT(lon, lat)))::NUMERIC, 0) as distance_meters
# MAGIC   FROM bank.counterparty
# MAGIC  ORDER BY geo <-> geography(POINT(lon, lat))
# MAGIC  LIMIT 3
# MAGIC ```

# COMMAND ----------

# Get a sample branch
branches = run_sql("SELECT branch_id, lat, lon FROM bank.branch LIMIT 1")
if not branches:
    print("No branches found")
else:
    branch_id, branch_lat, branch_lon = branches[0]

    sql = f"""
    SELECT counterparty_id, name,
           ROUND((geo <-> ST_SetSRID(ST_MakePoint({branch_lon}, {branch_lat}), 4326)::geography)::NUMERIC, 0) as distance_meters
      FROM bank.counterparty
     ORDER BY geo <-> ST_SetSRID(ST_MakePoint({branch_lon}, {branch_lat}), 4326)::geography
     LIMIT 3
    """
    rows = run_sql(sql)
    print(f"3 nearest counterparties to {branch_id}:")
    for row in rows:
        print(f"  {row[0]}: {row[1]} ({row[2]} meters)")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 4, create GiST indexes on geography columns
# MAGIC
# MAGIC GiST (Generalized Search Tree) indexes accelerate spatial queries. The SQL:
# MAGIC
# MAGIC ```sql
# MAGIC CREATE INDEX IF NOT EXISTS idx_branch_geo ON bank.branch USING gist(geo);
# MAGIC CREATE INDEX IF NOT EXISTS idx_custodian_geo ON bank.custodian USING gist(geo);
# MAGIC CREATE INDEX IF NOT EXISTS idx_counterparty_geo ON bank.counterparty USING gist(geo);
# MAGIC ```

# COMMAND ----------

sqls = [
    "CREATE INDEX IF NOT EXISTS idx_branch_geo ON bank.branch USING gist(geo)",
    "CREATE INDEX IF NOT EXISTS idx_custodian_geo ON bank.custodian USING gist(geo)",
    "CREATE INDEX IF NOT EXISTS idx_counterparty_geo ON bank.counterparty USING gist(geo)"
]

with connect() as conn:
    with conn.cursor() as cur:
        for sql in sqls:
            cur.execute(sql)

print("GiST indexes created on branch, custodian, counterparty")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 5, EXPLAIN shows spatial index usage
# MAGIC
# MAGIC Show that EXPLAIN reveals index usage for spatial queries. The SQL:
# MAGIC
# MAGIC ```sql
# MAGIC EXPLAIN (ANALYZE, BUFFERS)
# MAGIC SELECT counterparty_id FROM bank.counterparty
# MAGIC  ORDER BY geo <-> geography(POINT(lon, lat))
# MAGIC  LIMIT 3
# MAGIC ```

# COMMAND ----------

branches = run_sql("SELECT branch_id, lat, lon FROM bank.branch LIMIT 1")
if not branches:
    print("No branches found")
else:
    branch_lat, branch_lon = branches[0][1], branches[0][2]

    sql = f"""
    EXPLAIN (ANALYZE, BUFFERS)
    SELECT counterparty_id FROM bank.counterparty
     ORDER BY geo <-> ST_SetSRID(ST_MakePoint({branch_lon}, {branch_lat}), 4326)::geography
     LIMIT 3
    """
    rows = run_sql(sql)
    print("Query plan (look for 'Index Scan' or 'gist'):")
    for row in rows:
        print(f"  {row[0]}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## What you learned
# MAGIC
# MAGIC You enabled PostGIS and mastered spatial queries: ST_DWithin() for radius searches, the `<->` operator for nearest neighbors, and GiST indexes for performance. Financial network locations are now queryable by distance.
# MAGIC
# MAGIC Next: **Search, three ways** uses full-text search, fuzzy matching, and hybrid ranking.
