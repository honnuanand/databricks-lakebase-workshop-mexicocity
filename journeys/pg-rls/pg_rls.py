#!/usr/bin/env python3
"""Row-level security—multi-plant tenancy with RLS policies.

Create roles for each operator/plant, define RLS policies, and verify
that the same query returns different rows for different operators.
"""
import argparse
import os, sys
# The shared Lakebase helper lives in common/scripts/. Make it importable
# from this journey folder no matter where you run the script from.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "common", "scripts"))
from lakebase import connect, run_sql

def run_roles():
    """Step 1: Create roles for each plant operator."""
    print("\n=== Step 1: Create Roles ===")
    roles = ["operator_detroit", "operator_chicago", "operator_toronto"]
    with connect() as conn:
        with conn.cursor() as cur:
            for role in roles:
                try:
                    cur.execute(f"CREATE ROLE IF NOT EXISTS {role}")
                    print(f"  Created role: {role}")
                except Exception as e:
                    print(f"  {role} exists or error: {e}")

            # Grant permissions
            cur.execute(f"GRANT USAGE ON SCHEMA factory TO {', '.join(roles)}")
            cur.execute(f"GRANT SELECT ON ALL TABLES IN SCHEMA factory TO {', '.join(roles)}")
            print(f"  Granted permissions to all roles")

def run_policy():
    """Step 2: Create and enable RLS policy."""
    print("\n=== Step 2: Create RLS Policy ===")

    sql_enable = "ALTER TABLE factory.machine ENABLE ROW LEVEL SECURITY;"
    sql_policy = """
    CREATE POLICY IF NOT EXISTS machine_operator_isolation ON factory.machine
      FOR SELECT
      USING (plant_id = current_setting('app.current_operator_plant', true));
    """

    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute(sql_enable)
            cur.execute(sql_policy)
            print("  RLS enabled on factory.machine")
            print("  Policy created: machine_operator_isolation")

def run_query():
    """Step 3: Query with RLS for different operators."""
    print("\n=== Step 3: Query with Different Operators ===")

    # Get a sample plant
    plants = run_sql("SELECT plant_id FROM factory.plant LIMIT 1")
    if not plants:
        print("  No plants found")
        return

    plant_id = plants[0][0]

    sql = "SELECT machine_id, plant_id, status FROM factory.machine"

    with connect() as conn:
        with conn.cursor() as cur:
            # Query as if operator_detroit
            cur.execute(f"SET app.current_operator_plant = '{plant_id}'")
            cur.execute(sql)
            rows = cur.fetchall()
            print(f"\n  Querying as operator for plant {plant_id}:")
            for row in rows[:5]:
                print(f"    {row}")
            if len(rows) > 5:
                print(f"    ... ({len(rows)} total rows)")

def run_explain():
    """Step 4: EXPLAIN shows RLS policy filter."""
    print("\n=== Step 4: EXPLAIN Shows Policy ===")

    plants = run_sql("SELECT plant_id FROM factory.plant LIMIT 1")
    if not plants:
        print("  No plants found")
        return

    plant_id = plants[0][0]

    sql = f"""
    EXPLAIN SELECT machine_id FROM factory.machine WHERE health_pct > 50
    """

    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute(f"SET app.current_operator_plant = '{plant_id}'")
            cur.execute(sql)
            rows = cur.fetchall()
            print(f"\n  Query plan (should include RLS filter):")
            for row in rows:
                print(f"    {row[0]}")

def run_end_to_end():
    """Run all steps end to end."""
    print("\n" + "="*60)
    print("ROW-LEVEL SECURITY—MULTI-PLANT TENANCY")
    print("="*60)

    run_roles()
    run_policy()
    run_query()
    run_explain()

    print("\n" + "="*60)
    print("Done. See instructions.md for detailed explanations.")
    print("="*60)

def main():
    ap = argparse.ArgumentParser(description="RLS: multi-tenant tenancy")
    ap.add_argument("--step", choices=["roles", "policy", "query", "explain"],
                    help="Run a specific step (default: all)")
    args = ap.parse_args()

    if args.step == "roles":
        run_roles()
    elif args.step == "policy":
        run_policy()
    elif args.step == "query":
        run_query()
    elif args.step == "explain":
        run_explain()
    else:
        run_end_to_end()

if __name__ == "__main__":
    main()
