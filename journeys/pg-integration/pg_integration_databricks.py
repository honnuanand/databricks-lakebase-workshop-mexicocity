# Databricks notebook source
# MAGIC %md-sandbox
# MAGIC <div style="display:flex; align-items:center; gap:10px; padding:8px 16px; background:#F9F7F4; border-bottom:2px solid #E0E0E0; font-family:sans-serif; line-height:1;">
# MAGIC   <span style="display:inline-block; width:12px; height:12px; border-radius:2px; background:#FF3621;"></span>
# MAGIC   <span style="font-weight:bold; color:#0b2026;">Lakebase workshop</span>
# MAGIC   <span style="color:#999;">|</span>
# MAGIC   <span style="color:#5A6F77;">Part 1 · Journey 5 of 5 · Connecting Postgres Tools</span>
# MAGIC </div>

# COMMAND ----------

# MAGIC %md
# MAGIC # Connecting Postgres Tools
# MAGIC #### Duration: about 10 minutes
# MAGIC
# MAGIC *Journey 5 of 5. So far you've used Lakebase from this notebook. This journey shows what any Postgres tool sees when it connects.*
# MAGIC
# MAGIC ## Overview
# MAGIC
# MAGIC The bank's core platform, fraud engine, and risk and reporting apps already use SQLAlchemy, JDBC,
# MAGIC dbt, Metabase, and Tableau. If a new database needs its own drivers or adapters, every one of those
# MAGIC integrations has to be rebuilt. The question the team asks is simple: will the tools we already use
# MAGIC just work?
# MAGIC
# MAGIC Lakebase is Postgres, so they do. When a BI tool or an ORM connects, the first thing it does is read
# MAGIC Postgres's standard catalog, `information_schema`, to learn the tables and columns. In this lab you
# MAGIC run those same queries yourself.
# MAGIC
# MAGIC ## Learning objectives
# MAGIC
# MAGIC By the end of this lab, you will be able to:
# MAGIC
# MAGIC 1. **Discover the tables and columns** of a Lakebase database through `information_schema`.
# MAGIC 2. **Build the schema map** a BI tool or ORM builds when it connects.
# MAGIC 3. **Read sample rows** to confirm the data matches the schema.
# MAGIC 4. **Know what a Postgres tool needs to connect:** host, port, database, user, and a login token.

# COMMAND ----------

# MAGIC %md
# MAGIC ## Key concepts
# MAGIC
# MAGIC - **Postgres schema:** a named folder of tables inside a database. The workshop's tables are in the `bank` schema, so their full names are `bank.account`, `bank.txn`, and so on. (Not to be confused with "the schema" meaning the structure of the tables.)
# MAGIC - **`information_schema`:** a set of read-only views, defined by the SQL standard, that every Postgres database has. They describe the database itself: its schemas, tables, columns, and types. Querying them is how a tool learns what's in a database without being told.
# MAGIC - **Wire protocol:** the network language a client uses to talk to a database. Lakebase speaks the standard Postgres protocol, so any Postgres driver can connect.
# MAGIC - **ORM and BI tool:** an ORM (object-relational mapper, such as SQLAlchemy) lets application code work with tables as objects; a BI tool (such as Tableau or Power BI) builds reports and dashboards. Both discover tables and columns from the database's catalog, as you'll do here.
# MAGIC
# MAGIC More terms are defined in `docs/glossary.md` in the workshop folder.

# COMMAND ----------

# MAGIC %md-sandbox
# MAGIC ## A. Setup
# MAGIC
# MAGIC <div style="border-left:4px solid #1B5162; background:#EEF4F6; padding:12px 16px; border-radius:4px; margin:12px 0; font-family:sans-serif;">
# MAGIC   <strong style="display:block; color:#1B5162; margin-bottom:6px;">Before you start</strong>
# MAGIC   <div style="color:#333;">
# MAGIC     Run <code>00-setup/setup_databricks</code> once to create your branch and load the bank.
# MAGIC     If you just did Point-in-Time Restore, make sure you ran its reset cell.
# MAGIC     Attach this notebook to <strong>serverless</strong> compute.
# MAGIC   </div>
# MAGIC </div>

# COMMAND ----------

# MAGIC %md
# MAGIC ### A1. Install the driver and pick your branch
# MAGIC
# MAGIC Run the next three cells before anything else. They install the Postgres driver, upgrade the
# MAGIC Databricks SDK if your environment's version predates the Lakebase API, and set `LB_PROJECT`,
# MAGIC `LB_BRANCH`, and `LB_SCHEMA` from the widgets at the top of this notebook. `LB_BRANCH` defaults to
# MAGIC the branch `00-setup/setup_databricks` created for you. Change a widget only if you used a
# MAGIC different project or branch name.

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

# MAGIC %md-sandbox
# MAGIC **Expected result:** `signed in as` your email, followed by your project, branch, and schema:
# MAGIC
# MAGIC ```
# MAGIC signed in as alex.kim@example.com
# MAGIC   LB_PROJECT = bank
# MAGIC   LB_BRANCH = u-alex-kim
# MAGIC   LB_SCHEMA = bank
# MAGIC ```
# MAGIC
# MAGIC <div style="border-left:4px solid #FF9800; background:#FFF3E0; padding:12px 16px; border-radius:4px; margin:12px 0; font-family:sans-serif;">
# MAGIC   <strong style="display:block; color:#E65100; margin-bottom:6px;">Troubleshooting</strong>
# MAGIC   <div style="color:#333;">
# MAGIC     <ul style="margin:0; padding-left:20px;">
# MAGIC       <li><code>databricks-sdk ... predates the Lakebase API</code>: rerun the install cell and the restart cell, then this one.</li>
# MAGIC       <li><code>Fill in LB_BRANCH in the widgets at the top of the notebook</code>: type your branch name in the <code>LB_BRANCH</code> box, then rerun this cell.</li>
# MAGIC       <li>The widgets show an old branch name: run <code>dbutils.widgets.removeAll()</code> in a new cell, then rerun this one.</li>
# MAGIC     </ul>
# MAGIC   </div>
# MAGIC </div>

# COMMAND ----------

# MAGIC %md
# MAGIC ### A2. Load the helper
# MAGIC
# MAGIC This loads `run_sql()` from `common/scripts/`. It opens a connection to your branch, runs one SQL
# MAGIC statement, and returns any rows.
# MAGIC
# MAGIC Under the hood, `run_sql()` asks the Lakebase API for your branch's host name, gets a login token
# MAGIC from your Databricks identity (valid for about an hour), and opens a standard Postgres connection
# MAGIC with `psycopg`, a Postgres driver for Python.
# MAGIC
# MAGIC In the steps below, the SQL block in each step is the statement that runs on your branch. The Python
# MAGIC cell under it only sends that statement and prints the result.

# COMMAND ----------

import os, sys
sys.path.insert(0, os.path.join(os.getcwd(), "..", "..", "common", "scripts"))
from lakebase import run_sql, _env
from collections import defaultdict

SCHEMA = os.environ.get("LB_SCHEMA", "bank")
print(f"Schema: {SCHEMA}")

# COMMAND ----------

# MAGIC %md
# MAGIC **Expected result:** `Schema: bank`

# COMMAND ----------

# MAGIC %md
# MAGIC ## B. Discover the schema, the way a tool does
# MAGIC
# MAGIC ### B1. List the tables
# MAGIC
# MAGIC A standard Postgres catalog query. Any tool that connects runs something like it:
# MAGIC
# MAGIC ```sql
# MAGIC SELECT table_name FROM information_schema.tables
# MAGIC WHERE table_schema = 'bank' ORDER BY table_name;
# MAGIC ```

# COMMAND ----------

query = f"SELECT table_name FROM information_schema.tables WHERE table_schema='{SCHEMA}' ORDER BY table_name"
rows = run_sql(query)
tables = [row[0] for row in rows]
print(f"{len(tables)} tables discovered:")
for table in tables:
    print(f"  - {table}")

# COMMAND ----------

# MAGIC %md-sandbox
# MAGIC **Expected result:** `14 tables discovered:`, then one line per table: `account`, `agent_memory`,
# MAGIC `branch`, `case_note`, `counterparty`, `custodian`, `fund`, `holding`, `instrument`, `position`,
# MAGIC `settlement`, `trade`, `trade_counterparty`, `txn`.
# MAGIC
# MAGIC **What this proves:** with one standard query, you, or any tool, can list every table in the `bank` schema. No Lakebase-specific API is involved.
# MAGIC
# MAGIC <div style="border-left:4px solid #FF9800; background:#FFF3E0; padding:12px 16px; border-radius:4px; margin:12px 0; font-family:sans-serif;">
# MAGIC   <strong style="display:block; color:#E65100; margin-bottom:6px;">Troubleshooting</strong>
# MAGIC   <div style="color:#333;">
# MAGIC     <ul style="margin:0; padding-left:20px;">
# MAGIC       <li><code>0 tables discovered</code>: the bank isn't loaded on this branch, or <code>LB_SCHEMA</code> isn't <code>bank</code>. Check the widget, or run <code>00-setup/setup_databricks</code>.</li>
# MAGIC       <li><code>Missing required env var LB_PROJECT</code>: the A1 cells didn't run in this session. Run the three A1 cells, then A2 and this one.</li>
# MAGIC     </ul>
# MAGIC   </div>
# MAGIC </div>

# COMMAND ----------

# MAGIC %md
# MAGIC ### B2. List the columns and their types
# MAGIC
# MAGIC The cell prints the total, then the first few columns of the first three tables:
# MAGIC
# MAGIC ```sql
# MAGIC SELECT table_name, column_name, data_type
# MAGIC FROM information_schema.columns
# MAGIC WHERE table_schema = 'bank'
# MAGIC ORDER BY table_name, ordinal_position;
# MAGIC ```

# COMMAND ----------

query = (
    f"SELECT table_name, column_name, data_type "
    f"FROM information_schema.columns "
    f"WHERE table_schema='{SCHEMA}' "
    f"ORDER BY table_name, ordinal_position"
)
rows = run_sql(query)

# Group by table
by_table = defaultdict(list)
for table, column, dtype in rows:
    by_table[table].append((column, dtype))

print(f"{len(rows)} columns across {len(by_table)} tables")
for table in sorted(by_table.keys())[:3]:
    print(f"\n{table}:")
    for col, dtype in by_table[table][:5]:
        print(f"  {col}: {dtype}")

# COMMAND ----------

# MAGIC %md
# MAGIC **Expected result:** `77 columns across 14 tables` if you ran *Lakebase Data in the Lakehouse*,
# MAGIC which adds a `fraud_risk` column (76 on a freshly loaded branch). Then the first columns of
# MAGIC `account`, `agent_memory`, and `branch`:
# MAGIC
# MAGIC ```
# MAGIC account:
# MAGIC   account_id: text
# MAGIC   branch_id: text
# MAGIC   line: text
# MAGIC   type: text
# MAGIC   status: text
# MAGIC
# MAGIC agent_memory:
# MAGIC   id: bigint
# MAGIC   ...
# MAGIC
# MAGIC branch:
# MAGIC   branch_id: text
# MAGIC   ...
# MAGIC   lat: double precision
# MAGIC ```
# MAGIC
# MAGIC **What this proves:** the column names and types come from the same standard views. That's how a tool knows `health_pct` is a number and `status` is text before it reads any rows.

# COMMAND ----------

# MAGIC %md
# MAGIC ### B3. Build a schema map
# MAGIC
# MAGIC Add whether each column allows nulls, and you have the map a BI tool or ORM builds before it shows
# MAGIC you any data:
# MAGIC
# MAGIC ```sql
# MAGIC SELECT table_name, column_name, data_type, is_nullable
# MAGIC FROM information_schema.columns
# MAGIC WHERE table_schema = 'bank'
# MAGIC ORDER BY table_name, ordinal_position;
# MAGIC ```

# COMMAND ----------

query = (
    f"SELECT table_name, column_name, data_type, is_nullable "
    f"FROM information_schema.columns "
    f"WHERE table_schema='{SCHEMA}' "
    f"ORDER BY table_name, ordinal_position"
)
rows = run_sql(query)

schema_map = defaultdict(list)
for table, column, dtype, nullable in rows:
    schema_map[table].append({
        "column": column,
        "type": dtype,
        "nullable": nullable == "YES"
    })

print(f"\n=== Bank Schema Map ===")
total_cols = 0
for table in sorted(schema_map.keys())[:3]:
    print(f"\nTABLE: {table}")
    for col_info in schema_map[table][:4]:
        col = col_info["column"]
        dtype = col_info["type"]
        null_marker = "" if col_info["nullable"] else " NOT NULL"
        print(f"  {col}: {dtype}{null_marker}")
        total_cols += 1

print(f"\n=== Statistics ===")
print(f"Total tables: {len(schema_map)}")
print(f"Total columns: {len(rows)}")

# COMMAND ----------

# MAGIC %md
# MAGIC **Expected result:** `=== Bank Schema Map ===`, the first four columns of each of the first three
# MAGIC tables with `NOT NULL` where it applies (for example `account_id: text NOT NULL`), then:
# MAGIC
# MAGIC ```
# MAGIC === Statistics ===
# MAGIC Total tables: 14
# MAGIC Total columns: 77
# MAGIC ```
# MAGIC
# MAGIC As in B2, the total is 76 on a freshly loaded branch.
# MAGIC
# MAGIC **What this proves:** adding `is_nullable` gives a tool what it needs to build forms, reports, or ORM models, all from `information_schema`.

# COMMAND ----------

# MAGIC %md
# MAGIC ## C. Check the data
# MAGIC
# MAGIC Read a few rows from two tables to confirm the data matches the schema. The cell prints the first
# MAGIC three columns of each row:
# MAGIC
# MAGIC ```sql
# MAGIC SELECT * FROM bank.account LIMIT 3;
# MAGIC SELECT * FROM bank.trade LIMIT 3;
# MAGIC ```

# COMMAND ----------

# Sample account table
rows = run_sql(f"SELECT * FROM {SCHEMA}.account LIMIT 3")
print(f"Sample rows from account table:")
for row in rows:
    print(f"  {row[:3]}...")  # Show first 3 cols

# Sample trade table
rows = run_sql(f"SELECT * FROM {SCHEMA}.trade LIMIT 3")
print(f"\nSample rows from trade table:")
for row in rows:
    print(f"  {row[:3]}...")  # Show first 3 cols

# COMMAND ----------

# MAGIC %md-sandbox
# MAGIC **Expected result:**
# MAGIC
# MAGIC ```
# MAGIC Sample rows from account table:
# MAGIC   ('CTA-100234', 'BR-CDMX', 'Checking')...
# MAGIC   ('CTA-100235', 'BR-CDMX', 'Savings')...
# MAGIC   ('CTA-100240', 'BR-CDMX', 'Credit')...
# MAGIC
# MAGIC Sample rows from trade table:
# MAGIC   ('TRD-8821', 'BR-CDMX', 'FUND-GROWTH-A')...
# MAGIC   ('TRD-8822', 'BR-MTY', 'FUND-INCOME-B')...
# MAGIC ```
# MAGIC
# MAGIC **What this proves:** the data matches the structure the tool discovered.
# MAGIC
# MAGIC <div style="border-left:4px solid #FF9800; background:#FFF3E0; padding:12px 16px; border-radius:4px; margin:12px 0; font-family:sans-serif;">
# MAGIC   <strong style="display:block; color:#E65100; margin-bottom:6px;">Troubleshooting</strong>
# MAGIC   <div style="color:#333;">
# MAGIC     <ul style="margin:0; padding-left:20px;">
# MAGIC       <li><strong>No trade rows:</strong> <em>Point-in-Time Restore</em> deleted them on your branch. Run <code>import branch; branch.reset()</code> in a new cell to rebuild your branch, then rerun this cell.</li>
# MAGIC     </ul>
# MAGIC   </div>
# MAGIC </div>

# COMMAND ----------

# MAGIC %md-sandbox
# MAGIC ## D. Connect your own tools
# MAGIC
# MAGIC Any Postgres client connects with the same five settings this notebook uses: the branch's
# MAGIC **host**, port **5432**, database **databricks_postgres**, your **Databricks user name**, and a
# MAGIC **login token** as the password. Connections must use SSL (`sslmode=require`).
# MAGIC
# MAGIC <div style="border-left:4px solid #1B5162; background:#EEF4F6; padding:12px 16px; border-radius:4px; margin:12px 0; font-family:sans-serif;">
# MAGIC   <strong style="display:block; color:#1B5162; margin-bottom:6px;">See it in the UI (optional)</strong>
# MAGIC   <div style="color:#333;">
# MAGIC     In the <strong>Lakebase Postgres</strong> app, open your project and branch, then choose <strong>Connect</strong>
# MAGIC     under <strong>Computes</strong>. It shows the host and ready-made connection strings for <code>psql</code> and other
# MAGIC     clients. The <strong>Tables</strong> tab shows the same tables you just listed.
# MAGIC   </div>
# MAGIC </div>

# COMMAND ----------

# MAGIC %md-sandbox
# MAGIC ##### EXPAND FOR ADDITIONAL NOTES
# MAGIC
# MAGIC <details>
# MAGIC <summary><strong>Login tokens and long-running tools</strong></summary>
# MAGIC
# MAGIC The password is a short-lived token from your Databricks identity, not a stored password. It
# MAGIC expires after about an hour. That's fine for a notebook or script that asks for a new token each
# MAGIC time it connects, as this workshop's helper does.
# MAGIC
# MAGIC A tool that keeps a connection open for days, such as a BI server or an application, needs to get a
# MAGIC fresh token before the old one expires. Applications usually do this in their connection pool. The
# MAGIC *Building a Databricks App on Lakebase* journey shows how an app connects with its own service
# MAGIC principal.
# MAGIC
# MAGIC </details>

# COMMAND ----------

# MAGIC %md-sandbox
# MAGIC ##### Check your understanding
# MAGIC
# MAGIC <details>
# MAGIC <summary><strong>1. What is `information_schema`?</strong></summary>
# MAGIC
# MAGIC A set of standard, read-only views that describe the database's own schemas, tables, columns, and types.
# MAGIC
# MAGIC </details>
# MAGIC
# MAGIC <details>
# MAGIC <summary><strong>2. Why don't BI tools need a special Lakebase driver?</strong></summary>
# MAGIC
# MAGIC Lakebase speaks the standard Postgres wire protocol, so any Postgres driver connects.
# MAGIC
# MAGIC </details>
# MAGIC
# MAGIC <details>
# MAGIC <summary><strong>3. What does a tool use as its password?</strong></summary>
# MAGIC
# MAGIC A short-lived login token from your Databricks identity, valid for about an hour.
# MAGIC
# MAGIC </details>

# COMMAND ----------

# MAGIC %md
# MAGIC ## E. Conclusion
# MAGIC
# MAGIC In this lab you discovered the bank's schema the way a BI tool or ORM does, and checked the data.
# MAGIC Key takeaways:
# MAGIC
# MAGIC 1. **Lakebase is Postgres:** standard catalog queries, drivers, and tools work without adapters.
# MAGIC 2. **Tools discover the schema automatically** through `information_schema`.
# MAGIC 3. **Connecting takes five settings:** host, port 5432, database, your user name, and a login token,
# MAGIC    over SSL.
# MAGIC 4. **Login tokens are short-lived,** so long-running tools refresh them in their connection pool.
# MAGIC
# MAGIC That's the end of Part 1. Part 2 builds on the same bank: choose the track that fits your work.

# COMMAND ----------

# MAGIC %md
# MAGIC ---
# MAGIC **You've finished Part 1.** For Part 2, choose one track:
# MAGIC
# MAGIC - App developers: <a href="$../pg-json/pg_json_databricks">JSON Data with JSONB →</a>
# MAGIC - Agent developers: <a href="$../agent-memory/agent_memory_databricks">Shared Agent Memory →</a>
# MAGIC
# MAGIC <a href="$../../START_HERE">← Back to the table of contents</a>
