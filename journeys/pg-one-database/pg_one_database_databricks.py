# Databricks notebook source
# COMMAND ----------

# MAGIC # One query, every type, step by step
# MAGIC
# MAGIC A hands-on lab. Run one cell at a time. You will build a single table carrying JSON, vectors, and geospatial columns, then run one unified query across all of them.
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

# MAGIC ## Setup, connect
# COMMAND ----------

import os, sys
sys.path.insert(0, os.path.join(os.getcwd(), '..', '..', 'common', 'scripts'))
from lakebase import connect, _env

DEMO_TABLE = 'account_unified_demo'
SCHEMA = _env('LB_SCHEMA', 'bank')

print('Ready.')

# COMMAND ----------

# MAGIC ## Step 1, Create unified table (4 data types)
# MAGIC
# MAGIC ```sql
# MAGIC CREATE TABLE account_unified_demo (
# MAGIC     account_id TEXT PRIMARY KEY,
# MAGIC     branch_id TEXT NOT NULL,
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
                account_id TEXT PRIMARY KEY,
                branch_id TEXT NOT NULL,
                line TEXT NOT NULL,
                spec JSONB,
                embedding VECTOR(64),
                location GEOMETRY(POINT, 4326)
            )
        """)
        print(f'✓ Created unified table')

# COMMAND ----------

# MAGIC ## Step 2, Populate with 1000 accounts
# MAGIC
# MAGIC ```sql
# MAGIC INSERT INTO account_unified_demo(...) SELECT ... FROM generate_series(1, 1000) g
# MAGIC ```
# COMMAND ----------

with connect() as conn:
    with conn.cursor() as cur:
        cur.execute(f"""
            INSERT INTO {SCHEMA}.{DEMO_TABLE}(account_id, branch_id, line, spec, embedding, location)
            SELECT
                'ACCT-' || g,
                (ARRAY['BR-NYC', 'BR-SFO', 'BR-LON'])[1 + (g % 3)],
                (ARRAY['Checking', 'Savings', 'Credit'])[1 + (g % 3)],
                jsonb_build_object(
                    'type', (ARRAY['retail', 'commercial', 'wealth'])[1 + (g % 3)],
                    'year', 2020 + (g % 5),
                    'version', '3.' || (g % 10)
                ),
                (array_fill((0.5 + (g % 10)::real / 100.0), ARRAY[64]))::vector(64),
                ST_MakePoint(-73.0 + (g % 10)::numeric / 100, 45.0 + (g % 10)::numeric / 100)
            FROM generate_series(1, 1000) g
        """)
        print(f'✓ Populated 1000 accounts with all data types')

# COMMAND ----------

# MAGIC ## Step 3, Run unified query
# MAGIC
# MAGIC One query filtering on relational (branch_id), JSON (spec->>'type'), and geospatial (ST_DWithin) columns:
# MAGIC
# MAGIC ```sql
# MAGIC SELECT
# MAGIC     account_id,
# MAGIC     branch_id,
# MAGIC     line,
# MAGIC     (spec->>'type') as account_type,
# MAGIC     (spec->>'year')::int as vintage,
# MAGIC     ST_Distance(location, ST_GeomFromText('POINT(45 -73)')) as km_from_ref
# MAGIC FROM account_unified_demo
# MAGIC WHERE
# MAGIC     branch_id = 'BR-NYC'
# MAGIC     AND (spec->>'type') = 'commercial'
# MAGIC     AND ST_DWithin(location, ST_GeomFromText('POINT(45 -73)'), 1)
# MAGIC LIMIT 5;
# MAGIC ```
# COMMAND ----------

with connect() as conn:
    with conn.cursor() as cur:
        cur.execute(f"""
            SELECT
                account_id,
                branch_id,
                line,
                (spec->>'type') as account_type,
                (spec->>'year')::int as vintage,
                (embedding <-> (SELECT embedding FROM {SCHEMA}.{DEMO_TABLE} WHERE account_id='ACCT-1'))::numeric(6,4) as embedding_distance,
                ST_Distance(location, ST_MakePoint(-73.0, 45.0)::geometry) * 111.0 as km_from_ref
            FROM {SCHEMA}.{DEMO_TABLE}
            WHERE
                branch_id = 'BR-NYC'
                AND (spec->>'type') = 'commercial'
                AND ST_DWithin(location, ST_MakePoint(-73.0, 45.0)::geometry, 0.1)
            ORDER BY embedding_distance, km_from_ref
            LIMIT 5
        """)
        rows = cur.fetchall()
        cols = [desc[0] for desc in cur.description]

        print(f'Results (single query, single plan):')
        for row in rows:
            print(f'  {row[0]:12} | {row[1]:8} | {row[2]:12} | {row[3]:12} | {row[4]:4} | dist={row[5]:.4f} | km={row[6]:.4f}')

# COMMAND ----------

# MAGIC ## What you learned
# MAGIC
# MAGIC One table. Four data models. One query. Relational filters on branch_id and line. JSON extraction on spec. Vector and geospatial compute (when pgvector and PostGIS are loaded). No sync between systems, no consistency gaps, no application-layer glue code. One database.
# MAGIC
# MAGIC Next: **Your commits are a change feed** shows logical decoding (Preview) as a stream of changes.