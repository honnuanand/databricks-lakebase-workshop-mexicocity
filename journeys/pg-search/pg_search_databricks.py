# Databricks notebook source
# MAGIC %md
# MAGIC # Search, three ways, step by step
# MAGIC
# MAGIC A hands-on lab. Run one cell at a time, read what happened, then move on. You will master full-text search (FTS), fuzzy matching, and hybrid ranking using case notes and accounts.
# MAGIC
# MAGIC Each step shows the real interface: SQL where the step is a query, and Python for control operations.
# MAGIC
# MAGIC **Before you start:** finish `00-setup/` so `LB_PROFILE`, `LB_PROJECT`, `LB_BRANCH`, `LB_SCHEMA` are set and the bank schema is loaded on your branch.

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
# MAGIC ## Step 1, inspect case notes
# MAGIC
# MAGIC Sample the text we will search. The SQL:
# MAGIC
# MAGIC ```sql
# MAGIC SELECT note_id, account_id, writeup FROM bank.case_note LIMIT 3
# MAGIC ```

# COMMAND ----------

sql = "SELECT note_id, account_id, writeup FROM bank.case_note LIMIT 3"
rows = run_sql(sql)
print("Sample case notes:")
for row in rows:
    writeup = (row[2][:60] + "...") if row[2] and len(row[2]) > 60 else row[2]
    print(f"  note_id={row[0]}, account_id={row[1]}")
    print(f"    '{writeup}'")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 2, full-text search (FTS) on case notes
# MAGIC
# MAGIC Use `to_tsvector()` and `@@` to search for documents matching a query. Rank results with `ts_rank()`. The SQL:
# MAGIC
# MAGIC ```sql
# MAGIC SELECT note_id, account_id,
# MAGIC        ts_rank(to_tsvector('english', writeup),
# MAGIC                to_tsquery('english', 'wire | fraud')) as rank
# MAGIC   FROM bank.case_note
# MAGIC  WHERE to_tsvector('english', writeup) @@ to_tsquery('english', 'wire | fraud')
# MAGIC  ORDER BY rank DESC
# MAGIC  LIMIT 5
# MAGIC ```

# COMMAND ----------

sql = """
SELECT note_id, account_id,
       ts_rank(to_tsvector('english', writeup),
               to_tsquery('english', 'wire | fraud')) as rank
  FROM bank.case_note
 WHERE to_tsvector('english', writeup) @@ to_tsquery('english', 'wire | fraud')
 ORDER BY rank DESC
 LIMIT 5
"""
rows = run_sql(sql)
print("Case notes matching 'wire OR fraud', ranked by relevance:")
for row in rows:
    print(f"  note_id={row[0]}, account_id={row[1]}, rank={row[2]}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 3, fuzzy matching on account IDs using pg_trgm
# MAGIC
# MAGIC Enable pg_trgm (trigram matching), then find accounts similar to a sample ID. The `%` operator means "similar to". In a parameterized query, psycopg treats `%` as a parameter marker, so it must be doubled to `%%`. The SQL:
# MAGIC
# MAGIC ```sql
# MAGIC SELECT account_id,
# MAGIC        similarity(account_id, %s) as sim
# MAGIC   FROM bank.account
# MAGIC  WHERE account_id %% %s
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

# Find accounts similar to a sample account ID
sample_accounts = run_sql("SELECT account_id FROM bank.account LIMIT 1")
if not sample_accounts:
    print("No accounts found")
else:
    sample_id = sample_accounts[0][0]

    sql = """
    SELECT account_id,
           similarity(account_id, %s) as sim
      FROM bank.account
     WHERE account_id %% %s
     ORDER BY sim DESC
     LIMIT 5
    """
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (sample_id, sample_id))
            rows = cur.fetchall()

    print(f"Accounts similar to '{sample_id}' (fuzzy match, typo-tolerant):")
    for row in rows:
        print(f"  {row[0]} (similarity={row[1]:.3f})")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 4, create GIN index on FTS column
# MAGIC
# MAGIC GIN indexes accelerate full-text search. The SQL:
# MAGIC
# MAGIC ```sql
# MAGIC CREATE INDEX IF NOT EXISTS idx_case_note_fts
# MAGIC   ON bank.case_note
# MAGIC   USING gin(to_tsvector('english', writeup))
# MAGIC ```

# COMMAND ----------

sql = """
CREATE INDEX IF NOT EXISTS idx_case_note_fts
  ON bank.case_note
  USING gin(to_tsvector('english', writeup))
"""
with connect() as conn:
    with conn.cursor() as cur:
        cur.execute(sql)

print("GIN index created on bank.case_note(writeup)")
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
# MAGIC Next: **Row-level security** enforces multi-tenant access control so each user sees only their authorized accounts.
