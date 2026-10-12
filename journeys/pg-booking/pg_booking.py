#!/usr/bin/env python3
"""No settlement overlap, GiST exclusion constraints on time ranges.

Prevent overlapping settlements on the same account using EXCLUDE USING gist.
"""
import argparse
import os, sys
# The shared Lakebase helper lives in common/scripts/. Make it importable
# from this journey folder no matter where you run the script from.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "common", "scripts"))
from lakebase import connect, run_sql

def run_constraint():
    """Step 2: Create GiST exclusion constraint."""
    print("\n=== Step 2: Create GiST Exclusion Constraint ===")

    with connect() as conn:
        with conn.cursor() as cur:
            try:
                cur.execute("CREATE EXTENSION IF NOT EXISTS btree_gist")
                print("  btree_gist extension created")
            except:
                pass

            # Postgres has no ADD CONSTRAINT IF NOT EXISTS; drop then add so it's idempotent.
            cur.execute("ALTER TABLE bank.settlement DROP CONSTRAINT IF EXISTS no_account_overlap")
            sql = """
            ALTER TABLE bank.settlement
              ADD CONSTRAINT no_account_overlap
              EXCLUDE USING gist (account_id WITH =,
                                  tstzrange(starts_at, ends_at) WITH &&);
            """
            try:
                cur.execute(sql)
                print("  Exclusion constraint created: no_account_overlap")
            except Exception as e:
                print(f"  Could not create constraint: {e}")

def run_overlap():
    """Step 3: Try to insert an overlapping settlement."""
    print("\n=== Step 3: Attempt Overlapping Insert ===")

    # Get an existing settlement (and its trade_id, to satisfy the FK) to overlap.
    stls = run_sql("""
    SELECT settlement_id, trade_id, account_id, starts_at, ends_at
      FROM bank.settlement
     WHERE account_id IS NOT NULL AND starts_at IS NOT NULL AND ends_at IS NOT NULL
     LIMIT 1
    """)

    if not stls:
        print("  No existing settlements found")
        return

    settlement_id, trade_id, account_id, starts_at, ends_at = stls[0]

    # Clean any prior test row so this is re-runnable, then try to insert an overlap.
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM bank.settlement WHERE settlement_id = 'STL-OVERLAP'")
            try:
                overlap_start = starts_at  # same start as an existing settlement on this account
                overlap_end = ends_at + __import__('datetime').timedelta(hours=1)
                cur.execute("""
                INSERT INTO bank.settlement
                  (settlement_id, trade_id, account_id, seq, status, starts_at, ends_at)
                VALUES
                  ('STL-OVERLAP', %s, %s, 99, 'pending', %s, %s)
                """, (trade_id, account_id, overlap_start, overlap_end))
                print(f"  ERROR: Overlap should have been rejected!")
            except Exception as e:
                error_msg = str(e)
                if "no_account_overlap" in error_msg or "conflicting key" in error_msg or "exclusion" in error_msg.lower():
                    print(f"  Good: the database rejected the overlapping settlement.")
                    print(f"    {error_msg.splitlines()[0][:120]}")
                else:
                    print(f"  Unexpected error: {error_msg[:120]}")

def run_explain():
    """Step 4: EXPLAIN shows constraint check."""
    print("\n=== Step 4: EXPLAIN Shows Constraint Check ===")

    sql = ("EXPLAIN INSERT INTO bank.settlement "
           "(settlement_id, trade_id, account_id, seq, status, starts_at, ends_at) "
           "SELECT 'stl-explain', trade_id, 'ACCT-100240', 98, 'pending', now(), now() + interval '1 hour' "
           "FROM bank.settlement LIMIT 1")

    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute(sql)
            rows = cur.fetchall()
            print(f"  Query plan (should mention constraint):")
            for row in rows:
                print(f"    {row[0]}")

def run_end_to_end():
    """Run all steps end to end."""
    print("\n" + "="*60)
    print("NO SETTLEMENT OVERLAP, GIST EXCLUSION CONSTRAINTS")
    print("="*60)

    print("\n=== Step 1: Inspect Settlement Table ===")
    sql = """
    SELECT settlement_id, account_id, starts_at, ends_at
      FROM bank.settlement
     LIMIT 3
    """
    rows = run_sql(sql)
    print(f"Sample settlements:")
    for row in rows:
        print(f"  {row}")

    run_constraint()
    run_overlap()
    run_explain()

    print("\n" + "="*60)
    print("Done. See instructions.md for detailed explanations.")
    print("="*60)

def main():
    ap = argparse.ArgumentParser(description="GiST exclusion: no settlement overlap")
    ap.add_argument("--step", choices=["constraint", "overlap", "explain"],
                    help="Run a specific step (default: all)")
    args = ap.parse_args()

    if args.step == "constraint":
        run_constraint()
    elif args.step == "overlap":
        run_overlap()
    elif args.step == "explain":
        run_explain()
    else:
        run_end_to_end()

if __name__ == "__main__":
    main()
