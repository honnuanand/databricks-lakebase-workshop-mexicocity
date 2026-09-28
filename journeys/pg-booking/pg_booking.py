#!/usr/bin/env python3
"""No double-booking, GiST exclusion constraints on time ranges.

Prevent overlapping operations on the same machine using EXCLUDE USING gist.
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
            cur.execute("ALTER TABLE factory.operation DROP CONSTRAINT IF EXISTS no_machine_overlap")
            sql = """
            ALTER TABLE factory.operation
              ADD CONSTRAINT no_machine_overlap
              EXCLUDE USING gist (machine_id WITH =,
                                  tstzrange(starts_at, ends_at) WITH &&);
            """
            try:
                cur.execute(sql)
                print("  Exclusion constraint created: no_machine_overlap")
            except Exception as e:
                print(f"  Could not create constraint: {e}")

def run_overlap():
    """Step 3: Try to insert an overlapping operation."""
    print("\n=== Step 3: Attempt Overlapping Insert ===")

    # Get an existing operation (and its work order, to satisfy the FK) to overlap.
    ops = run_sql("""
    SELECT op_id, wo_id, machine_id, starts_at, ends_at
      FROM factory.operation
     WHERE machine_id IS NOT NULL AND starts_at IS NOT NULL AND ends_at IS NOT NULL
     LIMIT 1
    """)

    if not ops:
        print("  No existing operations found")
        return

    op_id, wo_id, machine_id, starts_at, ends_at = ops[0]

    # Clean any prior test row so this is re-runnable, then try to insert an overlap.
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM factory.operation WHERE op_id = 'OP-OVERLAP'")
            try:
                overlap_start = starts_at  # same start as an existing op on this machine
                overlap_end = ends_at + __import__('datetime').timedelta(hours=1)
                cur.execute("""
                INSERT INTO factory.operation
                  (op_id, wo_id, machine_id, seq, status, starts_at, ends_at)
                VALUES
                  ('OP-OVERLAP', %s, %s, 99, 'pending', %s, %s)
                """, (wo_id, machine_id, overlap_start, overlap_end))
                print(f"  ERROR: Overlap should have been rejected!")
            except Exception as e:
                error_msg = str(e)
                if "no_machine_overlap" in error_msg or "conflicting key" in error_msg or "exclusion" in error_msg.lower():
                    print(f"  Good: the database rejected the overlapping operation.")
                    print(f"    {error_msg.splitlines()[0][:120]}")
                else:
                    print(f"  Unexpected error: {error_msg[:120]}")

def run_explain():
    """Step 4: EXPLAIN shows constraint check."""
    print("\n=== Step 4: EXPLAIN Shows Constraint Check ===")

    sql = ("EXPLAIN INSERT INTO factory.operation "
           "(op_id, wo_id, machine_id, seq, status, starts_at, ends_at) "
           "SELECT 'op-explain', wo_id, 'M-204', 98, 'pending', now(), now() + interval '1 hour' "
           "FROM factory.operation LIMIT 1")

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
    print("NO DOUBLE-BOOKING, GIST EXCLUSION CONSTRAINTS")
    print("="*60)

    print("\n=== Step 1: Inspect Operation Table ===")
    sql = """
    SELECT op_id, machine_id, starts_at, ends_at
      FROM factory.operation
     LIMIT 3
    """
    rows = run_sql(sql)
    print(f"Sample operations:")
    for row in rows:
        print(f"  {row}")

    run_constraint()
    run_overlap()
    run_explain()

    print("\n" + "="*60)
    print("Done. See instructions.md for detailed explanations.")
    print("="*60)

def main():
    ap = argparse.ArgumentParser(description="GiST exclusion: no double-booking")
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
