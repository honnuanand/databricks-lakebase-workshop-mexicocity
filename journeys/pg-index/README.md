# One engine, every index

> ## What you'll learn
>
> **Key takeaways**
>
> - One Postgres table can carry every data type: relational columns, JSON, time-series, geography, and vectors, each serving a different query pattern.
> - Six index types ([btree](../../docs/glossary.md), [hash](../../docs/glossary.md), [GIN](../../docs/glossary.md), [BRIN](../../docs/glossary.md), [GiST](../../docs/glossary.md), [HNSW](../../docs/glossary.md)) each optimize a different query shape, and the cost-based planner chooses the right one on every query.
> - The proof: create each index and watch EXPLAIN show the planner picks it.
>
> **You'll be able to:** build a self-contained demo table with six data types and six index access methods, and prove via EXPLAIN that the planner uses each.
>
> **Time:** about 12 minutes  ·  **Status:** live

## The scenario

You're designing the account profile schema for a retail bank. Every account generates data: ID, merchant category code, account specifications (JSON), open date, branch location, and risk-embedding for fraud prevention. That's six completely different data types, each with its own query pattern:

- Lookup an account by ID (relational equality) → [**btree**](../../docs/glossary.md).
- Filter by merchant category (integer equality) → [**hash**](../../docs/glossary.md).
- Search account specs for a specific product tier → [**GIN**](../../docs/glossary.md) (JSON containment).
- Range queries on account age (which accounts opened in Q2?) → [**BRIN**](../../docs/glossary.md) (time-series).
- Find accounts near a branch location → [**GiST**](../../docs/glossary.md) (geospatial distance).
- Find similar accounts by risk profile embedding → [**HNSW**](../../docs/glossary.md) (vector similarity).

A naive design creates separate systems: a relational database, a JSON store, a time-series database, a geospatial service, and a vector store. Postgres is one database holding all six, each with its native index, one query planner arbitrating them all.

## The wow moment

You create a 60k-row table with all six types. For each type, you create the matching index. Then you run EXPLAIN on six different queries, one for each type, and the planner picks the right index every single time. One table, one execution plan for each, one engine. Not six products bolted together with ETL pipelines.

## What you'll do

1. Create a demo table with account data: relational (account_id, mcc), JSON (specs), timestamps, geography (branch location), and vectors (risk embedding).
2. Create six indexes: [btree](../../docs/glossary.md), [hash](../../docs/glossary.md), [GIN](../../docs/glossary.md), [BRIN](../../docs/glossary.md), [GiST](../../docs/glossary.md), [HNSW](../../docs/glossary.md).
3. Run EXPLAIN on six different query shapes and show each uses its index.

Full copy-paste steps are in [`instructions.md`](instructions.md); the exact output to check against is in [`expected.md`](expected.md).

## Prerequisites

Finish [`../../00-setup/`](../../00-setup/) so you have a branch and can connect. Nothing else; this journey is self-contained and doesn't depend on any other journey.

## Wrapping up

This is the foundation of why Postgres scales: one engine, many data types, many indexes, one planner. The next journey
[`../pg-iso/`](../pg-iso/) stays on the engine's concurrency guarantees, what happens when two writers hit the same row.
