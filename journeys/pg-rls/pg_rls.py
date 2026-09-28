#!/usr/bin/env python3
"""Row-level security, multi-plant tenancy with RLS policies.

Create roles for each operator/plant, define RLS policies, and verify
that the same query returns different rows for different operators.
"""
import argparse
import os, sys
# The shared Lakebase helper lives in common/scripts/. Make it importable
# from this journey folder no matter where you run the script from.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "common", "scripts"))
from lakebase import connect, run_sql

# Operator roles, one per real plant in the factory seed (PL-DETROIT, PL-AUSTIN, PL-MUNICH).
OPERATORS = {"op_detroit": "PL-DETROIT", "op_austin": "PL-AUSTIN", "op_munich": "PL-MUNICH"}


def run_roles():
    """Step 1: Create a restricted role per plant operator.

    Important: the row-level security policy is only enforced for a role that does
    NOT have the BYPASSRLS attribute (and is not the table owner). The workshop's
    own login often has BYPASSRLS, so to SEE isolation we create plain roles, grant
    ourselves membership, and later SET ROLE into them before querying.
    """
    print("\n=== Step 1: Create Roles ===")
    me_rows = run_sql("SELECT current_user")
    me = me_rows[0][0]
    with connect() as conn:
        with conn.cursor() as cur:
            for role in OPERATORS:
                cur.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", (role,))
                if cur.fetchone():
                    print(f"  role already exists: {role}")
                else:
                    cur.execute(f"CREATE ROLE {role}")
                    print(f"  created role: {role}")
                cur.execute(f"GRANT USAGE ON SCHEMA factory TO {role}")
                cur.execute(f"GRANT SELECT ON factory.machine TO {role}")
                # membership so we can SET ROLE into it to demonstrate enforcement
                cur.execute(f'GRANT {role} TO "{me}"')
            print("  granted schema/table SELECT and membership to all operator roles")

def run_policy():
    """Step 2: Create and enable RLS policy."""
    print("\n=== Step 2: Create RLS Policy ===")

    # ENABLE turns policies on, but the table OWNER bypasses them unless we also
    # FORCE row-level security. Without FORCE, the owner sees all rows and the demo
    # looks like it does nothing. FORCE makes the policy apply to the owner too.
    sql_enable = ("ALTER TABLE factory.machine ENABLE ROW LEVEL SECURITY;"
                  "ALTER TABLE factory.machine FORCE ROW LEVEL SECURITY;")
    # Postgres has no CREATE POLICY IF NOT EXISTS; drop any prior one, then create.
    sql_drop = "DROP POLICY IF EXISTS machine_operator_isolation ON factory.machine;"
    sql_policy = """
    CREATE POLICY machine_operator_isolation ON factory.machine
      FOR SELECT
      USING (plant_id = current_setting('app.current_operator_plant', true));
    """

    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute(sql_enable)
            cur.execute(sql_drop)
            cur.execute(sql_policy)
            print("  RLS enabled on factory.machine")
            print("  Policy created: machine_operator_isolation")

def run_query():
    """Step 3: The SAME query returns different rows for different operators.

    We SET ROLE into each restricted operator role (which does not bypass RLS),
    set its plant context, and run the identical SELECT. The database returns only
    that operator's machines, enforced by the policy, not by anything in the query.
    """
    print("\n=== Step 3: Same Query, Different Operators ===")
    sql = "SELECT machine_id, plant_id, status FROM factory.machine ORDER BY machine_id"

    with connect() as conn:
        with conn.cursor() as cur:
            for role, plant in OPERATORS.items():
                cur.execute(f"SET ROLE {role}")
                cur.execute(f"SET app.current_operator_plant = '{plant}'")
                cur.execute(sql)
                rows = cur.fetchall()
                cur.execute("RESET ROLE")
                cur.execute("RESET app.current_operator_plant")
                print(f"\n  as {role} (plant {plant}): {len(rows)} machines, the SAME query:")
                for row in rows:
                    print(f"    {row}")

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
    print("ROW-LEVEL SECURITY, MULTI-PLANT TENANCY")
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
