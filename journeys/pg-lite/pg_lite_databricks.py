# Databricks notebook source
# COMMAND ----------

# MAGIC # Postgres in your browser, step by step
# MAGIC
# MAGIC This journey is different: Postgres runs client-side using PGlite, a WebAssembly build of Postgres. There is no server connection and no Python script — instead, you open an HTML file in your browser and type SQL.
# MAGIC
# MAGIC **Before you start:** finish `00-setup/`.
# COMMAND ----------

# MAGIC ## What is PGlite?
# MAGIC
# MAGIC PGlite is Postgres compiled to WebAssembly (WASM). It runs entirely in your browser — no server, no network, no latency. Same Postgres SQL semantics, same data types, same functions. It is real Postgres, shrunk to 10 MB and embedded in a web page.
# COMMAND ----------

# MAGIC ## Step 1 — Open the interactive editor
# MAGIC
# MAGIC Open the file `../../common/pglite-demo.html` in your browser (or save it and open it as file://). Right-click on the file and select 'Open with Browser', or double-click it.
# MAGIC
# MAGIC You should see: 'PGlite ready. Type SQL and hit Run.'
# MAGIC
# MAGIC This notebook explains the concept. The interactive editor is in that HTML file.
# COMMAND ----------

# MAGIC ## Step 2 — Create a table
# MAGIC
# MAGIC In the HTML editor's SQL pane, type or paste:
# MAGIC
# MAGIC ```sql
# MAGIC CREATE TABLE accounts (
# MAGIC     id TEXT PRIMARY KEY,
# MAGIC     status TEXT,
# MAGIC     health NUMERIC
# MAGIC );
# MAGIC ```
# MAGIC
# MAGIC Hit 'Run SQL'. The table is created in the browser's memory.
# COMMAND ----------

# MAGIC ## Step 3 — Insert data
# MAGIC
# MAGIC ```sql
# MAGIC INSERT INTO accounts VALUES
# MAGIC     ('ACCT-100240', 'good_standing', 91.5),
# MAGIC     ('ACCT-100241', 'watch', 72.0),
# MAGIC     ('ACCT-100242', 'frozen', 45.0);
# MAGIC ```
# COMMAND ----------

# MAGIC ## Step 4 — Query the data
# MAGIC
# MAGIC ```sql
# MAGIC SELECT * FROM accounts WHERE health > 70;
# MAGIC ```
# MAGIC
# MAGIC Results appear instantly in the browser. No server round-trip.
# COMMAND ----------

# MAGIC ## Step 5 — Try window functions
# MAGIC
# MAGIC ```sql
# MAGIC SELECT
# MAGIC     id,
# MAGIC     status,
# MAGIC     health,
# MAGIC     ROW_NUMBER() OVER (ORDER BY health DESC) as rank
# MAGIC FROM accounts
# MAGIC ORDER BY rank;
# MAGIC ```
# COMMAND ----------

# MAGIC ## Step 6 — Try JSONB aggregation
# MAGIC
# MAGIC ```sql
# MAGIC SELECT
# MAGIC     status,
# MAGIC     jsonb_agg(jsonb_build_object('id', id, 'health', health)) as accounts
# MAGIC FROM accounts
# MAGIC GROUP BY status;
# MAGIC ```
# COMMAND ----------

# MAGIC ## Step 7 — Try upsert (ON CONFLICT)
# MAGIC
# MAGIC ```sql
# MAGIC INSERT INTO accounts VALUES ('ACCT-100240', 'good_standing', 99.0)
# MAGIC ON CONFLICT (id) DO UPDATE SET health = 99.0;
# MAGIC ```
# COMMAND ----------

# MAGIC ## Step 8 — Prove it is real Postgres
# MAGIC
# MAGIC ```sql
# MAGIC SELECT version();
# MAGIC ```
# MAGIC
# MAGIC You will see 'PostgreSQL on wasm32'. Same Postgres kernel.
# COMMAND ----------

# MAGIC ## What you learned
# MAGIC
# MAGIC Postgres runs client-side in WebAssembly. No server connection needed. Same SQL, same semantics, same reliability. This is how lightweight, embedded, and offline-first applications can use real Postgres — in the browser, on the phone, on the edge.
# MAGIC
# MAGIC Next: **Feature store served online** measures latency of materialized feature lookups at inference time.