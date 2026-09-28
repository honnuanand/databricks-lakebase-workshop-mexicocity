# Databricks notebook source
# COMMAND ----------

# MAGIC # One query, every type, step by step
# MAGIC
# MAGIC A hands-on lab. Run one cell at a time. You will build a single table carrying JSON, vectors, and geospatial columns, then run one unified query across all of them.
# MAGIC
# MAGIC **Before you start:** finish `00-setup/`.
# COMMAND ----------

# MAGIC ## Setup, connect
# COMMAND ----------

import os, sys
sys.path.insert(0, os.path.join(os.getcwd(), '..', '..', 'common', 'scripts'))
from lakebase import connect, _env

DEMO_TABLE = 'machine_unified_demo'
SCHEMA = _env('LB_SCHEMA', 'factory')

print('Ready.')

# COMMAND ----------

# MAGIC ## Step 1, Create unified table (4 data types)
# MAGIC
# MAGIC ```sql
# MAGIC CREATE TABLE machine_unified_demo (
# MAGIC     machine_id TEXT PRIMARY KEY,
# MAGIC     plant_id TEXT NOT NULL,
# MAGIC     line TEXT NOT NULL,
# MAGIC     spec JSONB,
# MAGIC     embedding VECTOR(64),
# MAGIC     location GEOMETRY(POINT, 4326)
# MAGIC );
# MAGIC ```
# COMMAND ----------

with connect() as conn:
    with conn.cursor() as cur:
        cur.execute("CREATE EXTENSION IF NOT EXISTS vector WITH SCHEMA public")
        cur.execute("CREATE EXTENSION IF NOT EXISTS postgis WITH SCHEMA public")
        cur.execute(f"DROP TABLE IF EXISTS {SCHEMA}.{DEMO_TABLE}")
        cur.execute(f"""
            CREATE TABLE {SCHEMA}.{DEMO_TABLE} (
                machine_id TEXT PRIMARY KEY,
                plant_id TEXT NOT NULL,
                line TEXT NOT NULL,
                spec JSONB,
                embedding VECTOR(64),
                location GEOMETRY(POINT, 4326)
            )
        """)
        print(f'✓ Created unified table')

# COMMAND ----------

# MAGIC ## Step 2, Populate with 1000 machines
# MAGIC
# MAGIC ```sql
# MAGIC INSERT INTO machine_unified_demo(...) SELECT ... FROM generate_series(1, 1000) g
# MAGIC ```
# COMMAND ----------

with connect() as conn:
    with conn.cursor() as cur:
        cur.execute(f"""
            INSERT INTO {SCHEMA}.{DEMO_TABLE}(machine_id, plant_id, line, spec, embedding, location)
            SELECT
                'M-' || g,
                (ARRAY['PL-DETROIT', 'PL-SHANGHAI', 'PL-FREMONT'])[1 + (g % 3)],
                (ARRAY['Stamping-A', 'Assembly-1', 'Finishing'])[1 + (g % 3)],
                jsonb_build_object(
                    'type', (ARRAY['CNC', 'Press', 'Robot'])[1 + (g % 3)],
                    'year', 2020 + (g % 5),
                    'version', '3.' || (g % 10)
                ),
                (array_fill((0.5 + (g % 10)::real / 100.0), ARRAY[64]))::vector(64),
                ST_MakePoint(-73.0 + (g % 10)::numeric / 100, 45.0 + (g % 10)::numeric / 100)
            FROM generate_series(1, 1000) g
        """)
        print(f'✓ Populated 1000 machines with all data types')

# COMMAND ----------

# MAGIC ## Step 3, Run unified query
# MAGIC
# MAGIC One query filtering on relational (plant_id), JSON (spec->>'type'), and geospatial (ST_DWithin) columns:
# MAGIC
# MAGIC ```sql
# MAGIC SELECT
# MAGIC     machine_id,
# MAGIC     plant_id,
# MAGIC     line,
# MAGIC     (spec->>'type') as machine_type,
# MAGIC     (spec->>'year')::int as manufacture_year,
# MAGIC     ST_Distance(location, ST_GeomFromText('POINT(45 -73)')) as km_from_ref
# MAGIC FROM machine_unified_demo
# MAGIC WHERE
# MAGIC     plant_id = 'PL-DETROIT'
# MAGIC     AND (spec->>'type') = 'Press'
# MAGIC     AND ST_DWithin(location, ST_GeomFromText('POINT(45 -73)'), 1)
# MAGIC LIMIT 5;
# MAGIC ```
# COMMAND ----------

with connect() as conn:
    with conn.cursor() as cur:
        cur.execute(f"""
            SELECT
                machine_id,
                plant_id,
                line,
                (spec->>'type') as machine_type,
                (spec->>'year')::int as manufacture_year,
                (embedding <-> (SELECT embedding FROM {SCHEMA}.{DEMO_TABLE} WHERE machine_id='M-1'))::numeric(6,4) as embedding_distance,
                ST_Distance(location, ST_MakePoint(-73.0, 45.0)::geometry) * 111.0 as km_from_ref
            FROM {SCHEMA}.{DEMO_TABLE}
            WHERE
                plant_id = 'PL-DETROIT'
                AND (spec->>'type') = 'Press'
                AND ST_DWithin(location, ST_MakePoint(-73.0, 45.0)::geometry, 0.1)
            ORDER BY embedding_distance, km_from_ref
            LIMIT 5
        """)
        rows = cur.fetchall()
        cols = [desc[0] for desc in cur.description]

        print(f'Results (single query, single plan):')
        for row in rows:
            print(f'  {row[0]:6} | {row[1]:12} | {row[2]:12} | {row[3]:6} | {row[4]:4} | dist={row[5]:.4f} | km={row[6]:.4f}')

# COMMAND ----------

# MAGIC ## What you learned
# MAGIC
# MAGIC One table. Four data models. One query. Relational filters on plant_id and line. JSON extraction on spec. Vector and geospatial compute (when pgvector and PostGIS are loaded). No sync between systems, no consistency gaps, no application-layer glue code. One database.
# MAGIC
# MAGIC Next: **Your commits are a change feed** shows logical decoding (Preview) as a stream of changes.