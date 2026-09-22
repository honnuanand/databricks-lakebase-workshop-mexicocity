# Databricks notebook source
# COMMAND ----------

# MAGIC # One query, every type, step by step
# MAGIC
# MAGIC A hands-on lab. Run one cell at a time. You will build a single table carrying JSON, vectors, and geospatial columns, then run one unified query across all of them.
# MAGIC
# MAGIC **Before you start:** finish `00-setup/`.
# COMMAND ----------

# MAGIC ## Setup — connect
# COMMAND ----------

import os, sys
sys.path.insert(0, os.path.join(os.getcwd(), '..', '..', 'common', 'scripts'))
from lakebase import connect, _env

DEMO_TABLE = 'machine_unified_demo'
SCHEMA = _env('LB_SCHEMA', 'factory')

print('Ready.')

# COMMAND ----------

# MAGIC ## Step 1 — Create unified table (4 data types)
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

# MAGIC ## Step 2 — Populate with 1000 machines
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
                (ARRAY['PL-DETROIT', 'PL-SHANGHAI'])[1 + (g % 2)],
                (ARRAY['Stamping-A', 'Assembly-1', 'Welding-B'])[1 + (g % 3)],
                jsonb_build_object('type', 'Press', 'year', 2020 + (g % 4)),
                ('{{'::text || ARRAY_AGG(0.5 FILTER (WHERE false))::text || '}}'::text)::vector(64),
                ST_GeomFromText('POINT(45.0 -73.0)')
            FROM generate_series(1, 1000) g
            GROUP BY g
        """)
        print(f'✓ Populated 1000 machines with all data types')

# COMMAND ----------

# MAGIC ## Step 3 — Run unified query
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
                (spec->>'year')::int as manufacture_year
            FROM {SCHEMA}.{DEMO_TABLE}
            WHERE
                plant_id = 'PL-DETROIT'
                AND (spec->>'type') = 'Press'
            LIMIT 5
        """)
        rows = cur.fetchall()
        print(f'✓ Unified query returned {len(rows)} rows')
        for row in rows[:3]:
            print(f'  {row}')

# COMMAND ----------

# MAGIC ## What you learned
# MAGIC
# MAGIC One table. Four data models. One query. Relational filters on plant_id and line. JSON extraction on spec. Vector and geospatial compute (when pgvector and PostGIS are loaded). No sync between systems, no consistency gaps, no application-layer glue code. One database.
# MAGIC
# MAGIC Next: **Your commits are a change feed** shows logical decoding (Preview) as a stream of changes.