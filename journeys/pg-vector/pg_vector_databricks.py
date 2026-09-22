# Databricks notebook source
# MAGIC %md
# MAGIC # PG vector - step by step
# MAGIC
# MAGIC A hands-on lab. Run one cell at a time, read what happened, then move on. You will create the pgvector extension, add embeddings to parts, populate them with deterministic vectors, run a similarity search to find replacement parts, and create an HNSW index for faster lookups at scale.
# MAGIC
# MAGIC **Before you start:** finish `00-setup/` so `LB_PROFILE`, `LB_PROJECT`, `LB_BRANCH`, `LB_SCHEMA` are set and the factory is loaded on your branch.

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
# MAGIC ## Step 1 - Check the part table
# MAGIC
# MAGIC Query the part table to see what we're working with. The SQL:
# MAGIC
# MAGIC ```sql
# MAGIC SELECT count(*) FROM factory.part;
# MAGIC SELECT part_id, name FROM factory.part LIMIT 5;
# MAGIC ```

# COMMAND ----------

with connect() as conn:
    with conn.cursor() as cur:
        cur.execute("SELECT count(*) FROM factory.part")
        count = cur.fetchone()[0]
        cur.execute("SELECT part_id, name FROM factory.part LIMIT 5")
        parts = cur.fetchall()

print(f"Checking part table:")
print(f"  Total parts: {count}")
print(f"  Sample parts:")
for p in parts:
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
# MAGIC ## Step 3 - Add embedding column to part table
# MAGIC
# MAGIC Add a 768-dimensional vector column. The SQL:
# MAGIC
# MAGIC ```sql
# MAGIC ALTER TABLE factory.part ADD COLUMN IF NOT EXISTS embedding vector(768);
# MAGIC ```

# COMMAND ----------

with connect() as conn:
    with conn.cursor() as cur:
        cur.execute("ALTER TABLE factory.part ADD COLUMN IF NOT EXISTS embedding vector(768)")
        print(f"Embedding column added to factory.part")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 4 - Populate embeddings
# MAGIC
# MAGIC Generate embeddings from part names and specs (deterministic hashing for reproducibility). Then update the table. The SQL:
# MAGIC
# MAGIC ```sql
# MAGIC UPDATE factory.part SET embedding = CAST('<vector_value>' AS vector) WHERE part_id = '<id>';
# MAGIC ```

# COMMAND ----------

with connect() as conn:
    with conn.cursor() as cur:
        cur.execute("SELECT part_id, name, spec FROM factory.part ORDER BY part_id")
        parts = cur.fetchall()

print(f"Populating {len(parts)} embeddings:")

with connect() as conn:
    with conn.cursor() as cur:
        for part_id, name, spec in parts:
            text_for_embedding = f"{name} {spec}"
            embedding_str = hash_to_embedding(text_for_embedding, 768)
            cur.execute(
                f"UPDATE factory.part SET embedding = CAST(%s AS vector) WHERE part_id = %s",
                [embedding_str, part_id]
            )

print(f"  Updated {len(parts)} parts with embeddings")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 5 - Run similarity search
# MAGIC
# MAGIC Find similar parts using cosine distance. The SQL:
# MAGIC
# MAGIC ```sql
# MAGIC SELECT part_id, name, embedding <-> embedding_query AS distance
# MAGIC FROM factory.part
# MAGIC WHERE part_id != 'P-001'
# MAGIC ORDER BY embedding <-> embedding_query
# MAGIC LIMIT 5;
# MAGIC ```

# COMMAND ----------

with connect() as conn:
    with conn.cursor() as cur:
        cur.execute("SELECT part_id, name FROM factory.part LIMIT 1")
        query_part = cur.fetchone()
        query_part_id = query_part[0]
        query_part_name = query_part[1]

query_embedding = hash_to_embedding(query_part_name, 768)

with connect() as conn:
    with conn.cursor() as cur:
        cur.execute(
            f"SELECT part_id, name, embedding <-> CAST(%s AS vector) AS distance "
            f"FROM factory.part "
            f"WHERE part_id != %s "
            f"ORDER BY embedding <-> CAST(%s AS vector) "
            f"LIMIT 5",
            [query_embedding, query_part_id, query_embedding]
        )
        similar_parts = cur.fetchall()

print(f"Query part: {query_part_id} ({query_part_name})")
print(f"\nMost similar replacement parts:")
for part_id, name, distance in similar_parts:
    print(f"  {part_id}: {name} (distance: {distance:.4f})")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 6 - Create HNSW index for scale
# MAGIC
# MAGIC For fast similarity search at scale, create an HNSW index. The SQL:
# MAGIC
# MAGIC ```sql
# MAGIC CREATE INDEX IF NOT EXISTS idx_part_embedding_hnsw
# MAGIC ON factory.part USING hnsw (embedding vector_cosine_ops);
# MAGIC ```

# COMMAND ----------

with connect() as conn:
    with conn.cursor() as cur:
        cur.execute(
            f"CREATE INDEX IF NOT EXISTS idx_part_embedding_hnsw "
            f"ON factory.part USING hnsw (embedding vector_cosine_ops)"
        )
        print(f"HNSW index created on factory.part.embedding")
        print(f"\nIndex optimization: HNSW (Hierarchical Navigable Small World)")
        print(f"  Fast approximate nearest neighbor search")
        print(f"  O(log n) query time for millions of vectors")

# COMMAND ----------

# MAGIC %md
# MAGIC ## What you learned
# MAGIC
# MAGIC You added pgvector to Lakebase: created embeddings from operational data (part specs), ran similarity search to find replacement parts, and indexed with HNSW for production scale. All on live data, no separate vector database needed. The pattern extends to supply chain (similar suppliers), maintenance (similar failure modes), quality (similar defects) - operational vectors stored in the same Postgres table with your transaction data.
# MAGIC
# MAGIC **Next:** Continue the workshop with more advanced journeys.
