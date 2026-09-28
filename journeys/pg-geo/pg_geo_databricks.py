# Databricks notebook source
# MAGIC %md
# MAGIC # Geospatial, step by step
# MAGIC
# MAGIC A hands-on lab. Run one cell at a time, read what happened, then move on. You will enable PostGIS, store locations as geographic points, query within distances, find nearest neighbors, and index spatial data.
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
# MAGIC ## Step 1, enable PostGIS and add geography columns
# MAGIC
# MAGIC PostGIS is a spatial extension for Postgres. Enable it, then add geography columns (POINT type) to plant, warehouse, and supplier tables. The SQL:
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

# Add geography columns to plant, warehouse, supplier if missing
tables = [
    ("factory.plant", "geo"),
    ("factory.warehouse", "geo"),
    ("factory.supplier", "geo")
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
# MAGIC ## Step 2, query warehouses within 100 km of a plant
# MAGIC
# MAGIC Use ST_DWithin() to find all warehouses within a distance (in meters) of a plant. The SQL:
# MAGIC
# MAGIC ```sql
# MAGIC SELECT warehouse_id, plant_id,
# MAGIC        ROUND((ST_Distance(geo, geography(POINT(lon, lat))) / 1000.0)::NUMERIC, 2) as distance_km
# MAGIC   FROM factory.warehouse
# MAGIC  WHERE ST_DWithin(geo, geography(POINT(lon, lat)), 100000)
# MAGIC  ORDER BY distance_km
# MAGIC  LIMIT 10
# MAGIC ```

# COMMAND ----------

# Get a sample plant
plants = run_sql("SELECT plant_id, lat, lon FROM factory.plant LIMIT 1")
if not plants:
    print("No plants found")
else:
    plant_id, plant_lat, plant_lon = plants[0]

    sql = f"""
    SELECT warehouse_id, plant_id,
           ROUND((ST_Distance(geo, ST_SetSRID(ST_MakePoint({plant_lon}, {plant_lat}), 4326)::geography) / 1000.0)::NUMERIC, 2) as distance_km
      FROM factory.warehouse
     WHERE ST_DWithin(geo, ST_SetSRID(ST_MakePoint({plant_lon}, {plant_lat}), 4326)::geography, 100000)
     ORDER BY distance_km
     LIMIT 10
    """
    rows = run_sql(sql)
    print(f"Warehouses within 100 km of {plant_id}:")
    for row in rows:
        print(f"  {row[0]} (distance: {row[2]} km)")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 3, find nearest suppliers to a plant
# MAGIC
# MAGIC Use the `<->` operator for nearest-neighbor queries (without a distance limit). The SQL:
# MAGIC
# MAGIC ```sql
# MAGIC SELECT supplier_id, name,
# MAGIC        ROUND((geo <-> geography(POINT(lon, lat)))::NUMERIC, 0) as distance_meters
# MAGIC   FROM factory.supplier
# MAGIC  ORDER BY geo <-> geography(POINT(lon, lat))
# MAGIC  LIMIT 3
# MAGIC ```

# COMMAND ----------

# Get a sample plant
plants = run_sql("SELECT plant_id, lat, lon FROM factory.plant LIMIT 1")
if not plants:
    print("No plants found")
else:
    plant_id, plant_lat, plant_lon = plants[0]

    sql = f"""
    SELECT supplier_id, name,
           ROUND((geo <-> ST_SetSRID(ST_MakePoint({plant_lon}, {plant_lat}), 4326)::geography)::NUMERIC, 0) as distance_meters
      FROM factory.supplier
     ORDER BY geo <-> ST_SetSRID(ST_MakePoint({plant_lon}, {plant_lat}), 4326)::geography
     LIMIT 3
    """
    rows = run_sql(sql)
    print(f"3 nearest suppliers to {plant_id}:")
    for row in rows:
        print(f"  {row[0]}: {row[1]} ({row[2]} meters)")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 4, create GiST indexes on geography columns
# MAGIC
# MAGIC GiST (Generalized Search Tree) indexes accelerate spatial queries. The SQL:
# MAGIC
# MAGIC ```sql
# MAGIC CREATE INDEX IF NOT EXISTS idx_plant_geo ON factory.plant USING gist(geo);
# MAGIC CREATE INDEX IF NOT EXISTS idx_warehouse_geo ON factory.warehouse USING gist(geo);
# MAGIC CREATE INDEX IF NOT EXISTS idx_supplier_geo ON factory.supplier USING gist(geo);
# MAGIC ```

# COMMAND ----------

sqls = [
    "CREATE INDEX IF NOT EXISTS idx_plant_geo ON factory.plant USING gist(geo)",
    "CREATE INDEX IF NOT EXISTS idx_warehouse_geo ON factory.warehouse USING gist(geo)",
    "CREATE INDEX IF NOT EXISTS idx_supplier_geo ON factory.supplier USING gist(geo)"
]

with connect() as conn:
    with conn.cursor() as cur:
        for sql in sqls:
            cur.execute(sql)

print("GiST indexes created on plant, warehouse, supplier")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 5, EXPLAIN shows spatial index usage
# MAGIC
# MAGIC Show that EXPLAIN reveals index usage for spatial queries. The SQL:
# MAGIC
# MAGIC ```sql
# MAGIC EXPLAIN (ANALYZE, BUFFERS)
# MAGIC SELECT supplier_id FROM factory.supplier
# MAGIC  ORDER BY geo <-> geography(POINT(lon, lat))
# MAGIC  LIMIT 3
# MAGIC ```

# COMMAND ----------

plants = run_sql("SELECT plant_id, lat, lon FROM factory.plant LIMIT 1")
if not plants:
    print("No plants found")
else:
    plant_lat, plant_lon = plants[0][1], plants[0][2]

    sql = f"""
    EXPLAIN (ANALYZE, BUFFERS)
    SELECT supplier_id FROM factory.supplier
     ORDER BY geo <-> ST_SetSRID(ST_MakePoint({plant_lon}, {plant_lat}), 4326)::geography
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
# MAGIC You enabled PostGIS and mastered spatial queries: ST_DWithin() for radius searches, the `<->` operator for nearest neighbors, and GiST indexes for performance. Supply chain locations are now queryable by distance.
# MAGIC
# MAGIC Next: **Search, three ways** uses full-text search, fuzzy matching, and hybrid ranking.
