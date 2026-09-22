# Operational vectors

> ## What you'll learn
>
> **Key takeaways**
>
> - pgvector stores dense embeddings as vector columns on Postgres tables and queries them with
>   cosine similarity (`<=>`) in the same transaction as your operational data.
> - Finding the best-fit replacement part by similarity (or the closest warehouse by location
>   vector) happens in SQL without leaving the database.
> - pgvector with [Hierarchical Navigable Small Worlds](../../docs/glossary.md) (HNSW) indexing scales to millions of vectors while staying fast (sub-millisecond
>   for typical queries).
> - pgvector is single-transaction, in-process; for large, batch-synced corpora (RAG over docs
>   at scale), Databricks Vector Search is the platform tool. pgvector complements it for
>   operational decisions on live data.
>
> **You'll be able to:** add embedding vectors to the part table, find the best-fit replacement
> part for a failure using similarity search, and verify the closest match in a single SQL query.
>
> **Time:** about 20 minutes  ·  **Status:** live

## The scenario

You're on the factory floor. Machine M-204 has a bearing failure (bearing reference PT-BEARING-6204).
The part is backordered from the regular supplier, but you have a warehouse with 50 compatible
bearings that *feel* similar: same bore size, same load rating, but slightly different outer
diameter. Instead of waiting, you want to find the best-fit replacement from inventory using
*similarity*, not an exact column match.

On a traditional system, the answer is "query a Vector Search service" (network hop, out-of-process,
eventual consistency). On Lakebase with pgvector, the answer is: **embed the part spec, store
the embeddings on the part table, search with `<=>` (cosine similarity) in the same query that
checks inventory**. Single transaction. No cache miss. The database is the vector search engine.

## What pgvector actually is

pgvector is a Postgres extension that adds a `vector` data type and operators:

```sql
ALTER TABLE part ADD COLUMN embedding vector(1536);  -- 1536-dim embedding

UPDATE part SET embedding = ... WHERE ...;  -- populate from a model

SELECT part_id, name, spec, embedding <-> query_vector AS distance
FROM part WHERE embedding <=> query_vector WITHIN 0.3
ORDER BY distance LIMIT 5;  -- find top-5 similar parts within 0.3 cosine distance
```

The `<=>` operator computes cosine similarity. The `<->` operator computes L2 distance. With an
HNSW index, lookups stay fast even with millions of vectors.

## Why pgvector on Lakebase (not Vector Search)

pgvector is for **operational similarity**, in-transaction decisions on live data. Vector Search
is for **large-scale, batch-synced corpora** (RAG over documentation, product catalog search at
scale, where latency is not sub-millisecond critical and data is eventually consistent). They
complement each other:

- **pgvector**: "Is there a similar part in my warehouse right now?" (sub-ms, live)
- **Vector Search**: "Find all documents in the lakehouse that discuss bearing failures" (ms-scale,
  batch-synced)

This journey shows pgvector. For large corpora, use Vector Search.

## The wow moment

The beat worth watching: you query for a replacement bearing. The query joins part (with embeddings),
inventory (warehouse stock), and uses `<=>` to find the closest match in cosine distance. In one
SQL statement, across three tables, with no network hop, you get: "You have 50 PT-BEARING-6205
in Warehouse-2. Similarity to the original: 0.92." Then the MES assistant allocates it
automatically.

## What you'll do

1. Check the part table structure (it's part of the factory schema).
2. Create the pgvector extension and add an `embedding` column to the part table.
3. Seed the embedding column: encode part specs as vectors (using a model or a deterministic hash).
4. Write a similarity search query: find the best-fit replacement part by cosine distance.
5. Verify the search result against expected similar parts.

Full copy-paste steps are in [`instructions.md`](instructions.md); the exact output to check
against is in [`expected.md`](expected.md).

## Prerequisites

Finish [`../../00-setup/`](../../00-setup/) so you have a branch and can connect. This journey
is self-contained; it uses the factory tables but doesn't depend on prior journeys. You'll run
SQL directly (no Python script needed), so you can follow along in a SQL client or the script
examples.

## Wrapping up

You've now seen the full spectrum of operational AI on Lakebase:

- **Agent memory** (sharing state between agents)
- **Agentic work** (reading data, taking action, remembering)
- **Human-in-the-loop** (extracting insights with confidence, learning from corrections)
- **Vectors** (similarity search in a single transaction)

The remaining journeys explore Lakebase's other differentiators: branching, point-in-time restore,
partitioning for time-series, recursive queries for hierarchies, and more. You now have the
foundations to explore them.
