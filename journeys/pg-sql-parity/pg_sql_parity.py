#!/usr/bin/env python3
"""SQL you already know, Oracle to Postgres migration.

Window functions (ROW_NUMBER, LAG, RANK), recursive CTEs (WITH RECURSIVE),
and an Oracle idiom map (ROWNUM->LIMIT, NVL->COALESCE, SYSDATE->now()).

A fund holdings explosion is the star: start with a fund and recursively
traverse to every underlying instrument, multiplying units as we go. The
explosion demonstrates the power of recursive CTEs on tree structures.
"""
import argparse
import os, sys
# The shared Lakebase helper lives in common/scripts/. Make it importable
# from this journey folder no matter where you run the script from.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "common", "scripts"))
from lakebase import connect, run_sql, client, branch_endpoint, _env

def run_window_functions():
    """Window functions: rank accounts by health with ROW_NUMBER, RANK, LAG."""
    sql = """
    SELECT account_id, branch_id, health_pct,
           ROW_NUMBER() OVER (ORDER BY health_pct DESC) as rank,
           RANK() OVER (ORDER BY health_pct DESC) as rank_with_ties,
           LAG(health_pct, 1) OVER (ORDER BY health_pct DESC) as prev_health
      FROM bank.account
     ORDER BY health_pct DESC
     LIMIT 10;
    """
    print("\n=== Step 2: Window Functions (ROW_NUMBER, RANK, LAG) ===")
    rows = run_sql(sql)
    print(f"Top 10 accounts by health:")
    for row in rows:
        print(f"  {row}")

def run_holdings_explosion():
    """Recursive CTE: explode a fund holdings tree."""
    # Find a fund to explode; pick the first one
    fund_rows = run_sql("SELECT fund_id FROM bank.fund LIMIT 1")
    if not fund_rows:
        print("No funds found; holdings cannot be exploded. Check 00-setup/load_bank.py")
        return

    fund_id = fund_rows[0][0]
    print(f"\n=== Step 3: Recursive CTE (Holdings Explosion for {fund_id}) ===")

    sql = f"""
    WITH RECURSIVE holdings_tree AS (
      -- Anchor: start with holdings of the fund
      SELECT parent_id, instrument_id, qty as multiplier, 1 as depth
        FROM bank.holding
       WHERE parent_id = %s

      UNION ALL

      -- Recursive: traverse holding -> sub-holding, multiply units
      SELECT h.parent_id, h.instrument_id, t.multiplier * h.qty, t.depth + 1
        FROM bank.holding h
        JOIN holdings_tree t ON h.parent_id = t.instrument_id
       WHERE t.depth < 10
    )
    SELECT instrument_id, multiplier, depth
      FROM holdings_tree
     ORDER BY depth, instrument_id;
    """

    # Use manual connection to pass parameters
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (fund_id,))
            rows = cur.fetchall()

    if rows:
        print(f"Holdings explosion for {fund_id} (first 15 rows):")
        for row in rows[:15]:
            print(f"  instrument={row[0]}, units={row[1]}, depth={row[2]}")
        if len(rows) > 15:
            print(f"  ... and {len(rows) - 15} more rows")
    else:
        print(f"  No holdings found for {fund_id}")

def run_oracle_idioms():
    """Oracle idiom map: ROWNUM->LIMIT, NVL->COALESCE, SYSDATE->now(), CONNECT BY->WITH RECURSIVE."""
    print("\n=== Step 4: Oracle Idiom Map ===")

    # ROWNUM -> LIMIT
    print("\n  1. ROWNUM -> LIMIT:")
    sql_limit = "SELECT account_id, health_pct FROM bank.account LIMIT 3"
    rows = run_sql(sql_limit)
    print(f"     LIMIT 3 returns {len(rows)} rows (same as WHERE ROWNUM <= 3 on Oracle)")

    # NVL -> COALESCE
    print("\n  2. NVL -> COALESCE:")
    sql_coalesce = """
    SELECT account_id,
           COALESCE(health_pct, 0.0) as health_or_zero
      FROM bank.account
     LIMIT 3
    """
    rows = run_sql(sql_coalesce)
    print(f"     COALESCE(health_pct, 0.0) works the same as NVL():")
    for row in rows:
        print(f"       {row}")

    # SYSDATE -> now()
    print("\n  3. SYSDATE -> now():")
    sql_now = "SELECT now() as current_time, CURRENT_TIMESTAMP as alt_form"
    rows = run_sql(sql_now)
    if rows:
        print(f"     now() returns: {rows[0][0]}")
        print(f"     CURRENT_TIMESTAMP also works: {rows[0][1]}")

    # CONNECT BY -> WITH RECURSIVE (we already did the full holdings tree above)
    print("\n  4. CONNECT BY -> WITH RECURSIVE:")
    print("     (See Step 3 above for the full holdings explosion using WITH RECURSIVE)")
    print("     Old Oracle CONNECT BY:")
    print("       SELECT * FROM holding START WITH parent_id = 'FUND-X' CONNECT BY parent_id = PRIOR instrument_id")
    print("     New Postgres WITH RECURSIVE (Step 3) is more explicit and often faster")

def run_end_to_end():
    """Run all steps end to end."""
    print("\n" + "="*60)
    print("SQL YOU ALREADY KNOW, ORACLE TO POSTGRES")
    print("="*60)

    print("\n=== Step 1: Holdings Data Model ===")
    sql = "SELECT parent_id, instrument_id, qty FROM bank.holding LIMIT 5"
    rows = run_sql(sql)
    print(f"Holdings edges (parent -> instrument with units):")
    for row in rows:
        print(f"  {row}")

    run_window_functions()
    run_holdings_explosion()
    run_oracle_idioms()

    print("\n" + "="*60)
    print("Done. See instructions.md for detailed explanations.")
    print("="*60)

def main():
    ap = argparse.ArgumentParser(description="SQL parity: Oracle idioms in Postgres")
    ap.add_argument("--step", choices=["window", "holdings", "idioms"],
                    help="Run a specific step (default: all)")
    args = ap.parse_args()

    if args.step == "window":
        run_window_functions()
    elif args.step == "holdings":
        run_holdings_explosion()
    elif args.step == "idioms":
        run_oracle_idioms()
    else:
        run_end_to_end()

if __name__ == "__main__":
    main()
