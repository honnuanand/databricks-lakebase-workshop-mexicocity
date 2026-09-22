#!/usr/bin/env python3
"""SQL you already know—Oracle to Postgres migration.

Window functions (ROW_NUMBER, LAG, RANK), recursive CTEs (WITH RECURSIVE),
and an Oracle idiom map (ROWNUM->LIMIT, NVL->COALESCE, SYSDATE->now()).

A bill-of-materials parts-explosion is the star: start with a product and
recursively traverse to every child part, multiplying quantities as we go.
The explosion demonstrates the power of recursive CTEs on tree structures.
"""
import argparse
import os, sys
# The shared Lakebase helper lives in common/scripts/. Make it importable
# from this journey folder no matter where you run the script from.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "common", "scripts"))
from lakebase import connect, run_sql, client, branch_endpoint, _env

def run_window_functions():
    """Window functions: rank machines by health with ROW_NUMBER, RANK, LAG."""
    sql = """
    SELECT machine_id, plant_id, health_pct,
           ROW_NUMBER() OVER (ORDER BY health_pct DESC) as rank,
           RANK() OVER (ORDER BY health_pct DESC) as rank_with_ties,
           LAG(health_pct, 1) OVER (ORDER BY health_pct DESC) as prev_health
      FROM factory.machine
     ORDER BY health_pct DESC
     LIMIT 10;
    """
    print("\n=== Step 2: Window Functions (ROW_NUMBER, RANK, LAG) ===")
    rows = run_sql(sql)
    print(f"Top 10 machines by health:")
    for row in rows:
        print(f"  {row}")

def run_bom_explosion():
    """Recursive CTE: explode a BOM (bill of materials) tree."""
    # Find a product to explode; pick the first one
    product_rows = run_sql("SELECT product_id FROM factory.product LIMIT 1")
    if not product_rows:
        print("No products found; BOM cannot be exploded. Check 00-setup/load-factory.py")
        return

    product_id = product_rows[0][0]
    print(f"\n=== Step 3: Recursive CTE (BOM Explosion for {product_id}) ===")

    sql = f"""
    WITH RECURSIVE bom_tree AS (
      -- Anchor: start with edges from the product
      SELECT parent_id, child_part, qty as multiplier, 1 as depth
        FROM factory.bom_edge
       WHERE parent_id = %s

      UNION ALL

      -- Recursive: traverse child -> grandchild, multiply quantities
      SELECT e.parent_id, e.child_part, t.multiplier * e.qty, t.depth + 1
        FROM factory.bom_edge e
        JOIN bom_tree t ON e.parent_id = t.child_part
       WHERE t.depth < 10
    )
    SELECT child_part, multiplier, depth
      FROM bom_tree
     ORDER BY depth, child_part;
    """

    # Use manual connection to pass parameters
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (product_id,))
            rows = cur.fetchall()

    if rows:
        print(f"BOM explosion for {product_id} (first 15 rows):")
        for row in rows[:15]:
            print(f"  part={row[0]}, qty={row[1]}, depth={row[2]}")
        if len(rows) > 15:
            print(f"  ... and {len(rows) - 15} more rows")
    else:
        print(f"  No BOM edges found for {product_id}")

def run_oracle_idioms():
    """Oracle idiom map: ROWNUM->LIMIT, NVL->COALESCE, SYSDATE->now(), CONNECT BY->WITH RECURSIVE."""
    print("\n=== Step 4: Oracle Idiom Map ===")

    # ROWNUM -> LIMIT
    print("\n  1. ROWNUM -> LIMIT:")
    sql_limit = "SELECT machine_id, health_pct FROM factory.machine LIMIT 3"
    rows = run_sql(sql_limit)
    print(f"     LIMIT 3 returns {len(rows)} rows (same as WHERE ROWNUM <= 3 on Oracle)")

    # NVL -> COALESCE
    print("\n  2. NVL -> COALESCE:")
    sql_coalesce = """
    SELECT machine_id,
           COALESCE(health_pct, 0.0) as health_or_zero
      FROM factory.machine
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

    # CONNECT BY -> WITH RECURSIVE (we already did the full BOM above)
    print("\n  4. CONNECT BY -> WITH RECURSIVE:")
    print("     (See Step 3 above for the full BOM explosion using WITH RECURSIVE)")
    print("     Old Oracle CONNECT BY:")
    print("       SELECT * FROM bom_edge START WITH parent_id = 'PRD-X' CONNECT BY parent_id = PRIOR child_part")
    print("     New Postgres WITH RECURSIVE (Step 3) is more explicit and often faster")

def run_end_to_end():
    """Run all steps end to end."""
    print("\n" + "="*60)
    print("SQL YOU ALREADY KNOW—ORACLE TO POSTGRES")
    print("="*60)

    print("\n=== Step 1: BOM Data Model ===")
    sql = "SELECT parent_id, child_part, qty FROM factory.bom_edge LIMIT 5"
    rows = run_sql(sql)
    print(f"BOM edges (parent -> child with qty):")
    for row in rows:
        print(f"  {row}")

    run_window_functions()
    run_bom_explosion()
    run_oracle_idioms()

    print("\n" + "="*60)
    print("Done. See instructions.md for detailed explanations.")
    print("="*60)

def main():
    ap = argparse.ArgumentParser(description="SQL parity: Oracle idioms in Postgres")
    ap.add_argument("--step", choices=["window", "bom", "idioms"],
                    help="Run a specific step (default: all)")
    args = ap.parse_args()

    if args.step == "window":
        run_window_functions()
    elif args.step == "bom":
        run_bom_explosion()
    elif args.step == "idioms":
        run_oracle_idioms()
    else:
        run_end_to_end()

if __name__ == "__main__":
    main()
