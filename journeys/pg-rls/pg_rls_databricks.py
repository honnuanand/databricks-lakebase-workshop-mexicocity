# Databricks notebook source
# MAGIC %md
# MAGIC # Row-level security, step by step
# MAGIC
# MAGIC A hands-on lab. Run one cell at a time, read what happened, then move on. You will create roles for plant operators, define RLS policies, and verify that different operators see different data from the same query.
# MAGIC
# MAGIC Each step shows the real interface: SQL where the step is a query, and Python for control operations.
# MAGIC
# MAGIC **Before you start:** finish `00-setup/` so `LB_PROFILE`, `LB_PROJECT`, `LB_BRANCH`, `LB_SCHEMA` are set and the factory is loaded on your branch.

# COMMAND ----------

# MAGIC %md
# MAGIC ## Setup, connect to your branch

# COMMAND ----------

import os, sys
sys.path.insert(0, os.path.join(os.getcwd(), "..", "..", "common", "scripts"))
from lakebase import connect, run_sql

SCHEMA = os.environ.get("LB_SCHEMA", "factory")
print("connected; schema:", SCHEMA)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 1, create roles for plant operators
# MAGIC
# MAGIC Create restricted roles for each operator at a real plant (Detroit, Austin, Munich, the plants in the factory seed). Grant schema access and membership so we can SET ROLE into them to demonstrate RLS enforcement. The SQL:
# MAGIC
# MAGIC ```sql
# MAGIC SELECT 1 FROM pg_roles WHERE rolname = 'op_detroit';
# MAGIC CREATE ROLE op_detroit;
# MAGIC GRANT USAGE ON SCHEMA factory TO op_detroit;
# MAGIC GRANT SELECT ON factory.machine TO op_detroit;
# MAGIC GRANT op_detroit TO current_user;
# MAGIC ```

# COMMAND ----------

# Operator roles, one per real plant in the factory seed.
operators = {"op_detroit": "PL-DETROIT", "op_austin": "PL-AUSTIN", "op_munich": "PL-MUNICH"}

me_rows = run_sql("SELECT current_user")
me = me_rows[0][0]

with connect() as conn:
    with conn.cursor() as cur:
        for role, plant in operators.items():
            # Check if role exists via catalog, since CREATE ROLE IF NOT EXISTS is invalid in Postgres
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

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 2, create and enable RLS policy
# MAGIC
# MAGIC Enable RLS on the machine table with both ENABLE and FORCE (FORCE makes the policy apply to the table owner too). Then create a policy that filters rows based on the plant context variable. The SQL:
# MAGIC
# MAGIC ```sql
# MAGIC ALTER TABLE factory.machine ENABLE ROW LEVEL SECURITY;
# MAGIC ALTER TABLE factory.machine FORCE ROW LEVEL SECURITY;
# MAGIC DROP POLICY IF EXISTS machine_operator_isolation ON factory.machine;
# MAGIC CREATE POLICY machine_operator_isolation ON factory.machine
# MAGIC   FOR SELECT
# MAGIC   USING (plant_id = current_setting('app.current_operator_plant', true))
# MAGIC ```

# COMMAND ----------

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
  USING (plant_id = current_setting('app.current_operator_plant', true))
"""

with connect() as conn:
    with conn.cursor() as cur:
        cur.execute(sql_enable)
        cur.execute(sql_drop)
        cur.execute(sql_policy)
        print("  RLS enabled on factory.machine")
        print("  Policy created: machine_operator_isolation")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 3, same query, different operators
# MAGIC
# MAGIC Set each operator role, set its plant context, and run the same SELECT. The database returns only that operator's machines, enforced by the policy. We SET ROLE into each operator because RLS is only enforced for a role that does NOT have BYPASSRLS (and is not the table owner). The query is identical; only the context changes. The SQL:
# MAGIC
# MAGIC ```sql
# MAGIC SET ROLE op_detroit;
# MAGIC SET app.current_operator_plant = 'PL-DETROIT';
# MAGIC SELECT machine_id, plant_id, status FROM factory.machine ORDER BY machine_id;
# MAGIC RESET ROLE;
# MAGIC RESET app.current_operator_plant;
# MAGIC ```

# COMMAND ----------

# Operator roles, one per real plant in the factory seed.
operators = {"op_detroit": "PL-DETROIT", "op_austin": "PL-AUSTIN", "op_munich": "PL-MUNICH"}

sql = "SELECT machine_id, plant_id, status FROM factory.machine ORDER BY machine_id"

with connect() as conn:
    with conn.cursor() as cur:
        for role, plant in operators.items():
            cur.execute(f"SET ROLE {role}")
            cur.execute(f"SET app.current_operator_plant = '{plant}'")
            cur.execute(sql)
            rows = cur.fetchall()
            cur.execute("RESET ROLE")
            cur.execute("RESET app.current_operator_plant")
            print(f"\n  as {role} (plant {plant}): {len(rows)} machines, the SAME query:")
            for row in rows:
                print(f"    {row}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 4, EXPLAIN shows RLS policy in query plan
# MAGIC
# MAGIC Run EXPLAIN to see the RLS filter in the query plan. The SQL:
# MAGIC
# MAGIC ```sql
# MAGIC SET app.current_operator_plant = 'PLANT-ID';
# MAGIC EXPLAIN SELECT machine_id FROM factory.machine WHERE health_pct > 50
# MAGIC ```

# COMMAND ----------

plants = run_sql("SELECT plant_id FROM factory.plant LIMIT 1")
if not plants:
    print("No plants found")
else:
    plant_id = plants[0][0]

    sql = "EXPLAIN SELECT machine_id FROM factory.machine WHERE health_pct > 50"

    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute(f"SET app.current_operator_plant = '{plant_id}'")
            cur.execute(sql)
            rows = cur.fetchall()
            print("Query plan (should include RLS filter):")
            for row in rows:
                print(f"  {row[0]}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## What you learned
# MAGIC
# MAGIC You implemented row-level security (RLS) for multi-tenant access control. Roles, policies, and context variables work together so operators see only their plant's data. RLS is enforced at the database level, not the application.
# MAGIC
# MAGIC Next: **No double-booking** uses exclusion constraints to prevent overlapping operations on the same machine.
