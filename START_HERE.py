# Databricks notebook source
# MAGIC %md
# MAGIC # Lakebase workshop: start here
# MAGIC
# MAGIC Run the setup notebook once, then work through Part 1. For Part 2, pick one of the two tracks.
# MAGIC Every notebook ends with a link to the next one in its path and a link back to this page.
# MAGIC
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
# MAGIC ## Part 2. Choose one track
# MAGIC
# MAGIC ### App developers (about 2.5 hours)
# MAGIC
# MAGIC | # | Journey | Time | What you'll do |
# MAGIC | - | ------- | ---- | -------------- |
# MAGIC | 1 | <a href="$./journeys/pg-json/pg_json_databricks">JSON Data with JSONB</a> | 20 min | Store varying instrument and fund spec sheets as JSONB, query them in SQL, and index them with GIN. |
# MAGIC | 2 | <a href="$./journeys/pg-vector/pg_vector_databricks">Vector Similarity Search</a> | 20 min | Find the instruments most similar to a holding by embedding similarity, next to your transactional data. |
# MAGIC | 3 | <a href="$./journeys/pg-search/pg_search_databricks">Full-Text and Fuzzy Search</a> | 30 min | Keyword, typo-tolerant, and hybrid search over fraud and AML case notes. |
# MAGIC | 4 | <a href="$./journeys/pg-booking/pg_booking_databricks">Preventing Overlapping Schedules</a> | 20 min | The database refuses two overlapping settlement windows on the same account. |
# MAGIC | 5 | <a href="$./journeys/data-api/data_api_databricks">Lakebase Data API</a> | 20 min | Query your tables over HTTPS with an OAuth token and get JSON back. |
# MAGIC | 6 | <a href="$./journeys/capstone-app/capstone_app_databricks">Building a Databricks App on Lakebase</a> | 45 min | Deploy a FastAPI dashboard on Databricks Apps, with Lakebase as its backend. |
# MAGIC
# MAGIC ### Agent developers (about 1.5 hours)
# MAGIC
# MAGIC | # | Journey | Time | What you'll do |
# MAGIC | - | ------- | ---- | -------------- |
# MAGIC | 1 | <a href="$./journeys/agent-memory/agent_memory_databricks">Shared Agent Memory</a> | 20 min | Two agents share one memory table: one writes a fraud note, the other reads it and acts on it. |
# MAGIC | 2 | <a href="$./journeys/agentic-work/agentic_work_databricks">Tool-Calling Agents</a> | 20 min | An agent reads live transactions with a tool, places a hold on a flagged account, and remembers it so it won't hold twice. |
# MAGIC | 3 | <a href="$./journeys/learning-loop/learning_loop_databricks">Human Review of AI Output</a> | 25 min | AI extracts findings from case notes with a confidence score; low-confidence ones go to a human analyst. |
# MAGIC | 4 | <a href="$./journeys/pg-vector/pg_vector_databricks">Vector Similarity Search</a> | 20 min | Find the instruments most similar to a holding by embedding similarity, next to your transactional data. |
# MAGIC | 5 | <a href="$./journeys/pg-features/pg_features_databricks">Online Feature Serving</a> | 10 min | Serve an account's fraud-risk features from Lakebase with a fast key lookup. |
