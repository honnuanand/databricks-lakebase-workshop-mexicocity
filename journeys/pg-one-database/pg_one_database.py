#!/usr/bin/env python3
"""One query, every type, relational + JSON + vector + geo unified.

A single table spans all four data models: relational columns, JSONB specs,
vector embeddings, and geospatial coordinates. One SELECT across all four
runs in a single execution plan, single snapshot, single transaction.

Proves: not four products bolted together; one engine.

Usage:
    python pg_one_database.py            # build table and run the unified query
    python pg_one_database.py --step sql # show the SQL (no exec)

Env: LB_PROFILE, LB_PROJECT, LB_BRANCH, LB_SCHEMA (see 00-setup/).
"""
from __future__ import annotations

import argparse

import psycopg
import os, sys
# The shared Lakebase helper lives in common/scripts/. Make it importable
# from this journey folder no matter where you run the script from.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "common", "scripts"))
from lakebase import connect, _env

DEMO_TABLE = "account_unified_demo"


def setup(conn):
    """Create a table with all four data types."""
    schema = _env("LB_SCHEMA", "bank")

    with conn.cursor() as cur:
        # Enable extensions
        cur.execute("CREATE EXTENSION IF NOT EXISTS vector WITH SCHEMA public")
        cur.execute("CREATE EXTENSION IF NOT EXISTS postgis WITH SCHEMA public")

        # Drop if exists
        cur.execute(f"DROP TABLE IF EXISTS {schema}.{DEMO_TABLE} CASCADE")

        # Create unified table
        cur.execute(f"""
            CREATE TABLE {schema}.{DEMO_TABLE} (
                -- Relational
                account_id TEXT PRIMARY KEY,
                branch_id TEXT NOT NULL,
                line TEXT NOT NULL,

                -- JSON: flexible spec sheet
                spec JSONB DEFAULT '{{}}'::jsonb,

                -- Vector: embedding for account similarity
                embedding VECTOR(64),

                -- Geospatial: branch location
                location GEOMETRY(POINT, 4326)
            )
        """)

        # Seed with 1000 accounts
        cur.execute(f"""
            INSERT INTO {schema}.{DEMO_TABLE}(account_id, branch_id, line, spec, embedding, location)
            SELECT
                'ACCT-' || g,
                (ARRAY['BR-NYC', 'BR-SFO', 'BR-LON'])[1 + (g % 3)],
                (ARRAY['Checking', 'Savings', 'Credit'])[1 + (g % 3)],
                jsonb_build_object(
                    'type', (ARRAY['retail', 'commercial', 'wealth'])[1 + (g % 3)],
                    'year', 2020 + (g % 5),
                    'version', '3.' || (g % 10)
                ),
                -- a per-row embedding: fill all 64 dims with a value that varies by row,
                -- so different accounts have different (comparable) vectors. Building the
                -- array with the per-row value avoids adding a scalar to a vector (unsupported).
                (array_fill((0.5 + (g % 10)::real / 100.0), ARRAY[64]))::vector(64),
                ST_MakePoint(-73.0 + (g % 10)::numeric / 100, 45.0 + (g % 10)::numeric / 100)
            FROM generate_series(1, 1000) g
        """)

        print(f"Created {schema}.{DEMO_TABLE} with 1000 accounts (relational + JSON + vector + geo)")


def run_unified_query(conn):
    """Run a single query spanning all four data types."""
    schema = _env("LB_SCHEMA", "bank")

    query = f"""
        SELECT
            account_id,
            branch_id,
            line,
            (spec->>'type') as account_type,
            (spec->>'year')::int as vintage,
            -- vector similarity: find accounts with similar embeddings
            (embedding <-> (SELECT embedding FROM {schema}.{DEMO_TABLE} WHERE account_id='ACCT-1'))::numeric(6,4) as embedding_distance,
            -- geospatial: distance to a reference point
            ST_Distance(location, ST_MakePoint(-73.0, 45.0)::geometry) * 111.0 as km_from_ref
        FROM {schema}.{DEMO_TABLE}
        WHERE
            branch_id = 'BR-NYC'
            AND (spec->>'type') = 'commercial'
            AND ST_DWithin(location, ST_MakePoint(-73.0, 45.0)::geometry, 0.1)
        ORDER BY embedding_distance, km_from_ref
        LIMIT 5
    """

    print("\nOne SELECT spanning relational + JSON + vector + geo:")
    print(f"\nQuery:\n{query}\n")

    with conn.cursor() as cur:
        cur.execute(query)
        rows = cur.fetchall()
        cols = [desc[0] for desc in cur.description]

        print("Results (single query, single plan):")
        for row in rows:
            print(f"  {row[0]:12} | {row[1]:8} | {row[2]:12} | {row[3]:12} | {row[4]:4} | dist={row[5]:.4f} | km={row[6]:.4f}")

        print(f"\n✓ All four data models (relational, JSON, vector, geo) in one query")
        print(f"✓ One execution plan, one snapshot, one transaction")


def show_explain(conn):
    """Show EXPLAIN for the unified query."""
    schema = _env("LB_SCHEMA", "bank")

    query = f"""
        EXPLAIN
        SELECT
            account_id,
            (spec->>'type') as account_type,
            ST_Distance(location, ST_MakePoint(-73.0, 45.0)::geometry) as km_from_ref
        FROM {schema}.{DEMO_TABLE}
        WHERE branch_id = 'BR-NYC'
    """

    with conn.cursor() as cur:
        cur.execute(query)
        plan = [row[0] for row in cur.fetchall()]
        print("\nEXPLAIN shows single plan across all types:")
        for line in plan[:20]:
            print(f"  {line}")


def main():
    ap = argparse.ArgumentParser(description="One table, every data type, unified query")
    ap.add_argument(
        "--step",
        choices=["sql"],
        help="show SQL without running it",
    )
    args = ap.parse_args()

    with connect() as conn:
        print("1. Creating unified table (relational + JSON + vector + geo):")
        setup(conn)

        if args.step == "sql":
            schema = _env("LB_SCHEMA", "bank")
            query = f"""
                SELECT
                    account_id,
                    branch_id,
                    line,
                    (spec->>'type') as account_type,
                    (spec->>'year')::int as vintage,
                    (embedding <-> (SELECT embedding FROM {schema}.{DEMO_TABLE} WHERE account_id='ACCT-1'))::numeric(6,4) as embedding_distance,
                    ST_Distance(location, ST_MakePoint(-73.0, 45.0)::geometry) * 111.0 as km_from_ref
                FROM {schema}.{DEMO_TABLE}
                WHERE
                    branch_id = 'BR-NYC'
                    AND (spec->>'type') = 'commercial'
                    AND ST_DWithin(location, ST_MakePoint(-73.0, 45.0)::geometry, 0.1)
                ORDER BY embedding_distance, km_from_ref
                LIMIT 5
            """
            print("\n2. The unified query (no execution):")
            print(query)
        else:
            print("\n2. Running the unified query:")
            run_unified_query(conn)
            print("\n3. EXPLAIN shows single plan across all types:")
            show_explain(conn)
            print("\n✓ Not four products. One database.")


if __name__ == "__main__":
    main()
