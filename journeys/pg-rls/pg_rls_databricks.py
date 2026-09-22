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
# MAGIC Create roles representing operators at different plants. The SQL:
# MAGIC
# MAGIC ```sql
# MAGIC CREATE ROLE IF NOT EXISTS operator_detroit;
# MAGIC CREATE ROLE IF NOT EXISTS operator_chicago;
# MAGIC CREATE ROLE IF NOT EXISTS operator_toronto;
# MAGIC GRANT USAGE ON SCHEMA factory TO operator_detroit, operator_chicago, operator_toronto;
# MAGIC GRANT SELECT ON ALL TABLES IN SCHEMA factory TO operator_detroit, operator_chicago, operator_toronto;
# MAGIC ```

# COMMAND ----------

roles = ["operator_detroit", "operator_chicago", "operator_toronto"]

with connect() as conn:
    with conn.cursor() as cur:
        for role in roles:
            try:
                cur.execute(f"CREATE ROLE IF NOT EXISTS {role}")
                print(f"Created role: {role}")
            except Exception as e:
                print(f"{role} exists or error: {e}")

        # Grant permissions
        cur.execute(f"GRANT USAGE ON SCHEMA factory TO {', '.join(roles)}")
        cur.execute(f"GRANT SELECT ON ALL TABLES IN SCHEMA factory TO {', '.join(roles)}")
        print(f"Granted permissions to all roles")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 2, create and enable RLS policy
# MAGIC
# MAGIC Enable RLS on the machine table, then create a policy that filters rows based on the app context variable. The SQL:
# MAGIC
# MAGIC ```sql
# MAGIC ALTER TABLE factory.machine ENABLE ROW LEVEL SECURITY;
# MAGIC CREATE POLICY IF NOT EXISTS machine_operator_isolation ON factory.machine
# MAGIC   FOR SELECT
# MAGIC   USING (plant_id = current_setting('app.current_operator_plant', true))
# MAGIC ```

# COMMAND ----------

sql_enable = "ALTER TABLE factory.machine ENABLE ROW LEVEL SECURITY"
sql_policy = """
CREATE POLICY IF NOT EXISTS machine_operator_isolation ON factory.machine
  FOR SELECT
  USING (plant_id = current_setting('app.current_operator_plant', true))
"""

with connect() as conn:
    with conn.cursor() as cur:
        cur.execute(sql_enable)
        cur.execute(sql_policy)
        print("RLS enabled on factory.machine")
        print("Policy created: machine_operator_isolation")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 3, query with RLS for different operators
# MAGIC
# MAGIC Set the app context and query the machine table. The same query returns different rows depending on the operator context. The SQL:
# MAGIC
# MAGIC ```sql
# MAGIC SET app.current_operator_plant = 'PLANT-ID';
# MAGIC SELECT machine_id, plant_id, status FROM factory.machine
# MAGIC ```

# COMMAND ----------

# Get a sample plant
plants = run_sql("SELECT plant_id FROM factory.plant LIMIT 1")
if not plants:
    print("No plants found")
else:
    plant_id = plants[0][0]

    sql = "SELECT machine_id, plant_id, status FROM factory.machine"

    with connect() as conn:
        with conn.cursor() as cur:
            # Query as if operator_detroit
            cur.execute(f"SET app.current_operator_plant = '{plant_id}'")
            cur.execute(sql)
            rows = cur.fetchall()
            print(f"Querying as operator for plant {plant_id}:")
            for row in rows[:5]:
                print(f"  {row}")
            if len(rows) > 5:
                print(f"  ... ({len(rows)} total rows)")

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
