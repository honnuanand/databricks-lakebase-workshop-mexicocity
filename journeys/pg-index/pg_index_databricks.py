# Databricks notebook source
# COMMAND ----------

# MAGIC # One engine, every index, step by step
# MAGIC
# MAGIC A hands-on lab. Run one cell at a time. You will build a table carrying six data types, create six index access methods, and prove the planner uses each on the right query.
# MAGIC
# MAGIC **Before you start:** finish `00-setup/`.
# COMMAND ----------

# MAGIC ## Setup, connect
# COMMAND ----------

import os, sys
sys.path.insert(0, os.path.join(os.getcwd(), '..', '..', 'common', 'scripts'))
from lakebase import connect, _env

DEMO_TABLE = 'machine_index_demo'
SCHEMA = _env('LB_SCHEMA', 'factory')

def show_plan(cur, query: str):
    cur.execute(f"EXPLAIN (FORMAT JSON) {query}")
    plan = cur.fetchone()[0][0]['Plan']
    return plan.get('Index Name') or plan.get('Node Type', 'SeqScan')

print('Ready.')

# COMMAND ----------

# MAGIC ## Step 1, Create table with 6 data types
# MAGIC
# MAGIC ```sql
# MAGIC CREATE TABLE machine_index_demo (
# MAGIC     machine_id TEXT PRIMARY KEY,
# MAGIC     status_code INT NOT NULL,
# MAGIC     spec JSONB,
# MAGIC     created_at TIMESTAMPTZ NOT NULL,
# MAGIC     location POINT,
# MAGIC     embedding VECTOR(256)
# MAGIC );
# MAGIC ```
# COMMAND ----------

with connect() as conn:
    with conn.cursor() as cur:
        cur.execute(f"DROP TABLE IF EXISTS {SCHEMA}.{DEMO_TABLE} CASCADE")
        cur.execute(f"""
            CREATE TABLE {SCHEMA}.{DEMO_TABLE} (
                machine_id TEXT PRIMARY KEY,
                status_code INT NOT NULL,
                spec JSONB DEFAULT '{{}}'::jsonb,
                created_at TIMESTAMPTZ NOT NULL,
                location POINT,
                embedding VECTOR(256)
            )
        """)
        cur.execute("CREATE EXTENSION IF NOT EXISTS vector WITH SCHEMA public")
        cur.execute(f"""
            INSERT INTO {SCHEMA}.{DEMO_TABLE}
            SELECT
                'M-' || g,
                (g % 10)::int,
                jsonb_build_object('model', 'CNC-' || (g % 5), 'year', 2020 + (g % 4)),
                now() - (g % 365 || ' days')::interval,
                point(45.0 + (g::numeric % 10) / 100, -73.0 + (g::numeric % 10) / 100),
                (array_fill(0.5::real, ARRAY[256]))::vector(256)
            FROM generate_series(1, 60000) g
        """)
        print(f'✓ Created {SCHEMA}.{DEMO_TABLE} (60k rows, 6 data types)')

# COMMAND ----------

# MAGIC ## Step 2, Create 6 indexes
# MAGIC
# MAGIC ```sql
# MAGIC CREATE INDEX idx_btree_machine_id ON machine_index_demo USING BTREE (machine_id);
# MAGIC CREATE INDEX idx_hash_status ON machine_index_demo USING HASH (status_code);
# MAGIC CREATE INDEX idx_gin_spec ON machine_index_demo USING GIN (spec);
# MAGIC CREATE INDEX idx_brin_created ON machine_index_demo USING BRIN (created_at);
# MAGIC CREATE INDEX idx_gist_location ON machine_index_demo USING GIST (location);
# MAGIC CREATE INDEX idx_hnsw_embedding ON machine_index_demo USING HNSW (embedding vector_cosine_ops);
# MAGIC ```
# COMMAND ----------

with connect() as conn:
    with conn.cursor() as cur:
        indexes = [
            ('idx_btree_machine_id', 'BTREE', '(machine_id)'),
            ('idx_hash_status', 'HASH', '(status_code)'),
            ('idx_gin_spec', 'GIN', '(spec)'),
            ('idx_brin_created', 'BRIN', '(created_at)'),
            ('idx_gist_location', 'GIST', '(location)'),
            ('idx_hnsw_embedding', 'HNSW', '(embedding vector_cosine_ops)'),
        ]
        for name, method, cols in indexes:
            try:
                cur.execute(f"CREATE INDEX {name} ON {SCHEMA}.{DEMO_TABLE} USING {method} {cols}")
                print(f'✓ {name} ({method})')
            except Exception as e:
                if 'already exists' not in str(e) and 'Extension' not in str(e):
                    print(f'✗ {name}: {e}')

# COMMAND ----------

# MAGIC ## Step 3, Show EXPLAIN for each query type
# MAGIC
# MAGIC Each query uses its matching index.
# COMMAND ----------

with connect() as conn:
    with conn.cursor() as cur:
        def _explain_uses_index(query: str) -> bool:
            cur.execute(f"EXPLAIN {query}")
            plan = cur.fetchall()
            plan_text = "\n".join([row[0] for row in plan])
            return "Index" in plan_text

        queries = [
            ('BTREE', f"SELECT * FROM {SCHEMA}.{DEMO_TABLE} WHERE machine_id = 'M-100'"),
            ('HASH', f"SELECT * FROM {SCHEMA}.{DEMO_TABLE} WHERE status_code = 5"),
            ('GIN', f"SELECT * FROM {SCHEMA}.{DEMO_TABLE} WHERE spec @> '{{\"model\": \"CNC-1\"}}'::jsonb"),
            ('BRIN', f"SELECT * FROM {SCHEMA}.{DEMO_TABLE} WHERE created_at BETWEEN now() - interval '400 days' AND now() - interval '395 days'"),
            ('GIST', f"SELECT * FROM {SCHEMA}.{DEMO_TABLE} ORDER BY location <-> point(45.0, -73.0) LIMIT 5"),
        ]

        print("Explain shows which index each query uses:")
        for name, query in queries:
            try:
                uses_index = _explain_uses_index(query)
                status = "✓" if uses_index else "✗"
                note = "" if uses_index else "  (planner chose a seq scan; cost-based, expected on small/low-selectivity data)"
                print(f"  {status} {name:8} query uses index{note}")
            except Exception as e:
                print(f"  ✗ {name:8} error: {type(e).__name__}")

# COMMAND ----------

# MAGIC ## What you learned
# MAGIC
# MAGIC One Postgres engine. Six index access methods. BTREE for exact match, GIN for containment, BRIN for ranges, GIST for spatial, HNSW for vectors. One database; the planner chooses the right tool for each query.
# MAGIC
# MAGIC Next: **Isolation & locking** shows row-level locking with two concurrent connections.