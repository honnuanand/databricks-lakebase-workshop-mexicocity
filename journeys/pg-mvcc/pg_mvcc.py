#!/usr/bin/env python3
"""MVCC and the WAL—multi-version concurrency control machinery.

Query xmin/xmax/ctid, watch versioning, observe dead tuples, run VACUUM.
"""
import argparse
import os, sys
# The shared Lakebase helper lives in common/scripts/. Make it importable
# from this journey folder no matter where you run the script from.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "common", "scripts"))
from lakebase import connect, run_sql

def run_update():
    """Step 2: UPDATE and watch xmin/xmax/ctid change."""
    print("\n=== Step 2: UPDATE and Watch Versioning ===")

    # Get a sample machine
    machines = run_sql("SELECT machine_id FROM factory.machine LIMIT 1")
    if not machines:
        print("  No machines found")
        return

    machine_id = machines[0][0]

    with connect() as conn:
        with conn.cursor() as cur:
            # Query before
            cur.execute(f"""
            SELECT xmin, xmax, ctid, health_pct
              FROM factory.machine
             WHERE machine_id = %s
            """, (machine_id,))
            before = cur.fetchone()
            print(f"\n  Before UPDATE:")
            if before:
                print(f"    xmin={before[0]}, xmax={before[1]}, ctid={before[2]}, health_pct={before[3]}")

            # UPDATE
            cur.execute(f"""
            UPDATE factory.machine
              SET health_pct = 50.0
             WHERE machine_id = %s
            """, (machine_id,))
            print(f"\n  Running UPDATE...")

            # Query after
            cur.execute(f"""
            SELECT xmin, xmax, ctid, health_pct
              FROM factory.machine
             WHERE machine_id = %s
            """, (machine_id,))
            after = cur.fetchone()
            print(f"\n  After UPDATE:")
            if after:
                print(f"    xmin={after[0]}, xmax={after[1]}, ctid={after[2]}, health_pct={after[3]}")

            if before and after:
                if before[0] != after[0]:
                    print(f"\n  Note: xmin changed ({before[0]} → {after[0]}), new version created")
                if before[2] != after[2]:
                    print(f"  Note: ctid changed ({before[2]} → {after[2]}), new physical location")

def run_deadtuples():
    """Step 3: Run multiple UPDATEs and watch dead tuples accumulate."""
    print("\n=== Step 3: Dead Tuples Accumulate ===")

    machines = run_sql("SELECT machine_id FROM factory.machine LIMIT 1")
    if not machines:
        print("  No machines found")
        return

    machine_id = machines[0][0]

    with connect() as conn:
        with conn.cursor() as cur:
            # Before UPDATEs
            cur.execute("""
            SELECT n_live_tup, n_dead_tup
              FROM pg_stat_user_tables
             WHERE relname = 'machine'
            """)
            before = cur.fetchone()
            print(f"\n  Before UPDATEs:")
            if before:
                print(f"    n_live_tup={before[0]}, n_dead_tup={before[1]}")

            # Run 10 UPDATEs
            for i in range(10):
                cur.execute(f"""
                UPDATE factory.machine
                  SET health_pct = health_pct + 1.0
                 WHERE machine_id = %s
                """, (machine_id,))

            print(f"\n  After 10 UPDATEs:")

            # After UPDATEs
            cur.execute("""
            SELECT n_live_tup, n_dead_tup
              FROM pg_stat_user_tables
             WHERE relname = 'machine'
            """)
            after = cur.fetchone()
            if after:
                print(f"    n_live_tup={after[0]}, n_dead_tup={after[1]}")
                if before and after[1] > before[1]:
                    print(f"    Dead tuples increased by {after[1] - before[1]}")

def run_vacuum():
    """Step 4: Run VACUUM and reclaim space."""
    print("\n=== Step 4: VACUUM Reclaims Space ===")

    with connect() as conn:
        with conn.cursor() as cur:
            # Before VACUUM
            cur.execute("""
            SELECT n_live_tup, n_dead_tup
              FROM pg_stat_user_tables
             WHERE relname = 'machine'
            """)
            before = cur.fetchone()
            print(f"\n  Before VACUUM:")
            if before:
                print(f"    n_live_tup={before[0]}, n_dead_tup={before[1]}")

            # VACUUM
            cur.execute("VACUUM factory.machine")
            print(f"\n  Running VACUUM...")

            # After VACUUM
            cur.execute("""
            SELECT n_live_tup, n_dead_tup
              FROM pg_stat_user_tables
             WHERE relname = 'machine'
            """)
            after = cur.fetchone()
            print(f"\n  After VACUUM:")
            if after:
                print(f"    n_live_tup={after[0]}, n_dead_tup={after[1]}")
                if before and after[1] < before[1]:
                    print(f"    Dead tuples reclaimed: {before[1] - after[1]}")

def run_end_to_end():
    """Run all steps end to end."""
    print("\n" + "="*60)
    print("MVCC AND THE WAL—MULTI-VERSION CONCURRENCY CONTROL")
    print("="*60)

    print("\n=== Step 1: Query System Columns ===")
    machines = run_sql("SELECT machine_id FROM factory.machine LIMIT 1")
    if machines:
        machine_id = machines[0][0]
        sql = f"""
        SELECT xmin, xmax, ctid, machine_id, health_pct
          FROM factory.machine
         WHERE machine_id = %s
        """
        with connect() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (machine_id,))
                row = cur.fetchone()
                if row:
                    print(f"  xmin={row[0]}, xmax={row[1]}, ctid={row[2]}")
                    print(f"  machine_id={row[3]}, health_pct={row[4]}")

    run_update()
    run_deadtuples()
    run_vacuum()

    print("\n" + "="*60)
    print("Done. See instructions.md for detailed explanations.")
    print("="*60)

def main():
    ap = argparse.ArgumentParser(description="MVCC: versioning and the WAL")
    ap.add_argument("--step", choices=["update", "deadtuples", "vacuum"],
                    help="Run a specific step (default: all)")
    args = ap.parse_args()

    if args.step == "update":
        run_update()
    elif args.step == "deadtuples":
        run_deadtuples()
    elif args.step == "vacuum":
        run_vacuum()
    else:
        run_end_to_end()

if __name__ == "__main__":
    main()
