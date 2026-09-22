#!/usr/bin/env python3
"""Tune the planner — extended statistics fix a bad row estimate.

When a query filters on two CORRELATED columns (e.g., machine_line and plant),
the planner assumes they're independent and badly under-estimates rows.
CREATE STATISTICS teaches it the correlation, and the estimate snaps to reality.

All numbers are server-side (EXPLAIN ANALYZE) — measured by Postgres itself.

Usage:
    python pg_perf.py                 # run the whole story with estimates
    python pg_perf.py --step setup    # create the demo table
    python pg_perf.py --step before   # show the bad estimate (no stats)
    python pg_perf.py --step stats    # create CREATE STATISTICS
    python pg_perf.py --step after    # show the fixed estimate

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

DEMO_TABLE = "machine_perf_demo"
DEMO_STAT = "machine_perf_stat"


def _explain(cur, query: str) -> tuple[int, int]:
    """Run EXPLAIN ANALYZE and return (estimated_rows, actual_rows)."""
    cur.execute(f"EXPLAIN (ANALYZE, FORMAT JSON) {query}")
    raw = cur.fetchone()[0][0]
    p = raw["Plan"]
    while p.get("Plans"):
        p = p["Plans"][0]
    est = p.get("Plan Rows", 0)
    act = p.get("Actual Rows", 0)
    return est, act


def setup(conn):
    """Create a demo table with correlated columns: machine_line => plant."""
    schema = _env("LB_SCHEMA", "factory")
    with conn.cursor() as cur:
        # Drop if exists
        cur.execute(f"DROP TABLE IF EXISTS {schema}.{DEMO_TABLE} CASCADE")
        cur.execute(f"DROP STATISTICS IF EXISTS {schema}.{DEMO_STAT}")

        # Create table: machine_line is fully determined by plant (100% correlated)
        cur.execute(f"""
            CREATE TABLE {schema}.{DEMO_TABLE} (
                id BIGSERIAL PRIMARY KEY,
                machine_id TEXT,
                plant_id TEXT,
                machine_line TEXT,
                temp_c NUMERIC,
                health_pct NUMERIC
            )
        """)

        # Insert: each plant has specific lines (correlated)
        # Plant PL-DETROIT -> Stamping-A,B,C; Plant PL-SHANGHAI -> Assembly-1,2
        cur.execute(f"""
            INSERT INTO {schema}.{DEMO_TABLE}(machine_id, plant_id, machine_line, temp_c, health_pct)
            SELECT
                'M-' || g,
                (ARRAY['PL-DETROIT', 'PL-DETROIT', 'PL-SHANGHAI', 'PL-SHANGHAI'])[1 + (g % 4)],
                CASE (g % 4)
                    WHEN 0 THEN 'Stamping-A'
                    WHEN 1 THEN 'Stamping-B'
                    WHEN 2 THEN 'Assembly-1'
                    ELSE 'Assembly-2'
                END,
                50.0 + (g % 30),
                80.0 + (g % 20)
            FROM generate_series(1, 100000) g
        """)

        # Gather statistics so the planner has baseline data
        cur.execute(f"ANALYZE {schema}.{DEMO_TABLE}")
        print(f"Created demo table {schema}.{DEMO_TABLE} with 100k rows (machine_line correlated with plant)")


def before(conn):
    """Show the bad estimate before CREATE STATISTICS."""
    schema = _env("LB_SCHEMA", "factory")
    query = (
        f"SELECT id FROM {schema}.{DEMO_TABLE} "
        f"WHERE plant_id = 'PL-DETROIT' AND machine_line = 'Stamping-A'"
    )
    with conn.cursor() as cur:
        est, act = _explain(cur, query)
        underest_ratio = act / est if est > 0 else 0
        print(f"\nBefore CREATE STATISTICS:")
        print(f"  Estimated rows: ~{est:,}")
        print(f"  Actual rows:    {act:,}")
        print(f"  Planner error:  {underest_ratio:.1f}x (estimate is {100 * (1 - underest_ratio):.0f}% off)")


def create_stats(conn):
    """Create statistics to teach the planner the correlation."""
    schema = _env("LB_SCHEMA", "factory")
    with conn.cursor() as cur:
        # CREATE STATISTICS on the two correlated columns with dependencies
        cur.execute(f"""
            CREATE STATISTICS {schema}.{DEMO_STAT}
            ON plant_id, machine_line
            FROM {schema}.{DEMO_TABLE}
        """)
        print(f"Created statistics: {schema}.{DEMO_STAT} on (plant_id, machine_line)")

        # Reanalyze so the planner picks up the new stats
        cur.execute(f"ANALYZE {schema}.{DEMO_TABLE}")
        print("Reanalyzed table — planner now uses the new statistics")


def after(conn):
    """Show the fixed estimate after CREATE STATISTICS."""
    schema = _env("LB_SCHEMA", "factory")
    query = (
        f"SELECT id FROM {schema}.{DEMO_TABLE} "
        f"WHERE plant_id = 'PL-DETROIT' AND machine_line = 'Stamping-A'"
    )
    with conn.cursor() as cur:
        est, act = _explain(cur, query)
        error_ratio = abs(est - act) / act if act > 0 else 0
        print(f"\nAfter CREATE STATISTICS:")
        print(f"  Estimated rows: ~{est:,}")
        print(f"  Actual rows:    {act:,}")
        print(f"  Planner error:  {100 * error_ratio:.1f}% (estimate is now accurate)")


def main():
    ap = argparse.ArgumentParser(description="Extended statistics tune the planner")
    ap.add_argument(
        "--step",
        choices=["setup", "before", "stats", "after"],
        help="run a specific step",
    )
    args = ap.parse_args()

    with connect() as conn:
        if args.step == "setup":
            setup(conn)
        elif args.step == "before":
            before(conn)
        elif args.step == "stats":
            create_stats(conn)
        elif args.step == "after":
            after(conn)
        else:
            # Run the whole story
            print("1. Set up the demo table (correlated columns):")
            setup(conn)
            print("\n2. Show the bad estimate (no stats):")
            before(conn)
            print("\n3. Create statistics to teach the planner:")
            create_stats(conn)
            print("\n4. Show the fixed estimate:")
            after(conn)
            print("\n✓ The planner's knowledge is now tuned to reality.")


if __name__ == "__main__":
    main()
