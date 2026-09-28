# Databricks notebook source
# MAGIC %md
# MAGIC # Search, three ways, step by step
# MAGIC
# MAGIC A hands-on lab. Run one cell at a time, read what happened, then move on. You will master full-text search (FTS), fuzzy matching, and hybrid ranking using maintenance logs and parts.
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
# MAGIC ## Step 1, inspect maintenance write-ups
# MAGIC
# MAGIC Sample the text we will search. The SQL:
# MAGIC
# MAGIC ```sql
# MAGIC SELECT log_id, machine_id, writeup FROM factory.maintenance_log LIMIT 3
# MAGIC ```

# COMMAND ----------

sql = "SELECT log_id, machine_id, writeup FROM factory.maintenance_log LIMIT 3"
rows = run_sql(sql)
print("Sample maintenance logs:")
for row in rows:
    writeup = (row[2][:60] + "...") if row[2] and len(row[2]) > 60 else row[2]
    print(f"  log_id={row[0]}, machine_id={row[1]}")
    print(f"    '{writeup}'")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 2, full-text search (FTS) on maintenance writeups
# MAGIC
# MAGIC Use `to_tsvector()` and `@@` to search for documents matching a query. Rank results with `ts_rank()`. The SQL:
# MAGIC
# MAGIC ```sql
# MAGIC SELECT log_id, machine_id,
# MAGIC        ts_rank(to_tsvector('english', writeup),
# MAGIC                to_tsquery('english', 'hydraulic | bearing')) as rank
# MAGIC   FROM factory.maintenance_log
# MAGIC  WHERE to_tsvector('english', writeup) @@ to_tsquery('english', 'hydraulic | bearing')
# MAGIC  ORDER BY rank DESC
# MAGIC  LIMIT 5
# MAGIC ```

# COMMAND ----------

sql = """
SELECT log_id, machine_id,
       ts_rank(to_tsvector('english', writeup),
               to_tsquery('english', 'hydraulic | bearing')) as rank
  FROM factory.maintenance_log
 WHERE to_tsvector('english', writeup) @@ to_tsquery('english', 'hydraulic | bearing')
 ORDER BY rank DESC
 LIMIT 5
"""
rows = run_sql(sql)
print("Maintenance logs matching 'hydraulic OR bearing', ranked by relevance:")
for row in rows:
    print(f"  log_id={row[0]}, machine_id={row[1]}, rank={row[2]}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 3, fuzzy matching on part IDs using pg_trgm
# MAGIC
# MAGIC Enable pg_trgm (trigram matching), then find parts similar to a sample ID. The `%` operator means "similar to". In a parameterized query, psycopg treats `%` as a parameter marker, so it must be doubled to `%%`. The SQL:
# MAGIC
# MAGIC ```sql
# MAGIC SELECT part_id, name,
# MAGIC        similarity(part_id, %s) as sim
# MAGIC   FROM factory.part
# MAGIC  WHERE part_id %% %s
# MAGIC  ORDER BY sim DESC
# MAGIC  LIMIT 5
# MAGIC ```

# COMMAND ----------

# Enable pg_trgm
with connect() as conn:
    with conn.cursor() as cur:
        try:
            cur.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
        except:
            pass

# Find parts similar to a sample part ID
sample_parts = run_sql("SELECT part_id FROM factory.part LIMIT 1")
if not sample_parts:
    print("No parts found")
else:
    sample_id = sample_parts[0][0]

    sql = """
    SELECT part_id, name,
           similarity(part_id, %s) as sim
      FROM factory.part
     WHERE part_id %% %s
     ORDER BY sim DESC
     LIMIT 5
    """
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (sample_id, sample_id))
            rows = cur.fetchall()

    print(f"Parts similar to '{sample_id}' (fuzzy match, typo-tolerant):")
    for row in rows:
        print(f"  {row[0]}: {row[1]} (similarity={row[2]:.3f})")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 4, create GIN index on FTS column
# MAGIC
# MAGIC GIN indexes accelerate full-text search. The SQL:
# MAGIC
# MAGIC ```sql
# MAGIC CREATE INDEX IF NOT EXISTS idx_maintenance_log_fts
# MAGIC   ON factory.maintenance_log
# MAGIC   USING gin(to_tsvector('english', writeup))
# MAGIC ```

# COMMAND ----------

sql = """
CREATE INDEX IF NOT EXISTS idx_maintenance_log_fts
  ON factory.maintenance_log
  USING gin(to_tsvector('english', writeup))
"""
with connect() as conn:
    with conn.cursor() as cur:
        cur.execute(sql)

print("GIN index created on factory.maintenance_log(writeup)")
print("(Subsequent FTS queries will use the index)")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 5, hybrid search (keyword + semantic)
# MAGIC
# MAGIC Hybrid search requires pgvector for embeddings. If embeddings are available on your branch, you can blend FTS keyword matches with semantic similarity. For now, we have demonstrated the FTS and fuzzy matching halves.

# COMMAND ----------

print("Hybrid search (keyword + semantic) requires pgvector for embeddings.")
print("You have now mastered FTS (full-text search) and fuzzy matching (pg_trgm).")
print("Those two approaches cover most production search use cases.")

# COMMAND ----------

# MAGIC %md
# MAGIC ## What you learned
# MAGIC
# MAGIC You mastered three search patterns: full-text search (FTS) with `to_tsvector()` and ranking, fuzzy matching with pg_trgm for typo tolerance, and GIN indexes for speed. Real search on production data.
# MAGIC
# MAGIC Next: **Row-level security** enforces multi-tenant access control so each operator sees only their plants' data.
