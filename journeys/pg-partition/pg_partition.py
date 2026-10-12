#!/usr/bin/env python3
"""Scale-out: partitioning + partition pruning.

One large time-series table split into monthly RANGE partitions.
EXPLAIN proves the planner PRUNES partitions: a one-month query scans
one partition; a cross-cutting query scans all. Demonstrates the scaling
principle: OLTP in Postgres (partitioned), analytics in the lakehouse (Delta/UC).

Usage:
    python pg_partition.py                # build partitioned table + explain
    python pg_partition.py --step setup   # create partitioned table with data
    python pg_partition.py --step explain # run EXPLAIN on range queries

Env: LB_PROFILE, LB_PROJECT, LB_BRANCH, LB_SCHEMA (see 00-setup/).
"""
from __future__ import annotations

import argparse
from datetime import datetime, timedelta

import psycopg
import os, sys
# The shared Lakebase helper lives in common/scripts/. Make it importable
# from this journey folder no matter where you run the script from.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "common", "scripts"))
from lakebase import connect, _env

DEMO_TABLE = "txn_partitioned"


def setup(conn):
    """Create a partitioned table with 6 months of transactions."""
    schema = _env("LB_SCHEMA", "bank")

    with conn.cursor() as cur:
        # Drop if exists
        cur.execute(f"DROP TABLE IF EXISTS {schema}.{DEMO_TABLE} CASCADE")

        # Create partitioned table (RANGE on month)
        cur.execute(f"""
            CREATE TABLE {schema}.{DEMO_TABLE} (
                txn_id BIGSERIAL,
                account_id TEXT NOT NULL,
                ts TIMESTAMPTZ NOT NULL,
                amount_usd NUMERIC(12,2),
                anomaly_score NUMERIC(6,2),
                PRIMARY KEY (txn_id, ts)
            ) PARTITION BY RANGE (ts)
        """)

        # Create 6 monthly partitions
        # Each partition holds one calendar month
        start_date = datetime(2024, 1, 1)
        for month_offset in range(6):
            month_start = start_date + timedelta(days=32 * month_offset)
            month_start = month_start.replace(day=1)  # align to 1st
            month_end = month_start + timedelta(days=32)
            month_end = month_end.replace(day=1)  # move to 1st of next month

            partition_name = f"{DEMO_TABLE}_{month_start.strftime('%Y%m')}"
            cur.execute(f"""
                CREATE TABLE {schema}.{partition_name} PARTITION OF {schema}.{DEMO_TABLE}
                FOR VALUES FROM ('{month_start.isoformat()}') TO ('{month_end.isoformat()}')
            """)

        print(f"Created partitioned table {schema}.{DEMO_TABLE} with 6 monthly partitions")

        # Insert data: 30k rows per month (transactions across 1000 accounts)
        # Total: 180k rows across 6 months
        cur.execute(f"""
            INSERT INTO {schema}.{DEMO_TABLE}(account_id, ts, amount_usd, anomaly_score)
            SELECT
                'ACCT-' || (g % 1000),
                '2024-01-01'::timestamptz + (g / 1000 || ' days')::interval + (g % 1440 || ' minutes')::interval,
                45 + (g % 50),
                (g % 100) / 10.0
            FROM generate_series(1, 180000) g
        """)

        cur.execute(f"ANALYZE {schema}.{DEMO_TABLE}")
        print("Inserted 180k transactions (6 months × 30k rows each)")


def explain_one_month(conn):
    """Show EXPLAIN for a one-month query, should prune 5 partitions."""
    schema = _env("LB_SCHEMA", "bank")

    query = f"""
        SELECT COUNT(*) FROM {schema}.{DEMO_TABLE}
        WHERE ts >= '2024-03-01' AND ts < '2024-04-01'
    """

    with conn.cursor() as cur:
        cur.execute(f"EXPLAIN (ANALYZE) {query}")
        plan = "\n".join([row[0] for row in cur.fetchall()])
        print("\nOne-month query (March 2024):")
        print("EXPLAIN output:")
        for line in plan.split("\n")[:15]:  # first 15 lines
            print(f"  {line}")

        # Count scanned partitions
        if "Subplans Removed" in plan:
            print("  ✓ PARTITION PRUNING: 5 of 6 partitions removed (only March scanned)")
        else:
            print("  (Showing pruning via output above)")


def explain_all_months(conn):
    """Show EXPLAIN for a full-range query, must scan all 6 partitions."""
    schema = _env("LB_SCHEMA", "bank")

    query = f"""
        SELECT COUNT(*) FROM {schema}.{DEMO_TABLE}
        WHERE ts >= '2024-01-01' AND ts < '2024-07-01'
    """

    with conn.cursor() as cur:
        cur.execute(f"EXPLAIN (ANALYZE) {query}")
        plan = "\n".join([row[0] for row in cur.fetchall()])
        print("\nFull-range query (all 6 months):")
        print("EXPLAIN output:")
        for line in plan.split("\n")[:20]:  # first 20 lines
            print(f"  {line}")
        print("  (All 6 partitions scanned; no pruning possible)")


def main():
    ap = argparse.ArgumentParser(description="Partitioning + partition pruning")
    ap.add_argument(
        "--step",
        choices=["setup", "explain"],
        help="run a specific step",
    )
    args = ap.parse_args()

    with connect() as conn:
        if args.step == "setup":
            setup(conn)
        elif args.step == "explain":
            setup(conn)
            explain_one_month(conn)
            explain_all_months(conn)
        else:
            # Run the whole story
            print("1. Creating partitioned table with 6 months of transaction data:")
            setup(conn)
            print("\n2. Running EXPLAIN on one-month query (PARTITION PRUNING):")
            explain_one_month(conn)
            print("\n3. Running EXPLAIN on full-range query (all partitions scanned):")
            explain_all_months(conn)
            print("\n✓ OLTP scale in Postgres, OLAP scale-out to the lakehouse.")


if __name__ == "__main__":
    main()
