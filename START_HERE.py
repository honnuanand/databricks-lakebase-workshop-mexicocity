# Databricks notebook source
# MAGIC %md-sandbox
# MAGIC <div style="display:flex; align-items:center; gap:10px; padding:8px 16px; background:#F9F7F4; border-bottom:2px solid #E0E0E0; font-family:sans-serif; line-height:1;">
# MAGIC   <span style="display:inline-block; width:12px; height:12px; border-radius:2px; background:#FF3621;"></span>
# MAGIC   <span style="font-weight:bold; color:#0b2026;">Lakebase workshop</span>
# MAGIC   <span style="color:#999;">|</span>
# MAGIC   <span style="color:#5A6F77;">Start Here</span>
# MAGIC </div>

# COMMAND ----------

# MAGIC %md
# MAGIC # Start Here
# MAGIC
# MAGIC Run the setup notebook once, then work through Part 1 and Part 2, the App developers track.
# MAGIC Every notebook ends with a link to the next one and a link back to this page.
# MAGIC
# MAGIC *Versión en español:* <a href="$./START_HERE_es">Comienza aquí</a>

# COMMAND ----------

# MAGIC %md-sandbox
# MAGIC <div style="border-left:4px solid #1B5162; background:#EEF4F6; padding:12px 16px; border-radius:4px; margin:12px 0; font-family:sans-serif;">
# MAGIC   <strong style="display:block; color:#1B5162; margin-bottom:6px;">How the notebooks work</strong>
# MAGIC   <div style="color:#333;">
# MAGIC     Attach each notebook to <strong>serverless</strong> compute and run it top to bottom, one cell at a
# MAGIC     time. Every journey runs on your own branch of the bank database, so nothing you do affects anyone
# MAGIC     else. Each journey starts with the same three setup cells, and shows the expected output under
# MAGIC     every cell.
# MAGIC   </div>
# MAGIC </div>

# COMMAND ----------

# MAGIC %md
# MAGIC ## Before you start
# MAGIC
# MAGIC <a href="$./00-setup/setup_databricks">Setup: Create Your Branch</a>: creates your own branch of the
# MAGIC bank database, loads the data, and checks the connection. Run it once, top to bottom.

# COMMAND ----------

# MAGIC %md
# MAGIC ## Part 1. Lakebase core capabilities
# MAGIC
# MAGIC **About 60 minutes.** What makes Lakebase different from a regular Postgres database.
# MAGIC
# MAGIC | # | Journey | What you'll do |
# MAGIC | - | ------- | -------------- |
# MAGIC | 1 | <a href="$./journeys/branch-the-brain/branch_the_brain_databricks">Database Branching</a> | Fork the whole bank database in seconds, freeze an account on the fork, then throw the fork away with your branch untouched. |
# MAGIC | 2 | <a href="$./journeys/break-and-rewind/break_and_rewind_databricks">Point-in-Time Restore</a> | Delete trades and settlements on purpose, then recover them from the moment before the mistake. No backup job. |
# MAGIC | 3 | <a href="$./journeys/write-to-analytics/write_to_analytics_databricks">Lakebase Data in the Lakehouse</a> | Write a card transaction through Postgres, compute a fraud-risk score, write it back to the same row, and see the query the lakehouse uses to read it. |
# MAGIC | 4 | <a href="$./journeys/scale-to-zero/scale_to_zero_databricks">Scale to Zero</a> | Idle compute suspends itself and costs nothing; the next query wakes it up. |
# MAGIC | 5 | <a href="$./journeys/pg-integration/pg_integration_databricks">Connecting Postgres Tools</a> | Run the schema-discovery queries a standard Postgres or BI tool runs, and see the full bank schema. |

# COMMAND ----------

# MAGIC %md
# MAGIC ## Part 2. App developers
# MAGIC
# MAGIC **About 2 hours.** Build up to a Databricks App on Lakebase that uses everything in this track.
# MAGIC
# MAGIC | # | Journey | Time | What you'll do |
# MAGIC | - | ------- | ---- | -------------- |
# MAGIC | 1 | <a href="$./journeys/pg-json/pg_json_databricks">JSON Data with JSONB</a> | 20 min | Store varying instrument and fund spec sheets as JSONB, query them in SQL, and index them with GIN. |
# MAGIC | 2 | <a href="$./journeys/lakebase-search/lakebase_search_databricks">Lakebase Search</a> | 35 min | Search 40 fraud and AML notes by keyword (BM25), by meaning (real embeddings), and both at once (hybrid), filtered and joined to live accounts. Needs Lakebase Search enabled on your project (the journey shows how) and the `databricks-gte-large-en` embedding endpoint. |
# MAGIC | 3 | <a href="$./journeys/data-api/data_api_databricks">Lakebase Data API</a> | 20 min | Query your tables over HTTPS with an OAuth token and get JSON back. Needs the Data API enabled on your branch. |
# MAGIC | 4 | <a href="$./journeys/capstone-app/capstone_app_databricks">Building a Databricks App on Lakebase</a> | 45 min | Deploy a FastAPI dashboard on Databricks Apps from a notebook, with Lakebase as its backend. Needs permission to create apps. |
