# One query, every type

> ## What you'll learn
>
> **Key takeaways**
>
> - One SELECT query spans relational columns + JSON + vector embeddings + geospatial coordinates on a single table.
> - One execution plan, one snapshot, one transaction, no sync, no consistency gaps.
> - Not four products bolted together with ETL; one engine, one query surface.
>
> **You'll be able to:** build a self-contained unified table with all four data types and run a single query that uses all of them together.
>
> **Time:** about 8 minutes  ·  **Status:** live

## The scenario

You're designing a comprehensive machine-intelligence query. Given a plant and machine type, find machines that:
- Are physically near a reference location (geospatial: "within 5 km").
- Have a similar spec to a reference machine (vector similarity: "similar embeddings").
- Are of a specific model (JSON spec: "type = 'Press'").
- Are in a particular production line (relational: "line = 'Stamping-A'").

A naive architecture would split this across four systems:
- A relational database for line filters.
- A JSON search engine for specs.
- A vector database for embedding similarity.
- A geospatial service for distance queries.

Then you'd stitch the results together with application code, pray they stay consistent, and debug cross-system bugs.

Postgres's answer: one table, all four data types, one query.

## The wow moment

You create a single table with relational, JSON, vector, and geospatial columns. You write one SELECT that filters on all four types in the WHERE and SELECT clauses. One execution plan appears. No sync, no consistency gaps, no four-system orchestration.

## What you'll do

1. Create a demo table with all four data types: relational (machine_id, line), JSON (spec), vector (embedding), and geospatial (location).
2. Write a single SELECT that filters on all four and computes similarity/distance.
3. Show the EXPLAIN plan: one plan, not four sub-queries.
4. Run the query and show the unified result.

Full copy-paste steps are in [`instructions.md`](instructions.md); the exact output is in [`expected.md`](expected.md).

## Prerequisites

Finish [`../../00-setup/`](../../00-setup/) so you have a branch and can connect. Nothing else; this journey is self-contained.

## Wrapping up

This is the point of the entire Postgres track: one query, every data type, one engine. You've learned about
indexes (pg-index), performance tuning (pg-perf), isolation (pg-iso), partitioning (pg-partition), and online serving
(pg-features). They all serve the same principle: one database, many patterns. The final journey [`../pg-cdc/`](../pg-cdc/)
previews logical decoding, the roadmap for change-feeds on Lakebase.
