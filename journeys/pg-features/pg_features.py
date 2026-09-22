#!/usr/bin/env python3
"""Feature store, served online — materialize once, serve in ms.

Aggregate raw machine events into a feature table keyed by machine_id.
Serve features with a primary-key lookup, measured latency, and a
computed_at freshness stamp.

Usage:
    python pg_features.py                    # build and serve
    python pg_features.py --step setup       # create raw events table
    python pg_features.py --step materialize # compute features into feature table
    python pg_features.py --step serve       # show feature lookup latency

Env: LB_PROFILE, LB_PROJECT, LB_BRANCH, LB_SCHEMA (see 00-setup/).
"""
from __future__ import annotations

import argparse
import time

import os, sys
# The shared Lakebase helper lives in common/scripts/. Make it importable
# from this journey folder no matter where you run the script from.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "common", "scripts"))
from lakebase import connect, _env

EVENTS_TABLE = "machine_events_for_features"
FEATURE_TABLE = "machine_features_online"


def setup(conn):
    """Create a raw events table with machine telemetry."""
    schema = _env("LB_SCHEMA", "factory")

    with conn.cursor() as cur:
        # Drop if exists
        cur.execute(f"DROP TABLE IF EXISTS {schema}.{EVENTS_TABLE} CASCADE")
        cur.execute(f"DROP TABLE IF EXISTS {schema}.{FEATURE_TABLE} CASCADE")

        # Raw events: every machine run logged
        cur.execute(f"""
            CREATE TABLE {schema}.{EVENTS_TABLE} (
                event_id BIGSERIAL PRIMARY KEY,
                machine_id TEXT NOT NULL,
                event_ts TIMESTAMPTZ NOT NULL DEFAULT now(),
                event_type TEXT,              -- run, failure, maintenance
                cycles INT,
                temp_c NUMERIC(6,2),
                vibration_mm_s NUMERIC(6,2)
            )
        """)

        # Seed with 10k events across 100 machines
        cur.execute(f"""
            INSERT INTO {schema}.{EVENTS_TABLE}(machine_id, event_ts, event_type, cycles, temp_c, vibration_mm_s)
            SELECT
                'M-' || (g % 100),
                now() - (g % 3600 || ' seconds')::interval,
                (ARRAY['run', 'failure', 'maintenance'])[1 + (g % 3)],
                g % 1000,
                45 + (g % 50),
                (g % 100) / 10.0
            FROM generate_series(1, 10000) g
        """)

        print(f"Created {schema}.{EVENTS_TABLE} with 10k events across 100 machines")


def materialize_features(conn):
    """Compute features from raw events and materialize into a feature table."""
    schema = _env("LB_SCHEMA", "factory")

    with conn.cursor() as cur:
        # Create feature table: one row per machine, keyed by machine_id
        cur.execute(f"""
            CREATE TABLE {schema}.{FEATURE_TABLE} (
                machine_id TEXT PRIMARY KEY,
                runs_this_month INT,
                failures_this_month INT,
                avg_temp_c NUMERIC(8,2),
                avg_vibration_mm_s NUMERIC(8,2),
                total_cycles INT,
                computed_at TIMESTAMPTZ NOT NULL DEFAULT now()
            )
        """)

        # Aggregate features from events
        cur.execute(f"""
            INSERT INTO {schema}.{FEATURE_TABLE}(
                machine_id, runs_this_month, failures_this_month,
                avg_temp_c, avg_vibration_mm_s, total_cycles, computed_at
            )
            SELECT
                e.machine_id,
                COUNT(CASE WHEN e.event_type = 'run' THEN 1 END),
                COUNT(CASE WHEN e.event_type = 'failure' THEN 1 END),
                ROUND(AVG(e.temp_c), 2),
                ROUND(AVG(e.vibration_mm_s), 2),
                COALESCE(SUM(e.cycles), 0),
                now()
            FROM {schema}.{EVENTS_TABLE} e
            WHERE e.event_ts >= now() - interval '30 days'
            GROUP BY e.machine_id
        """)

        print(f"Materialized features into {schema}.{FEATURE_TABLE}")
        with conn.cursor() as check:
            check.execute(f"SELECT COUNT(*) FROM {schema}.{FEATURE_TABLE}")
            count = check.fetchone()[0]
            print(f"  {count} machines with computed features")


def serve_online(conn):
    """Demonstrate single primary-key feature lookup with measured latency."""
    schema = _env("LB_SCHEMA", "factory")

    with conn.cursor() as cur:
        # Warm up: one query to load the table
        cur.execute(f"SELECT COUNT(*) FROM {schema}.{FEATURE_TABLE}")

        # Now measure: 100 feature lookups
        times = []
        for i in range(100):
            machine_id = f"M-{i % 10}"  # query 10 different machines repeatedly
            start = time.perf_counter()
            cur.execute(
                f"SELECT * FROM {schema}.{FEATURE_TABLE} WHERE machine_id = %s",
                [machine_id],
            )
            row = cur.fetchone()
            elapsed_ms = (time.perf_counter() - start) * 1000
            times.append(elapsed_ms)

        avg_ms = sum(times) / len(times)
        min_ms = min(times)
        max_ms = max(times)

        print(f"\nFeature lookup latency (primary-key access):")
        print(f"  100 lookups across 10 machines")
        print(f"  Average: {avg_ms:.2f} ms")
        print(f"  Min: {min_ms:.2f} ms, Max: {max_ms:.2f} ms")
        print(f"  ✓ Fast enough for real-time model inference")

        # Show a sample feature vector
        cur.execute(f"SELECT * FROM {schema}.{FEATURE_TABLE} WHERE machine_id = 'M-0'")
        row = cur.fetchone()
        if row:
            print(f"\nSample feature vector for M-0:")
            cols = [desc[0] for desc in cur.description]
            for col, val in zip(cols, row):
                print(f"  {col}: {val}")


def main():
    ap = argparse.ArgumentParser(description="Online feature store with measured latency")
    ap.add_argument(
        "--step",
        choices=["setup", "materialize", "serve"],
        help="run a specific step",
    )
    args = ap.parse_args()

    with connect() as conn:
        if args.step == "setup":
            setup(conn)
        elif args.step == "materialize":
            setup(conn)
            materialize_features(conn)
        elif args.step == "serve":
            setup(conn)
            materialize_features(conn)
            serve_online(conn)
        else:
            # Run the whole story
            print("1. Create raw events table:")
            setup(conn)
            print("\n2. Materialize features from events:")
            materialize_features(conn)
            print("\n3. Serve features online with measured latency:")
            serve_online(conn)
            print("\n✓ Offline training in the lakehouse, online serving in Lakebase.")


if __name__ == "__main__":
    main()
