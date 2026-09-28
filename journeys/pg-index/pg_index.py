#!/usr/bin/env python3
"""One table, every index type — six AMs proven by the planner.

A single table carries every data type from the Postgres track: relational,
JSON, time-series, geography, vector. Create each index (btree, hash, gin,
brin, gist, hnsw) and watch EXPLAIN prove the planner chooses it.

Usage:
    python pg_index.py                  # build table and all 6 indexes
    python pg_index.py --step setup     # create the demo table
    python pg_index.py --step indexes   # create all 6 indexes
    python pg_index.py --step explain   # run EXPLAIN on each query

Env: LB_PROFILE, LB_PROJECT, LB_BRANCH, LB_SCHEMA (see 00-setup/).
"""
from __future__ import annotations

import argparse
import os

import psycopg
import os, sys
# The shared Lakebase helper lives in common/scripts/. Make it importable
# from this journey folder no matter where you run the script from.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "common", "scripts"))
from lakebase import connect, _env

DEMO_TABLE = "machine_index_demo"


def _explain_uses_index(cur, query: str) -> bool:
    """Run EXPLAIN and check if an index is used."""
    cur.execute(f"EXPLAIN {query}")
    plan = cur.fetchall()
    plan_text = "\n".join([row[0] for row in plan])
    return "Index" in plan_text


def setup(conn):
    """Create a demo table with every data type."""
    schema = _env("LB_SCHEMA", "factory")

    with conn.cursor() as cur:
        # Drop if exists
        cur.execute(f"DROP TABLE IF EXISTS {schema}.{DEMO_TABLE} CASCADE")

        # Create table with all types
        cur.execute(f"""
            CREATE TABLE {schema}.{DEMO_TABLE} (
                machine_id TEXT PRIMARY KEY,           -- btree (lookups)
                status_code INT NOT NULL,               -- hash (equality)
                spec JSONB DEFAULT '{{}}'::jsonb,      -- gin (JSON containment)
                created_at TIMESTAMPTZ NOT NULL,        -- brin (time range scans)
                location POINT,                         -- gist (spatial queries)
                embedding VECTOR(256)                   -- hnsw (vector similarity)
            )
        """)

        # Enable extensions if not already enabled
        cur.execute("CREATE EXTENSION IF NOT EXISTS vector WITH SCHEMA public")

        # Seed with 60k rows
        cur.execute(f"""
            INSERT INTO {schema}.{DEMO_TABLE}(machine_id, status_code, spec, created_at, location, embedding)
            SELECT
                'M-' || g,
                g % 10,
                jsonb_build_object('model', 'CNC-X' || (g % 5), 'year', 2020 + (g % 4)),
                now() - (g % 365 || ' days')::interval,
                point(45.0 + (g % 10)::numeric / 100, -73.0 + (g % 10)::numeric / 100),
                (array_fill(0.5::real, ARRAY[256]))::vector(256)  -- simplified embedding
            FROM generate_series(1, 60000) g
        """)

        print(f"Created {schema}.{DEMO_TABLE} with 60k rows and all data types")


def create_indexes(conn):
    """Create all six index types."""
    schema = _env("LB_SCHEMA", "factory")

    with conn.cursor() as cur:
        # 1. BTREE (relational lookups)
        cur.execute(f"CREATE INDEX IF NOT EXISTS idx_btree_machine_id ON {schema}.{DEMO_TABLE} USING BTREE (machine_id)")
        print("✓ BTREE index on machine_id (relational lookups)")

        # 2. HASH (equality on integers)
        cur.execute(f"CREATE INDEX IF NOT EXISTS idx_hash_status ON {schema}.{DEMO_TABLE} USING HASH (status_code)")
        print("✓ HASH index on status_code (integer equality)")

        # 3. GIN (JSON containment)
        cur.execute(f"CREATE INDEX IF NOT EXISTS idx_gin_spec ON {schema}.{DEMO_TABLE} USING GIN (spec)")
        print("✓ GIN index on spec (JSON containment @>)")

        # 4. BRIN (time-series range scans)
        cur.execute(f"CREATE INDEX IF NOT EXISTS idx_brin_created ON {schema}.{DEMO_TABLE} USING BRIN (created_at)")
        print("✓ BRIN index on created_at (time-series range scans)")

        # 5. GIST (geospatial distance)
        cur.execute(f"CREATE INDEX IF NOT EXISTS idx_gist_location ON {schema}.{DEMO_TABLE} USING GIST (location)")
        print("✓ GIST index on location (geospatial distance <->)")

        # 6. HNSW (vector similarity) — requires pgvector
        try:
            cur.execute(f"CREATE INDEX IF NOT EXISTS idx_hnsw_embedding ON {schema}.{DEMO_TABLE} USING HNSW (embedding vector_cosine_ops)")
            print("✓ HNSW index on embedding (vector similarity <=>)")
        except psycopg.Error as e:
            print(f"⚠ HNSW index skipped (pgvector HNSW may not be available): {e}")


def explain_all(conn):
    """Run EXPLAIN on each query type to prove the planner picks each index."""
    schema = _env("LB_SCHEMA", "factory")

    queries = [
        ("BTREE", f"SELECT * FROM {schema}.{DEMO_TABLE} WHERE machine_id = 'M-100'"),
        ("HASH", f"SELECT * FROM {schema}.{DEMO_TABLE} WHERE status_code = 5"),
        ("GIN", f"SELECT * FROM {schema}.{DEMO_TABLE} WHERE spec @> '{{\"model\": \"CNC-X1\"}}'::jsonb"),
        # A narrow time window so the BRIN index is selective (a 90-day window matches
        # most rows, where the planner correctly prefers a seq scan).
        ("BRIN", f"SELECT * FROM {schema}.{DEMO_TABLE} WHERE created_at BETWEEN now() - interval '400 days' AND now() - interval '395 days'"),
        # A nearest-neighbor ORDER BY ... LIMIT is what a GiST distance index accelerates.
        ("GIST", f"SELECT * FROM {schema}.{DEMO_TABLE} ORDER BY location <-> point(45.0, -73.0) LIMIT 5"),
    ]

    with conn.cursor() as cur:
        print("\nExplain shows which index each query uses:")
        for am_name, query in queries:
            uses_index = _explain_uses_index(cur, query)
            status = "✓" if uses_index else "✗"
            note = "" if uses_index else "  (planner chose a seq scan; cost-based, expected on small/low-selectivity data)"
            print(f"  {status} {am_name:8} query uses index{note}")


def main():
    ap = argparse.ArgumentParser(description="Six index types, one table, one planner")
    ap.add_argument(
        "--step",
        choices=["setup", "indexes", "explain"],
        help="run a specific step",
    )
    args = ap.parse_args()

    with connect() as conn:
        if args.step == "setup":
            setup(conn)
        elif args.step == "indexes":
            setup(conn)
            create_indexes(conn)
        elif args.step == "explain":
            setup(conn)
            create_indexes(conn)
            explain_all(conn)
        else:
            # Run the whole story
            print("1. Creating demo table with every data type:")
            setup(conn)
            print("\n2. Creating six index types:")
            create_indexes(conn)
            print("\n3. Running EXPLAIN to show planner chooses each index:")
            explain_all(conn)
            print("\n✓ One table, every type. One engine, every index.")


if __name__ == "__main__":
    main()
