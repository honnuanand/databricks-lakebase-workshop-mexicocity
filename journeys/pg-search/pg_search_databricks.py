# Databricks notebook source
# MAGIC %md-sandbox
# MAGIC <div style="display:flex; align-items:center; gap:10px; padding:8px 16px; background:#F9F7F4; border-bottom:2px solid #E0E0E0; font-family:sans-serif; line-height:1;">
# MAGIC   <span style="display:inline-block; width:12px; height:12px; border-radius:2px; background:#FF3621;"></span>
# MAGIC   <span style="font-weight:bold; color:#0b2026;">Lakebase workshop</span>
# MAGIC   <span style="color:#999;">|</span>
# MAGIC   <span style="color:#5A6F77;">Part 2 · App developers · Journey 3 of 6 · Full-Text and Fuzzy Search</span>
# MAGIC </div>

# COMMAND ----------

# MAGIC %md
# MAGIC # Full-Text and Fuzzy Search
# MAGIC #### Duration: 30 minutes
# MAGIC
# MAGIC *Journey 3 of 6 in the App developers track. Vectors ranked rows by similarity; this journey searches text by words and by spelling.*
# MAGIC
# MAGIC ## Overview
# MAGIC
# MAGIC A fraud and AML analyst needs to search years of case notes. "I remember a note about a SPEI transfer
# MAGIC and an account takeover" should find it, ranked by relevance, and a typo in an account id shouldn't
# MAGIC stop the search.
# MAGIC
# MAGIC Postgres has both built in: **full-text search**, which matches words regardless of form and ranks the
# MAGIC results, and **trigram matching** (`pg_trgm`), which finds strings that are spelled similarly. In this
# MAGIC lab you run both on the bank's case notes and add the index that keeps full-text search fast.
# MAGIC
# MAGIC ## Learning objectives
# MAGIC
# MAGIC By the end of this lab, you will be able to:
# MAGIC
# MAGIC 1. **Search text by words** with full-text search, and rank the matches.
# MAGIC 2. **Find near-matches** for a misspelled id with trigram similarity.
# MAGIC 3. **Index text for search** with a GIN index on `to_tsvector`.
# MAGIC 4. **Explain hybrid search:** combining word matches with vector similarity.

# COMMAND ----------

# MAGIC %md
# MAGIC ## Key concepts
# MAGIC
# MAGIC - **Full-text search:** Postgres turns text into a list of normalized words (a `tsvector`) and matches it against a query (a `tsquery`). "transfers" and "transfer" match, and `ts_rank` scores relevance.
# MAGIC - **Trigram similarity:** the `pg_trgm` extension splits strings into three-character pieces and scores how many two strings share (0 to 1). Good for typos in names and ids.
# MAGIC - **GIN index on text:** indexes each word in the `tsvector`, so full-text searches don't read every row.
# MAGIC - **Hybrid search:** blending a full-text rank with a vector similarity score. This journey explains it; it doesn't run it.
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
# MAGIC     Attach this notebook to <strong>serverless</strong> compute.
# MAGIC     Needs: the <code>pg_trgm</code> extension, which this notebook creates.
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
# MAGIC This loads `run_sql()` and `connect()` from `common/scripts/`. `run_sql()` opens a connection to your
# MAGIC branch, runs one SQL statement, and returns any rows; `connect()` gives you the connection itself.
# MAGIC
# MAGIC Under the hood, both ask the Lakebase API for your branch's host name, get a login token from your
# MAGIC Databricks identity (valid for about an hour), and open a standard Postgres connection with `psycopg`,
# MAGIC a Postgres driver for Python.
# MAGIC
# MAGIC In the steps below, the SQL block in each step is the statement that runs on your branch. The Python
# MAGIC cell under it only sends that statement and prints the result.

# COMMAND ----------

import os, sys
sys.path.insert(0, os.path.join(os.getcwd(), "..", "..", "common", "scripts"))
from lakebase import connect, run_sql

SCHEMA = os.environ.get("LB_SCHEMA", "bank")
print("connected; schema:", SCHEMA)

# COMMAND ----------

# MAGIC %md-sandbox
# MAGIC **Expected result:** `connected; schema: bank`
# MAGIC
# MAGIC <div style="border-left:4px solid #FF9800; background:#FFF3E0; padding:12px 16px; border-radius:4px; margin:12px 0; font-family:sans-serif;">
# MAGIC   <strong style="display:block; color:#E65100; margin-bottom:6px;">Troubleshooting</strong>
# MAGIC   <div style="color:#333;">
# MAGIC     <ul style="margin:0; padding-left:20px;">
# MAGIC       <li><code>Missing required env var LB_PROJECT</code> or <code>KeyError: 'LB_PROJECT'</code>: the A1 cells didn't run in this session. Run the three A1 cells, then this one.</li>
# MAGIC     </ul>
# MAGIC   </div>
# MAGIC </div>

# COMMAND ----------

# MAGIC %md
# MAGIC ## B. Search by words

# COMMAND ----------

# MAGIC %md
# MAGIC ### B1. Look at the case notes
# MAGIC
# MAGIC Free-text notes analysts wrote on alerts. The SQL:
# MAGIC
# MAGIC ```sql
# MAGIC SELECT note_id, account_id, writeup FROM bank.case_note LIMIT 3;
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
# MAGIC **Expected result:** ```
# MAGIC Sample case notes:
# MAGIC   note_id=1, account_id=CTA-100240
# MAGIC     'Cardholder reports three card-not-present charges to a forei...'
# MAGIC   note_id=2, account_id=CTA-300421
# MAGIC     'Large outbound SPEI transfer to a new beneficiary, just unde...'
# MAGIC   note_id=3, account_id=CTA-200311
# MAGIC     'Customer disputed a recurring subscription charge. Confirmed...'
# MAGIC ```

# COMMAND ----------

# MAGIC %md
# MAGIC ### B2. Full-text search, ranked
# MAGIC
# MAGIC Find notes that mention "SPEI" or "takeover", most relevant first. The SQL:
# MAGIC
# MAGIC ```sql
# MAGIC SELECT note_id, account_id,
# MAGIC        ts_rank(to_tsvector('english', writeup), to_tsquery('english', 'spei | takeover')) AS rank
# MAGIC   FROM bank.case_note
# MAGIC  WHERE to_tsvector('english', writeup) @@ to_tsquery('english', 'spei | takeover')
# MAGIC  ORDER BY rank DESC;
# MAGIC ```

# COMMAND ----------

sql = """
SELECT note_id, account_id,
       ts_rank(to_tsvector('english', writeup),
               to_tsquery('english', 'spei | takeover')) as rank
  FROM bank.case_note
 WHERE to_tsvector('english', writeup) @@ to_tsquery('english', 'spei | takeover')
 ORDER BY rank DESC
 LIMIT 5
"""
rows = run_sql(sql)
print("Case notes matching 'SPEI OR takeover', ranked by relevance:")
for row in rows:
    print(f"  note_id={row[0]}, account_id={row[1]}, rank={row[2]}")

# COMMAND ----------

# MAGIC %md
# MAGIC **Expected result:** ```
# MAGIC Case notes matching 'SPEI OR takeover', ranked by relevance:
# MAGIC   note_id=1, account_id=CTA-100240, rank=0.06079271
# MAGIC   note_id=2, account_id=CTA-300421, rank=0.030396355
# MAGIC ```
# MAGIC
# MAGIC **What this proves:** the search matches words, not exact strings, and ranks by relevance: note 1 mentions both words, so it ranks above note 2, which mentions only "SPEI".

# COMMAND ----------

# MAGIC %md
# MAGIC ## C. Search by spelling

# COMMAND ----------

# MAGIC %md
# MAGIC ### C1. Fuzzy-match an account id
# MAGIC
# MAGIC `pg_trgm` scores how similar two strings are by their three-character pieces. The cell enables it,
# MAGIC then finds the accounts most similar to the first account it reads, `CTA-100234`. The SQL:
# MAGIC
# MAGIC ```sql
# MAGIC CREATE EXTENSION IF NOT EXISTS pg_trgm;
# MAGIC SELECT account_id, similarity(account_id, 'CTA-100234') AS sim
# MAGIC   FROM bank.account
# MAGIC  WHERE account_id % 'CTA-100234'      -- similar enough (pg_trgm's threshold, 0.3 by default)
# MAGIC  ORDER BY sim DESC LIMIT 5;
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
# MAGIC **Expected result:** ```
# MAGIC Accounts similar to 'CTA-100234' (fuzzy match, typo-tolerant):
# MAGIC   CTA-100234 (similarity=1.000)
# MAGIC   CTA-100235 (similarity=0.692)
# MAGIC   CTA-100240 (similarity=0.571)
# MAGIC   CTA-100241 (similarity=0.571)
# MAGIC ```
# MAGIC
# MAGIC **What this proves:** near-matches are found and ranked, so a mistyped id like `CTA-100243` would still bring up the right candidates.

# COMMAND ----------

# MAGIC %md
# MAGIC ### C2. Index the text
# MAGIC
# MAGIC A GIN index on the `tsvector` makes full-text search use the index instead of reading every note.
# MAGIC The SQL:
# MAGIC
# MAGIC ```sql
# MAGIC CREATE INDEX IF NOT EXISTS idx_case_note_fts ON bank.case_note USING gin (to_tsvector('english', writeup));
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
# MAGIC **Expected result:** ```
# MAGIC GIN index created on bank.case_note(writeup)
# MAGIC (Subsequent FTS queries will use the index)
# MAGIC ```
# MAGIC
# MAGIC **What this proves:** text search is indexed inside the database; no separate search engine is needed.

# COMMAND ----------

# MAGIC %md
# MAGIC ## D. Hybrid search (explained)

# COMMAND ----------

# MAGIC %md
# MAGIC ### D1. What hybrid search adds
# MAGIC
# MAGIC Full-text search finds the words you typed; vector search finds notes that mean something similar.
# MAGIC Hybrid search blends both scores. This cell only explains it: it would need an embedding on each case
# MAGIC note (see *Vector Similarity Search*).

# COMMAND ----------

print("Hybrid search (keyword + semantic) requires pgvector for embeddings.")
print("You have now mastered FTS (full-text search) and fuzzy matching (pg_trgm).")
print("Those two approaches cover most production search use cases.")

# COMMAND ----------

# MAGIC %md
# MAGIC **Expected result:** ```
# MAGIC Hybrid search (keyword + semantic) requires pgvector for embeddings.
# MAGIC You have now mastered FTS (full-text search) and fuzzy matching (pg_trgm).
# MAGIC Those two approaches cover most production search use cases.
# MAGIC ```

# COMMAND ----------

# MAGIC %md-sandbox
# MAGIC ##### EXPAND FOR ADDITIONAL NOTES
# MAGIC
# MAGIC <details>
# MAGIC <summary><strong>How a hybrid query would look</strong></summary>
# MAGIC
# MAGIC Give each case note an `embedding` column, as in *Vector Similarity Search*, then rank by a weighted
# MAGIC blend of the full-text rank and the vector similarity, for example
# MAGIC `0.6 * ts_rank(...) + 0.4 * (1 - (embedding <=> :query_embedding))`. Tune the weights on real questions
# MAGIC from your analysts.
# MAGIC
# MAGIC </details>

# COMMAND ----------

# MAGIC %md-sandbox
# MAGIC ##### Check your understanding
# MAGIC
# MAGIC <details>
# MAGIC <summary><strong>1. Why did note 1 rank above note 2?</strong></summary>
# MAGIC
# MAGIC It matches both search words, "SPEI" and "takeover"; note 2 matches only "SPEI".
# MAGIC
# MAGIC </details>
# MAGIC
# MAGIC <details>
# MAGIC <summary><strong>2. When would you use trigram similarity instead of full-text search?</strong></summary>
# MAGIC
# MAGIC For short strings where typos matter, like names and ids. Full-text search is for words in longer text.
# MAGIC
# MAGIC </details>
# MAGIC
# MAGIC <details>
# MAGIC <summary><strong>3. What does hybrid search need that this journey didn't create?</strong></summary>
# MAGIC
# MAGIC An embedding on each case note, so a vector similarity score can be blended with the text rank.
# MAGIC
# MAGIC </details>

# COMMAND ----------

# MAGIC %md
# MAGIC ## E. Conclusion
# MAGIC
# MAGIC In this lab you searched case notes by words, found near-matches by spelling, and indexed the text.
# MAGIC Key takeaways:
# MAGIC
# MAGIC 1. **Full-text search** matches words regardless of form and ranks by relevance.
# MAGIC 2. **Trigram similarity** catches typos in short strings like ids and names.
# MAGIC 3. **GIN indexes** keep both fast, inside the same database.
# MAGIC 4. **Hybrid search** blends text rank with vector similarity when you add embeddings.

# COMMAND ----------

# MAGIC %md
# MAGIC ---
# MAGIC **Next in the App developers track:** <a href="$../pg-booking/pg_booking_databricks">Preventing Overlapping Schedules →</a>
# MAGIC
# MAGIC <a href="$../../START_HERE">← Back to the table of contents</a>
