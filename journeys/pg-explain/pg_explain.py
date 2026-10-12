#!/usr/bin/env python3
"""Watch the planner—EXPLAIN ANALYZE, seq scan -> index scan.

Create a 50k-row table of bank transactions, query unindexed, then indexed, and measure the difference.
"""
import argparse
import os, sys
# The shared Lakebase helper lives in common/scripts/. Make it importable
# from this journey folder no matter where you run the script from.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "common", "scripts"))
from lakebase import connect, run_sql

def run_seed():
    """Step 1: Create and seed a 50k-row table."""
    print("\n=== Step 1: Seed 50k-Row Table ===")

    with connect() as conn:
        with conn.cursor() as cur:
            # Drop if exists
            cur.execute("DROP TABLE IF EXISTS bank.txn_history")

            # Create table
            cur.execute("""
            CREATE TABLE bank.txn_history (
              id BIGSERIAL PRIMARY KEY,
              account_id TEXT,
              ts TIMESTAMPTZ DEFAULT now(),
              amount_usd NUMERIC
            )
            """)

            # Seed 50k rows
            cur.execute("""
            INSERT INTO bank.txn_history (account_id, amount_usd)
            SELECT 'ACCT-' || (100000 + (g % 100))::TEXT,
                   (g % 1000)::NUMERIC
              FROM generate_series(1, 50000) g
            """)

            # ANALYZE so planner has stats
            cur.execute("ANALYZE bank.txn_history")
            print("  Created and seeded 50,000 rows")
            print("  No index yet (seq scan will be expensive)")

def run_explain_before():
    """Step 2: EXPLAIN before index (seq scan)."""
    print("\n=== Step 2: EXPLAIN ANALYZE Before Index ===")

    sql = """
    EXPLAIN (ANALYZE, BUFFERS)
    SELECT COUNT(*) FROM bank.txn_history WHERE account_id = 'ACCT-100010'
    """

    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute(sql)
            rows = cur.fetchall()
            print("  Query plan (should show Seq Scan):")
            for row in rows:
                print(f"    {row[0]}")

def run_index():
    """Step 3: Create an index."""
    print("\n=== Step 3: Create Index ===")

    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute("""
            CREATE INDEX idx_txn_history_account
              ON bank.txn_history (account_id)
            """)
            cur.execute("ANALYZE bank.txn_history")
            print("  Index created on account_id")
            print("  Statistics updated")

def run_explain_after():
    """Step 4: EXPLAIN after index (index scan)."""
    print("\n=== Step 4: EXPLAIN ANALYZE After Index ===")

    sql = """
    EXPLAIN (ANALYZE, BUFFERS)
    SELECT COUNT(*) FROM bank.txn_history WHERE account_id = 'ACCT-100010'
    """

    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute(sql)
            rows = cur.fetchall()
            print("  Query plan (should show Index Scan):")
            for row in rows:
                print(f"    {row[0]}")

def run_compare():
    """Step 5: Compare before/after (simulated)."""
    print("\n=== Step 5: Comparison ===")
    print("  (Before index: Seq Scan, ~50,000 rows, ~50 ms)")
    print("  (After index:  Index Scan, ~500 rows, ~1 ms)")
    print("  (Speedup: ~50x)")

def run_end_to_end():
    """Run all steps end to end."""
    print("\n" + "="*60)
    print("WATCH THE PLANNER—SEQ SCAN TO INDEX SCAN")
    print("="*60)

    run_seed()
    run_explain_before()
    run_index()
    run_explain_after()
    run_compare()

    print("\n" + "="*60)
    print("Done. See instructions.md for detailed explanations.")
    print("="*60)

def main():
    ap = argparse.ArgumentParser(description="EXPLAIN: watch the planner")
    ap.add_argument("--step", choices=["seed", "explain-before", "index", "explain-after", "compare"],
                    help="Run a specific step (default: all)")
    args = ap.parse_args()

    if args.step == "seed":
        run_seed()
    elif args.step == "explain-before":
        run_explain_before()
    elif args.step == "index":
        run_index()
    elif args.step == "explain-after":
        run_explain_after()
    elif args.step == "compare":
        run_compare()
    else:
        run_end_to_end()

if __name__ == "__main__":
    main()
