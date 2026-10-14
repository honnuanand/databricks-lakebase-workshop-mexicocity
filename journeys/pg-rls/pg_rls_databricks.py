# Databricks notebook source
# MAGIC %md
# MAGIC # Row-level security, step by step
# MAGIC
# MAGIC A hands-on lab. Run one cell at a time, read what happened, then move on. You will create roles for business unit operators, define RLS policies, and verify that different operators see different data from the same query.
# MAGIC
# MAGIC Each step shows the real interface: SQL where the step is a query, and Python for control operations.
# MAGIC
# MAGIC **Before you start:** run `00-setup/setup_databricks` once to create your branch, then run the setup cells below.

# COMMAND ----------

# MAGIC %md
# MAGIC ## Run first: install the driver and pick your branch
# MAGIC Run the next three cells before anything else. They install the Postgres driver, upgrade the
# MAGIC Databricks SDK if your environment's version predates the Lakebase API, and set `LB_PROJECT`,
# MAGIC `LB_BRANCH`, and `LB_SCHEMA` from the widgets at the top of this notebook.
# MAGIC `LB_BRANCH` defaults to the branch `00-setup/setup_databricks` created for you. Change a widget
# MAGIC only if you used a different project or branch name.

# COMMAND ----------

# MAGIC %pip install "databricks-sdk>=0.120.0" "psycopg[binary]==3.3.4"

# COMMAND ----------

dbutils.library.restartPython()

# COMMAND ----------

import os, sys
sys.path.insert(0, os.path.join(os.getcwd(), "..", "..", "common", "scripts"))
from lakebase import notebook_env
notebook_env(dbutils);

# COMMAND ----------

# MAGIC %md
# MAGIC ## Setup, connect to your branch

# COMMAND ----------

import os, sys
sys.path.insert(0, os.path.join(os.getcwd(), "..", "..", "common", "scripts"))
from lakebase import connect, run_sql

SCHEMA = os.environ.get("LB_SCHEMA", "bank")
print("connected; schema:", SCHEMA)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 1, create roles for business unit operators
# MAGIC
# MAGIC Create restricted roles for each business unit (RetailBank and GlobalMarkets from the bank seed). Grant schema access and membership so we can SET ROLE into them to demonstrate RLS enforcement. The SQL:
# MAGIC
# MAGIC ```sql
# MAGIC SELECT 1 FROM pg_roles WHERE rolname = 'bu_retailbank';
# MAGIC CREATE ROLE bu_retailbank;
# MAGIC GRANT USAGE ON SCHEMA bank TO bu_retailbank;
# MAGIC GRANT SELECT ON bank.account TO bu_retailbank;
# MAGIC GRANT bu_retailbank TO current_user;
# MAGIC ```

# COMMAND ----------

# Business unit roles, one per BU in the bank seed.
operators = {"bu_retailbank": "RetailBank", "bu_globalmarkets": "GlobalMarkets"}

me_rows = run_sql("SELECT current_user")
me = me_rows[0][0]

with connect() as conn:
    with conn.cursor() as cur:
        for role, bu in operators.items():
            # Check if role exists via catalog, since CREATE ROLE IF NOT EXISTS is invalid in Postgres
            cur.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", (role,))
            if cur.fetchone():
                print(f"  role already exists: {role}")
            else:
                cur.execute(f"CREATE ROLE {role}")
                print(f"  created role: {role}")
            cur.execute(f"GRANT USAGE ON SCHEMA bank TO {role}")
            cur.execute(f"GRANT SELECT ON bank.account TO {role}")
            # membership so we can SET ROLE into it to demonstrate enforcement
            cur.execute(f'GRANT {role} TO "{me}"')
        print("  granted schema/table SELECT and membership to all business unit roles")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 2, create and enable RLS policy
# MAGIC
# MAGIC Enable RLS on the account table with both ENABLE and FORCE (FORCE makes the policy apply to the table owner too). Then create a policy that filters rows based on the business unit context variable. The SQL:
# MAGIC
# MAGIC ```sql
# MAGIC ALTER TABLE bank.account ENABLE ROW LEVEL SECURITY;
# MAGIC ALTER TABLE bank.account FORCE ROW LEVEL SECURITY;
# MAGIC DROP POLICY IF EXISTS account_bu_isolation ON bank.account;
# MAGIC CREATE POLICY account_bu_isolation ON bank.account
# MAGIC   FOR SELECT
# MAGIC   USING (branch_id IN (
# MAGIC     SELECT branch_id FROM bank.branch
# MAGIC     WHERE operator = current_setting('app.current_bu', true)
# MAGIC   ))
# MAGIC ```

# COMMAND ----------

# ENABLE turns policies on, but the table OWNER bypasses them unless we also
# FORCE row-level security. Without FORCE, the owner sees all rows and the demo
# looks like it does nothing. FORCE makes the policy apply to the owner too.
sql_enable = ("ALTER TABLE bank.account ENABLE ROW LEVEL SECURITY;"
              "ALTER TABLE bank.account FORCE ROW LEVEL SECURITY;")
# Postgres has no CREATE POLICY IF NOT EXISTS; drop any prior one, then create.
sql_drop = "DROP POLICY IF EXISTS account_bu_isolation ON bank.account;"
sql_policy = """
CREATE POLICY account_bu_isolation ON bank.account
  FOR SELECT
  USING (branch_id IN (
    SELECT branch_id FROM bank.branch
    WHERE operator = current_setting('app.current_bu', true)
  ))
"""

with connect() as conn:
    with conn.cursor() as cur:
        cur.execute(sql_enable)
        cur.execute(sql_drop)
        cur.execute(sql_policy)
        print("  RLS enabled on bank.account")
        print("  Policy created: account_bu_isolation")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 3, same query, different business units
# MAGIC
# MAGIC Set each business unit role, set its context, and run the same SELECT. The database returns only that business unit's accounts, enforced by the policy. We SET ROLE into each BU because RLS is only enforced for a role that does NOT have BYPASSRLS (and is not the table owner). The query is identical; only the context changes. The SQL:
# MAGIC
# MAGIC ```sql
# MAGIC SET ROLE bu_retailbank;
# MAGIC SET app.current_bu = 'RetailBank';
# MAGIC SELECT account_id, branch_id, status FROM bank.account ORDER BY account_id;
# MAGIC RESET ROLE;
# MAGIC RESET app.current_bu;
# MAGIC ```

# COMMAND ----------

# Business unit roles, one per BU in the bank seed.
operators = {"bu_retailbank": "RetailBank", "bu_globalmarkets": "GlobalMarkets"}

sql = "SELECT account_id, branch_id, status FROM bank.account ORDER BY account_id"

with connect() as conn:
    with conn.cursor() as cur:
        for role, bu in operators.items():
            cur.execute(f"SET ROLE {role}")
            cur.execute(f"SET app.current_bu = '{bu}'")
            cur.execute(sql)
            rows = cur.fetchall()
            cur.execute("RESET ROLE")
            cur.execute("RESET app.current_bu")
            print(f"\n  as {role} (business unit {bu}): {len(rows)} accounts, the SAME query:")
            for row in rows:
                print(f"    {row}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 4, EXPLAIN shows RLS policy in query plan
# MAGIC
# MAGIC Run EXPLAIN to see the RLS filter in the query plan. The SQL:
# MAGIC
# MAGIC ```sql
# MAGIC SET app.current_bu = 'RetailBank';
# MAGIC EXPLAIN SELECT account_id FROM bank.account WHERE health_pct > 50
# MAGIC ```

# COMMAND ----------

branches = run_sql("SELECT operator FROM bank.branch LIMIT 1")
if not branches:
    print("No branches found")
else:
    bu = branches[0][0]

    sql = "EXPLAIN SELECT account_id FROM bank.account WHERE health_pct > 50"

    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute(f"SET app.current_bu = '{bu}'")
            cur.execute(sql)
            rows = cur.fetchall()
            print("Query plan (should include RLS filter):")
            for row in rows:
                print(f"  {row[0]}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## What you learned
# MAGIC
# MAGIC You implemented row-level security (RLS) for multi-business-unit access control. Roles, policies, and context variables work together so operators see only their business unit's accounts. RLS is enforced at the database level, not the application.
# MAGIC
# MAGIC Next: **No double-booking** uses exclusion constraints to prevent overlapping settlements on the same account.
