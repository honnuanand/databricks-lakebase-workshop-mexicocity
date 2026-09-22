# Search, three ways

> ## What you'll learn
>
> **Key takeaways**
>
> - Full-text search ranks results by relevance (e.g. "hydraulic manifold" finds write-ups with both words, ranked higher if they're close). Uses `to_tsvector`, `ts_rank`, and GIN indexes.
> - Fuzzy matching tolerates typos (e.g. a search for part "PT-BEARING-6024" still finds "PT-BEARING-6204" with the digits transposed). Uses `pg_trgm` (trigram similarity) for fast substring matching.
> - Hybrid search blends keyword relevance with semantic similarity when you have embeddings. One query, two ranking signals.
>
> **You'll be able to:** search 20+ years of maintenance write-ups by keyword and typo tolerance, and combine keyword and semantic ranking for smarter search results.
>
> **Time:** about 30 minutes  ·  **Status:** live

## The scenario

Ops needs to search decades of maintenance write-ups. "I remember an engineer's note about hydraulic noise on the nosewheel, maybe 3 years ago. Find it." A naive search for "hydraulic AND nosewheel" across unindexed text is slow. A search that tolerates "hydralic" (the typo) needs fuzzy logic. And if you have embeddings of historical maintenance docs, you could rank by both keyword match and semantic closeness: "show me notes about nosewheel hydraulics, preferring ones semantically similar to my query."

## Why search matters

Search is a feature, not a side effect. Every SaaS product has it. Most teams start with `LIKE '%term%'` (slow, doesn't rank well), then move to Elasticsearch (another system to run, sync, and secure). Postgres can do all three: full-text search, fuzzy matching, and hybrid ranking, natively, indexed, queryable in SQL.

## The wow moment

You write a single query that ranks maintenance logs by full-text relevance, tolerates typos in part numbers, and uses embeddings to find semantically similar notes. The query returns results in milliseconds, ranked by a blend of keyword and semantic signals. All of that is one table and one SQL statement.

## What you'll do

1. Load maintenance write-ups (free-text notes from engineers).
2. Write a full-text search (FTS) query: find notes matching "hydraulic AND nosewheel", ranked by relevance.
3. Add fuzzy matching: find part numbers that are close (typo-tolerant) using trigram similarity.
4. Create a GIN index on the FTS column and measure speedup.
5. (Optional) create a pgvector embedding column and write a hybrid query (keyword + semantic).

Full copy-paste steps are in [`instructions.md`](instructions.md); the exact output and reference numbers are in [`expected.md`](expected.md).

## Prerequisites

Finish [`../../00-setup/`](../../00-setup/) so you have a branch with the factory schema. The `pg_trgm` extension is standard; `pgvector` is optional (only for the hybrid search step).

## Wrapping up

Search is one of those features that seems simple but is surprisingly deep. Full-text search (keyword ranking), fuzzy matching (typo tolerance), and hybrid ranking (blending signals) are all native to Postgres. Once you know these patterns, you stop building search features in the app layer and start building them in SQL. The next journey dives into a different kind of access control: [Row-level security](../pg-rls/), the database itself refuses rows you're not allowed to see.
