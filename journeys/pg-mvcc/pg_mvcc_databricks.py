# Databricks notebook source
# MAGIC %md
# MAGIC # MVCC and the WAL, step by step
# MAGIC
# MAGIC A hands-on lab. Run one cell at a time, read what happened, then move on. You will query system columns (xmin, xmax, ctid), watch row versions change after an UPDATE, observe dead tuples accumulate, and run VACUUM to reclaim space.
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
# MAGIC ## Step 1, query system columns
# MAGIC
# MAGIC Postgres stores hidden columns on every row: xmin (transaction that inserted), xmax (transaction that deleted, or 0 if live), ctid (physical location). The SQL:
# MAGIC
# MAGIC ```sql
# MAGIC SELECT xmin, xmax, ctid, account_id, health_pct
# MAGIC   FROM bank.account
# MAGIC  WHERE account_id = %s
# MAGIC ```

# COMMAND ----------

accounts = run_sql("SELECT account_id FROM bank.account LIMIT 1")
if not accounts:
    print("No accounts found")
else:
    account_id = accounts[0][0]
    sql = """
    SELECT xmin, xmax, ctid, account_id, health_pct
      FROM bank.account
     WHERE account_id = %s
    """
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (account_id,))
            row = cur.fetchone()
            if row:
                print(f"xmin={row[0]}, xmax={row[1]}, ctid={row[2]}")
                print(f"account_id={row[3]}, health_pct={row[4]}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 2, UPDATE and watch versioning
# MAGIC
# MAGIC Run an UPDATE and see xmin, xmax, and ctid change as Postgres creates a new version. The SQL:
# MAGIC
# MAGIC ```sql
# MAGIC SELECT xmin, xmax, ctid, health_pct FROM bank.account WHERE account_id = %s;
# MAGIC UPDATE bank.account SET health_pct = 50.0 WHERE account_id = %s;
# MAGIC SELECT xmin, xmax, ctid, health_pct FROM bank.account WHERE account_id = %s
# MAGIC ```

# COMMAND ----------

accounts = run_sql("SELECT account_id FROM bank.account LIMIT 1")
if not accounts:
    print("No accounts found")
else:
    account_id = accounts[0][0]

    with connect() as conn:
        with conn.cursor() as cur:
            # Query before
            cur.execute("SELECT xmin, xmax, ctid, health_pct FROM bank.account WHERE account_id = %s", (account_id,))
            before = cur.fetchone()
            print("Before UPDATE:")
            if before:
                print(f"  xmin={before[0]}, xmax={before[1]}, ctid={before[2]}, health_pct={before[3]}")

            # UPDATE
            cur.execute("UPDATE bank.account SET health_pct = 50.0 WHERE account_id = %s", (account_id,))
            print("\nRunning UPDATE...")

            # Query after
            cur.execute("SELECT xmin, xmax, ctid, health_pct FROM bank.account WHERE account_id = %s", (account_id,))
            after = cur.fetchone()
            print("\nAfter UPDATE:")
            if after:
                print(f"  xmin={after[0]}, xmax={after[1]}, ctid={after[2]}, health_pct={after[3]}")

            if before and after:
                if before[0] != after[0]:
                    print(f"\nNote: xmin changed ({before[0]} → {after[0]}), new version created")
                if before[2] != after[2]:
                    print(f"Note: ctid changed ({before[2]} → {after[2]}), new physical location")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 3, dead tuples accumulate
# MAGIC
# MAGIC Run multiple UPDATEs and watch the dead tuple count grow. The SQL:
# MAGIC
# MAGIC ```sql
# MAGIC SELECT n_live_tup, n_dead_tup FROM pg_stat_user_tables WHERE relname = 'account';
# MAGIC -- Run multiple UPDATEs
# MAGIC UPDATE bank.account SET health_pct = health_pct + 1.0 WHERE account_id = %s  -- repeat 10 times
# MAGIC ```

# COMMAND ----------

accounts = run_sql("SELECT account_id FROM bank.account LIMIT 1")
if not accounts:
    print("No accounts found")
else:
    account_id = accounts[0][0]

    with connect() as conn:
        with conn.cursor() as cur:
            # Before UPDATEs
            cur.execute("SELECT n_live_tup, n_dead_tup FROM pg_stat_user_tables WHERE relname = 'account'")
            before = cur.fetchone()
            print("Before UPDATEs:")
            if before:
                print(f"  n_live_tup={before[0]}, n_dead_tup={before[1]}")

            # Run 10 UPDATEs
            for i in range(10):
                cur.execute("UPDATE bank.account SET health_pct = health_pct + 1.0 WHERE account_id = %s", (account_id,))

            print("\nAfter 10 UPDATEs:")

            # After UPDATEs
            cur.execute("SELECT n_live_tup, n_dead_tup FROM pg_stat_user_tables WHERE relname = 'account'")
            after = cur.fetchone()
            if after:
                print(f"  n_live_tup={after[0]}, n_dead_tup={after[1]}")
                if before and after[1] > before[1]:
                    print(f"  Dead tuples increased by {after[1] - before[1]}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 4, VACUUM reclaims space
# MAGIC
# MAGIC Run VACUUM to remove dead tuples and reclaim space. The SQL:
# MAGIC
# MAGIC ```sql
# MAGIC SELECT n_live_tup, n_dead_tup FROM pg_stat_user_tables WHERE relname = 'account';
# MAGIC VACUUM bank.account;
# MAGIC SELECT n_live_tup, n_dead_tup FROM pg_stat_user_tables WHERE relname = 'account'
# MAGIC ```

# COMMAND ----------

with connect() as conn:
    with conn.cursor() as cur:
        # Before VACUUM
        cur.execute("SELECT n_live_tup, n_dead_tup FROM pg_stat_user_tables WHERE relname = 'account'")
        before = cur.fetchone()
        print("Before VACUUM:")
        if before:
            print(f"  n_live_tup={before[0]}, n_dead_tup={before[1]}")

        # VACUUM
        cur.execute("VACUUM bank.account")
        print("\nRunning VACUUM...")

        # After VACUUM
        cur.execute("SELECT n_live_tup, n_dead_tup FROM pg_stat_user_tables WHERE relname = 'account'")
        after = cur.fetchone()
        print("\nAfter VACUUM:")
        if after:
            print(f"  n_live_tup={after[0]}, n_dead_tup={after[1]}")
            if before and after[1] < before[1]:
                print(f"  Dead tuples reclaimed: {before[1] - after[1]}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## What you learned
# MAGIC
# MAGIC You explored MVCC: Postgres stores multiple versions of rows (xmin, xmax, ctid) so readers do not block writers. UPDATEs create new versions, leaving old ones marked dead. VACUUM removes dead tuples and reclaims space. This is the machinery behind "consistent reads" and "no blocking."
# MAGIC
# MAGIC You have mastered the core SQL, performance, and concurrency features of Postgres. From window functions and recursive CTEs to JSONB, spatial queries, search, RLS, constraints, indexes, and MVCC, Postgres gives you a complete data engine.
