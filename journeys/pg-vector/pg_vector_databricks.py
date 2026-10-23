# Databricks notebook source
# MAGIC %md-sandbox
# MAGIC <div style="display:flex; align-items:center; gap:10px; padding:8px 16px; background:#F9F7F4; border-bottom:2px solid #E0E0E0; font-family:sans-serif; line-height:1;">
# MAGIC   <span style="display:inline-block; width:12px; height:12px; border-radius:2px; background:#FF3621;"></span>
# MAGIC   <span style="font-weight:bold; color:#0b2026;">Lakebase workshop</span>
# MAGIC   <span style="color:#999;">|</span>
# MAGIC   <span style="color:#5A6F77;">Part 2 · App developers: Journey 2 of 6 · Agent developers: Journey 4 of 5 · Vector Similarity Search</span>
# MAGIC </div>

# COMMAND ----------

# MAGIC %md
# MAGIC # Vector Similarity Search
# MAGIC #### Duration: 20 minutes
# MAGIC
# MAGIC *Journey 2 of 6 for App developers, 4 of 5 for Agent developers. JSONB searched for exact matches; this journey ranks rows by how similar they are.*
# MAGIC
# MAGIC ## Overview
# MAGIC
# MAGIC A portfolio manager holds Quetzal Tecnologia (`INS-QTZL`) and wants the instruments most like it, to
# MAGIC find a substitute or a hedge. "Most like it" isn't one column you can filter on; it's a judgement over
# MAGIC the whole profile. That's a similarity question.
# MAGIC
# MAGIC The usual answer is a separate vector search service. With the **pgvector** extension, Postgres stores
# MAGIC an embedding (a list of numbers) on each row and ranks rows by distance in plain SQL, next to your
# MAGIC operational data. **An honesty note:** this journey builds its embeddings from a deterministic hash of
# MAGIC each instrument's text, not a real embedding model, so the ranking shows the mechanism, not real
# MAGIC financial similarity.
# MAGIC
# MAGIC ## Learning objectives
# MAGIC
# MAGIC By the end of this lab, you will be able to:
# MAGIC
# MAGIC 1. **Add a vector column** to a table with the pgvector extension.
# MAGIC 2. **Store an embedding on each row** next to its operational data.
# MAGIC 3. **Rank rows by similarity** to a reference row with one SQL query.
# MAGIC 4. **Index the vectors** with HNSW so the search stays fast at scale.

# COMMAND ----------

# MAGIC %md
# MAGIC ## Key concepts
# MAGIC
# MAGIC - **Embedding:** a list of numbers that represents an item. Items with similar meaning get nearby embeddings, when a real model makes them.
# MAGIC - **pgvector:** a Postgres extension that adds the `vector` type and distance operators: `<->` (straight-line distance, used in this notebook) and `<=>` (cosine distance).
# MAGIC - **Distance:** how far apart two embeddings are. Smaller means more similar.
# MAGIC - **HNSW index:** Hierarchical Navigable Small World: an approximate nearest-neighbour index that keeps vector search fast on millions of rows.
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
# MAGIC     Needs: the <code>vector</code> (pgvector) extension, which this notebook creates. No model endpoint: the embeddings are a deterministic hash.
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
# MAGIC ### A2. Load the helper and the embedding function
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
# MAGIC
# MAGIC This cell also defines `hash_to_embedding()`, which turns text into a 768-number vector by hashing it, the stand-in for a real embedding model.

# COMMAND ----------

import os, sys, hashlib, struct
sys.path.insert(0, os.path.join(os.getcwd(), "..", "..", "common", "scripts"))
from lakebase import connect, run_sql

def hash_to_embedding(text: str, dim: int = 768) -> str:
    """Deterministic hash-based embedding for reproducibility."""
    h = hashlib.sha256(text.encode()).digest()
    values = []
    for i in range(dim):
        byte_idx = (i * 2) % len(h)
        val = (struct.unpack("B", h[byte_idx:byte_idx+1])[0] / 255.0) * 2 - 1
        values.append(f"{val:.4f}")
    return "[" + ",".join(values) + "]"

print("pgvector initialized")

# COMMAND ----------

# MAGIC %md-sandbox
# MAGIC **Expected result:** `pgvector initialized`
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
# MAGIC ## B. Prepare the table

# COMMAND ----------

# MAGIC %md
# MAGIC ### B1. Look at the instruments
# MAGIC
# MAGIC Five instruments: two tech equities, a Mexican government bond, an equity sleeve, and peso cash.
# MAGIC The SQL:
# MAGIC
# MAGIC ```sql
# MAGIC SELECT count(*) FROM bank.instrument;
# MAGIC SELECT instrument_id, name FROM bank.instrument LIMIT 5;
# MAGIC ```

# COMMAND ----------

with connect() as conn:
    with conn.cursor() as cur:
        cur.execute("SELECT count(*) FROM bank.instrument")
        count = cur.fetchone()[0]
        cur.execute("SELECT instrument_id, name FROM bank.instrument LIMIT 5")
        instruments = cur.fetchall()

print(f"Checking instrument table:")
print(f"  Total instruments: {count}")
print(f"  Sample instruments:")
for p in instruments:
    print(f"    - {p[0]}: {p[1]}")

# COMMAND ----------

# MAGIC %md
# MAGIC **Expected result:** ```
# MAGIC Checking instrument table:
# MAGIC   Total instruments: 5
# MAGIC   Sample instruments:
# MAGIC     - INS-CASH-MXN: Mexican Peso Cash
# MAGIC     - INS-SLEEVE-EQ: Equity Sleeve
# MAGIC     - INS-QTZL: Quetzal Tecnologia
# MAGIC     - INS-MBONO-10Y: Bono M 10Y (Mexico)
# MAGIC     - INS-ZAFR: Zafiro Software
# MAGIC ```

# COMMAND ----------

# MAGIC %md
# MAGIC ### B2. Enable pgvector
# MAGIC
# MAGIC ```sql
# MAGIC CREATE EXTENSION IF NOT EXISTS vector;
# MAGIC ```

# COMMAND ----------

with connect() as conn:
    with conn.cursor() as cur:
        cur.execute("CREATE EXTENSION IF NOT EXISTS vector")
        print(f"pgvector extension created")

# COMMAND ----------

# MAGIC %md
# MAGIC **Expected result:** `pgvector extension created`
# MAGIC
# MAGIC **What this proves:** vector search is a Postgres extension you switch on, not a separate service.

# COMMAND ----------

# MAGIC %md
# MAGIC ### B3. Add the embedding column
# MAGIC
# MAGIC ```sql
# MAGIC ALTER TABLE bank.instrument ADD COLUMN IF NOT EXISTS embedding vector(768);
# MAGIC ```

# COMMAND ----------

with connect() as conn:
    with conn.cursor() as cur:
        cur.execute("ALTER TABLE bank.instrument ADD COLUMN IF NOT EXISTS embedding vector(768)")
        print(f"Embedding column added to bank.instrument")

# COMMAND ----------

# MAGIC %md
# MAGIC **Expected result:** `Embedding column added to bank.instrument`

# COMMAND ----------

# MAGIC %md
# MAGIC ### B4. Store an embedding on each row
# MAGIC
# MAGIC The cell builds a text for each instrument from its name, kind and spec, hashes it into a vector, and
# MAGIC writes it to the `embedding` column. The SQL it runs for each row:
# MAGIC
# MAGIC ```sql
# MAGIC UPDATE bank.instrument SET embedding = '<768 numbers>'::vector WHERE instrument_id = '<id>';
# MAGIC ```

# COMMAND ----------

with connect() as conn:
    with conn.cursor() as cur:
        cur.execute("SELECT instrument_id, name, spec FROM bank.instrument ORDER BY instrument_id")
        instruments = cur.fetchall()

print(f"Populating {len(instruments)} embeddings:")

with connect() as conn:
    with conn.cursor() as cur:
        for instrument_id, name, spec in instruments:
            text_for_embedding = f"{name} {spec}"
            embedding_str = hash_to_embedding(text_for_embedding, 768)
            cur.execute(
                f"UPDATE bank.instrument SET embedding = CAST(%s AS vector) WHERE instrument_id = %s",
                [embedding_str, instrument_id]
            )

print(f"  Updated {len(instruments)} instruments with embeddings")

# COMMAND ----------

# MAGIC %md
# MAGIC **Expected result:** ```
# MAGIC Populating 5 embeddings:
# MAGIC   Updated 5 instruments with embeddings
# MAGIC ```
# MAGIC
# MAGIC **What this proves:** the embedding lives on the same row as the instrument's operational data.

# COMMAND ----------

# MAGIC %md
# MAGIC ## C. Search by similarity

# COMMAND ----------

# MAGIC %md
# MAGIC ### C1. Find the instruments most like Quetzal Tecnologia
# MAGIC
# MAGIC Take `INS-QTZL`'s stored embedding and rank the other instruments by distance to it (`<->`, smaller is
# MAGIC more similar). The SQL:
# MAGIC
# MAGIC ```sql
# MAGIC SELECT instrument_id, name, embedding <-> (SELECT embedding FROM bank.instrument WHERE instrument_id = 'INS-QTZL') AS distance
# MAGIC   FROM bank.instrument
# MAGIC  WHERE instrument_id != 'INS-QTZL'
# MAGIC  ORDER BY distance
# MAGIC  LIMIT 5;
# MAGIC ```

# COMMAND ----------

with connect() as conn:
    with conn.cursor() as cur:
        # the reference instrument and its stored embedding (same as pg_vector.py)
        cur.execute("SELECT instrument_id, name, embedding::text FROM bank.instrument WHERE instrument_id = %s",
                    ["INS-QTZL"])
        query_part = cur.fetchone()
        query_part_id = query_part[0]
        query_part_name = query_part[1]

query_embedding = query_part[2]

with connect() as conn:
    with conn.cursor() as cur:
        cur.execute(
            f"SELECT instrument_id, name, embedding <-> CAST(%s AS vector) AS distance "
            f"FROM bank.instrument "
            f"WHERE instrument_id != %s "
            f"ORDER BY embedding <-> CAST(%s AS vector) "
            f"LIMIT 5",
            [query_embedding, query_part_id, query_embedding]
        )
        similar_parts = cur.fetchall()

print(f"Query instrument: {query_part_id} ({query_part_name})")
print(f"\nMost similar comparable instruments:")
for instrument_id, name, distance in similar_parts:
    print(f"  {instrument_id}: {name} (distance: {distance:.4f})")

# COMMAND ----------

# MAGIC %md
# MAGIC **Expected result:** from a test run:
# MAGIC
# MAGIC ```
# MAGIC Query instrument: INS-QTZL (Quetzal Tecnologia)
# MAGIC
# MAGIC Most similar comparable instruments:
# MAGIC   INS-CASH-MXN: Mexican Peso Cash (distance: 23.3074)
# MAGIC   INS-MBONO-10Y: Bono M 10Y (Mexico) (distance: 23.6040)
# MAGIC   INS-SLEEVE-EQ: Equity Sleeve (distance: 23.9502)
# MAGIC   INS-ZAFR: Zafiro Software (distance: 23.9834)
# MAGIC ```
# MAGIC
# MAGIC The same hash gives the same numbers every run.
# MAGIC
# MAGIC **What this proves:** one SQL query ranks rows by similarity, in the same table as the data. **It doesn't prove the ranking means anything:** with hash embeddings, Zafiro Software (the other tech equity) comes last here. A real embedding model would put it first.

# COMMAND ----------

# MAGIC %md-sandbox
# MAGIC ##### EXPAND FOR ADDITIONAL NOTES
# MAGIC
# MAGIC <details>
# MAGIC <summary><strong>Making the similarity real</strong></summary>
# MAGIC
# MAGIC Swap `hash_to_embedding()` for a call to an embedding model, for example a Databricks Foundation Model
# MAGIC endpoint, and store its output instead. The table, the column, the query and the index stay exactly the
# MAGIC same; only the numbers change, and the ranking starts to mean something.
# MAGIC
# MAGIC pgvector suits operational lookups on live rows, like this one. For large document collections that
# MAGIC are synced in batches (search over thousands of PDFs, for example), Databricks Vector Search is
# MAGIC usually the better tool.
# MAGIC
# MAGIC </details>

# COMMAND ----------

# MAGIC %md
# MAGIC ### C2. Index the vectors
# MAGIC
# MAGIC On five rows the search reads every row anyway. On millions, an HNSW index finds the nearest
# MAGIC neighbours without scanning everything. The SQL:
# MAGIC
# MAGIC ```sql
# MAGIC CREATE INDEX IF NOT EXISTS idx_instrument_embedding_hnsw
# MAGIC   ON bank.instrument USING hnsw (embedding vector_l2_ops);
# MAGIC ```

# COMMAND ----------

with connect() as conn:
    with conn.cursor() as cur:
        cur.execute(
            f"CREATE INDEX IF NOT EXISTS idx_instrument_embedding_hnsw "
            f"ON bank.instrument USING hnsw (embedding vector_l2_ops)"
        )
        print(f"HNSW index created on bank.instrument.embedding")
        print(f"\nIndex optimization: HNSW (Hierarchical Navigable Small World)")
        print(f"  Fast approximate nearest neighbor search")
        print(f"  O(log n) query time for millions of vectors")

# COMMAND ----------

# MAGIC %md-sandbox
# MAGIC **Expected result:** ```
# MAGIC HNSW index created on bank.instrument.embedding
# MAGIC
# MAGIC Index optimization: HNSW (Hierarchical Navigable Small World)
# MAGIC   Fast approximate nearest neighbor search
# MAGIC   O(log n) query time for millions of vectors
# MAGIC ```
# MAGIC
# MAGIC `vector_l2_ops` matches the `<->` distance used in C1; an index only helps queries that use its operator.
# MAGIC
# MAGIC **What this proves:** vector columns are indexed like any other column, inside the same database.

# COMMAND ----------

# MAGIC %md-sandbox
# MAGIC ##### Check your understanding
# MAGIC
# MAGIC <details>
# MAGIC <summary><strong>1. Where is each instrument's embedding stored?</strong></summary>
# MAGIC
# MAGIC In the `embedding` column of `bank.instrument`, on the same row as the instrument.
# MAGIC
# MAGIC </details>
# MAGIC
# MAGIC <details>
# MAGIC <summary><strong>2. Why did Zafiro Software rank last, even though it's the other tech equity?</strong></summary>
# MAGIC
# MAGIC The embeddings are a hash of the text, not a model's understanding, so distances are arbitrary. A real embedding model would fix that without changing the query.
# MAGIC
# MAGIC </details>
# MAGIC
# MAGIC <details>
# MAGIC <summary><strong>3. What does `<->` return?</strong></summary>
# MAGIC
# MAGIC The distance between two vectors. Smaller means more similar.
# MAGIC
# MAGIC </details>

# COMMAND ----------

# MAGIC %md
# MAGIC ## D. Conclusion
# MAGIC
# MAGIC In this lab you added vectors to a table, stored one per row, ranked rows by similarity, and indexed
# MAGIC the vectors. Key takeaways:
# MAGIC
# MAGIC 1. **pgvector makes Postgres a vector store:** a column type, distance operators, and indexes.
# MAGIC 2. **Embeddings live next to operational data,** so a similarity search can also filter on status,
# MAGIC    owner, or anything else in one query.
# MAGIC 3. **HNSW keeps it fast** as tables grow.
# MAGIC 4. **The ranking is only as good as the embeddings:** here a hash, in production a real model.

# COMMAND ----------

# MAGIC %md
# MAGIC ---
# MAGIC **Next**, depending on your track:
# MAGIC
# MAGIC - App developers: <a href="$../pg-search/pg_search_databricks">Full-Text and Fuzzy Search →</a>
# MAGIC - Agent developers: <a href="$../pg-features/pg_features_databricks">Online Feature Serving →</a>
# MAGIC
# MAGIC <a href="$../../START_HERE">← Back to the table of contents</a>
