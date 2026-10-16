# Databricks notebook source
# MAGIC %md
# MAGIC # PG vector - step by step
# MAGIC
# MAGIC A hands-on lab. Run one cell at a time, read what happened, then move on. You will create the pgvector extension, add embeddings to instruments, populate them with deterministic vectors, run a similarity search to find comparable instruments, and create an HNSW index for faster lookups at scale.
# MAGIC
# MAGIC **Before you start:** run `00-setup/setup_databricks` once to create your branch, then run the setup cells below. Needs: the `vector` (pgvector) extension, which this notebook creates. No model endpoint: embeddings are a deterministic hash.

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
# MAGIC ## Setup - initialize

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

# MAGIC %md
# MAGIC ## Step 1 - Check the instrument table
# MAGIC
# MAGIC Query the instrument table to see what we're working with. The SQL:
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
# MAGIC ## Step 2 - Create pgvector extension
# MAGIC
# MAGIC Enable the pgvector extension for embeddings. The SQL:
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
# MAGIC ## Step 3 - Add embedding column to instrument table
# MAGIC
# MAGIC Add a 768-dimensional vector column. The SQL:
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
# MAGIC ## Step 4 - Populate embeddings
# MAGIC
# MAGIC Generate embeddings from instrument names and specs (deterministic hashing for reproducibility). Then update the table. The SQL:
# MAGIC
# MAGIC ```sql
# MAGIC UPDATE bank.instrument SET embedding = CAST('<vector_value>' AS vector) WHERE instrument_id = '<id>';
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
# MAGIC ## Step 5 - Run similarity search
# MAGIC
# MAGIC Find similar instruments using cosine distance. The SQL:
# MAGIC
# MAGIC ```sql
# MAGIC SELECT instrument_id, name, embedding <-> embedding_query AS distance
# MAGIC FROM bank.instrument
# MAGIC WHERE instrument_id != 'INS-QTZL'
# MAGIC ORDER BY embedding <-> embedding_query
# MAGIC LIMIT 5;
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
# MAGIC ## Step 6 - Create HNSW index for scale
# MAGIC
# MAGIC For fast similarity search at scale, create an HNSW index. The SQL:
# MAGIC
# MAGIC ```sql
# MAGIC CREATE INDEX IF NOT EXISTS idx_part_embedding_hnsw
# MAGIC ON bank.instrument USING hnsw (embedding vector_cosine_ops);
# MAGIC ```

# COMMAND ----------

with connect() as conn:
    with conn.cursor() as cur:
        cur.execute(
            f"CREATE INDEX IF NOT EXISTS idx_part_embedding_hnsw "
            f"ON bank.instrument USING hnsw (embedding vector_cosine_ops)"
        )
        print(f"HNSW index created on bank.instrument.embedding")
        print(f"\nIndex optimization: HNSW (Hierarchical Navigable Small World)")
        print(f"  Fast approximate nearest neighbor search")
        print(f"  O(log n) query time for millions of vectors")

# COMMAND ----------

# MAGIC %md
# MAGIC ## What you learned
# MAGIC
# MAGIC You added pgvector to Lakebase: created embeddings from operational data (instrument specs), ran similarity search to rank comparable instruments, and indexed with HNSW for production scale. All on live data, no separate vector database needed. (The workshop embeds with a reproducible hash, so the rankings are not financially meaningful; swap in a real embedding model for semantic neighbours.) The pattern extends across the bank: similar counterparties, similar funds by holdings profile, similar transactions for fraud clustering - operational vectors stored in the same Postgres table as your transaction data.

# COMMAND ----------

# MAGIC %md
# MAGIC ---
# MAGIC **Next**, depending on your track:
# MAGIC
# MAGIC - App developers: <a href="$../pg-search/pg_search_databricks">Full-Text and Fuzzy Search →</a>
# MAGIC - Agent developers: <a href="$../pg-features/pg_features_databricks">Online Feature Serving →</a>
# MAGIC
# MAGIC <a href="$../../START_HERE">← Back to the table of contents</a>
