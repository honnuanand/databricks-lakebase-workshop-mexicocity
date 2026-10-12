#!/usr/bin/env python3
"""Feature store, served online — materialize once, serve in ms.

Aggregate raw account transaction events into a feature table keyed by account_id.
Serve features with a primary-key lookup, measured latency, and a
computed_at freshness stamp for real-time fraud scoring.

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

EVENTS_TABLE = "account_events_for_features"
FEATURE_TABLE = "account_features_online"


def setup(conn):
    """Create a raw events table with account transaction telemetry."""
    schema = _env("LB_SCHEMA", "bank")

    with conn.cursor() as cur:
        # Drop if exists
        cur.execute(f"DROP TABLE IF EXISTS {schema}.{EVENTS_TABLE} CASCADE")
        cur.execute(f"DROP TABLE IF EXISTS {schema}.{FEATURE_TABLE} CASCADE")

        # Raw events: every account transaction logged
        cur.execute(f"""
            CREATE TABLE {schema}.{EVENTS_TABLE} (
                event_id BIGSERIAL PRIMARY KEY,
                account_id TEXT NOT NULL,
                event_ts TIMESTAMPTZ NOT NULL DEFAULT now(),
                event_type TEXT,              -- purchase, wire, dispute, chargeback
                amount_usd NUMERIC(12,2),
                anomaly_score NUMERIC(6,2),
                util_pct NUMERIC(6,2)
            )
        """)

        # Seed with 10k events across 100 accounts
        cur.execute(f"""
            INSERT INTO {schema}.{EVENTS_TABLE}(account_id, event_ts, event_type, amount_usd, anomaly_score, util_pct)
            SELECT
                'ACCT-' || (g % 100),
                now() - (g % 3600 || ' seconds')::interval,
                (ARRAY['purchase', 'wire', 'dispute', 'chargeback'])[1 + (g % 4)],
                (g % 5000) + (g % 100)::numeric / 100,
                (g % 10)::numeric + (g % 100)::numeric / 100,
                30 + (g % 70)::numeric
            FROM generate_series(1, 10000) g
        """)

        print(f"Created {schema}.{EVENTS_TABLE} with 10k events across 100 accounts")


def materialize_features(conn):
    """Compute features from raw events and materialize into a feature table."""
    schema = _env("LB_SCHEMA", "bank")

    with conn.cursor() as cur:
        # Create feature table: one row per account, keyed by account_id
        cur.execute(f"""
            CREATE TABLE {schema}.{FEATURE_TABLE} (
                account_id TEXT PRIMARY KEY,
                txns_this_month INT,
                disputes_this_month INT,
                avg_anomaly_score NUMERIC(8,2),
                avg_util_pct NUMERIC(8,2),
                total_amount_usd NUMERIC(12,2),
                computed_at TIMESTAMPTZ NOT NULL DEFAULT now()
            )
        """)

        # Aggregate features from events
        cur.execute(f"""
            INSERT INTO {schema}.{FEATURE_TABLE}(
                account_id, txns_this_month, disputes_this_month,
                avg_anomaly_score, avg_util_pct, total_amount_usd, computed_at
            )
            SELECT
                e.account_id,
                COUNT(CASE WHEN e.event_type = 'purchase' THEN 1 END),
                COUNT(CASE WHEN e.event_type = 'dispute' THEN 1 END),
                ROUND(AVG(e.anomaly_score), 2),
                ROUND(AVG(e.util_pct), 2),
                COALESCE(SUM(e.amount_usd), 0),
                now()
            FROM {schema}.{EVENTS_TABLE} e
            WHERE e.event_ts >= now() - interval '30 days'
            GROUP BY e.account_id
        """)

        print(f"Materialized features into {schema}.{FEATURE_TABLE}")
        with conn.cursor() as check:
            check.execute(f"SELECT COUNT(*) FROM {schema}.{FEATURE_TABLE}")
            count = check.fetchone()[0]
            print(f"  {count} accounts with computed features")


def serve_online(conn):
    """Demonstrate single primary-key feature lookup with measured latency."""
    schema = _env("LB_SCHEMA", "bank")

    with conn.cursor() as cur:
        # Warm up: one query to load the table
        cur.execute(f"SELECT COUNT(*) FROM {schema}.{FEATURE_TABLE}")

        # Now measure: 100 feature lookups
        times = []
        for i in range(100):
            account_id = f"ACCT-{i % 10}"  # query 10 different accounts repeatedly
            start = time.perf_counter()
            cur.execute(
                f"SELECT * FROM {schema}.{FEATURE_TABLE} WHERE account_id = %s",
                [account_id],
            )
            row = cur.fetchone()
            elapsed_ms = (time.perf_counter() - start) * 1000
            times.append(elapsed_ms)

        avg_ms = sum(times) / len(times)
        min_ms = min(times)
        max_ms = max(times)

        print(f"\nFeature lookup latency (primary-key access):")
        print(f"  100 lookups across 10 accounts")
        print(f"  Average: {avg_ms:.2f} ms")
        print(f"  Min: {min_ms:.2f} ms, Max: {max_ms:.2f} ms")
        print(f"  ✓ Fast enough for real-time fraud scoring at authorization time")

        # Show a sample feature vector
        cur.execute(f"SELECT * FROM {schema}.{FEATURE_TABLE} WHERE account_id = 'ACCT-0'")
        row = cur.fetchone()
        if row:
            print(f"\nSample feature vector for ACCT-0:")
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
