# Operational vectors

> ## What you'll learn
>
> **Key takeaways**
>
> - pgvector stores dense embeddings as vector columns on Postgres tables and queries them with
>   cosine similarity (`<=>`) in the same transaction as your operational data.
> - Finding the best-fit comparable instrument by similarity (or the closest warehouse by location
>   vector) happens in SQL without leaving the database.
> - pgvector with [Hierarchical Navigable Small Worlds](../../docs/glossary.md) (HNSW) indexing scales to millions of vectors while staying fast (sub-millisecond
>   for typical queries).
> - pgvector is single-transaction, in-process; for large, batch-synced corpora (RAG over docs
>   at scale), Databricks Vector Search is the platform tool. pgvector complements it for
>   operational decisions on live data.
>
> **You'll be able to:** add embedding vectors to the instrument table, find the instruments most
> similar to a given holding using similarity search, and verify the closest matches in a single SQL query.
>
> **Time:** about 20 minutes  ·  **Status:** live

## The scenario

A portfolio manager holds INS-AAPL (Apple equity) and wants the instruments most *similar* to it,
to find a substitute or a hedge if they need to reduce that position. "Similar" is not any one
column: it is a judgement over the instrument's whole profile, asset kind, sector, risk, how it
behaves. That is a similarity question, not an exact filter.

On a traditional system, the answer is "query a separate vector search service" (network hop,
out-of-process, eventually consistent). On Lakebase with pgvector, the answer is: **embed the
instrument's profile, store the embedding on the instrument row, and search with `<=>` (cosine
similarity) in the same transaction as your operational data**. No cache miss, no second system.
The database is the vector search engine.

## What pgvector actually is

pgvector is a Postgres extension that adds a `vector` data type and operators:

```sql
ALTER TABLE instrument ADD COLUMN embedding vector(1536);  -- 1536-dim embedding

UPDATE instrument SET embedding = ... WHERE ...;  -- populate from a model

SELECT instrument_id, name, spec, embedding <-> query_vector AS distance
FROM instrument WHERE embedding <=> query_vector WITHIN 0.3
ORDER BY distance LIMIT 5;  -- find top-5 similar instruments within 0.3 cosine distance
```

The `<=>` operator computes cosine similarity. The `<->` operator computes L2 distance. With an
HNSW index, lookups stay fast even with millions of vectors.

## Why pgvector on Lakebase (not Vector Search)

pgvector is for **operational similarity**, in-transaction decisions on live data. Vector Search
is for **large-scale, batch-synced corpora** (RAG over documentation, product catalog search at
scale, where latency is not sub-millisecond critical and data is eventually consistent). They
complement each other:

- **pgvector**: "Which instruments are most similar to the one I hold, right now?" (sub-ms, live)
- **Vector Search**: "Find all research documents in the lakehouse that discuss this sector"
  (ms-scale, batch-synced)

This journey shows pgvector. For large corpora, use Vector Search.

## The wow moment

The beat worth watching: you ask for the instruments most similar to INS-AAPL. The query reads the
instrument embeddings and uses `<=>` to rank the rest by cosine similarity, in one SQL statement,
in the same database that holds your positions and trades, with no network hop. The nearest
comparable instruments come back ranked, ready to inform a substitution or hedge.

## What you'll do

1. Check the instrument table structure (the `instrument` table of the bank schema).
2. Create the pgvector extension and add an `embedding` column to the instrument table.
3. Seed the embedding column: encode instrument specs as vectors (using a model or a deterministic hash).
4. Write a similarity search query: find the best-fit comparable instrument by cosine distance.
5. Verify the search result against expected similar instruments.

Full copy-paste steps are in [`instructions.md`](instructions.md); the exact output to check
against is in [`expected.md`](expected.md).

## Prerequisites

Finish [`../../00-setup/`](../../00-setup/) so you have a branch and can connect. This journey
is self-contained; it uses the bank tables but doesn't depend on prior journeys. You'll run
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
