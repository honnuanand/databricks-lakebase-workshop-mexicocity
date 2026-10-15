# Search, three ways

> ## What you'll learn
>
> **Key takeaways**
>
> - [Full-text search](../../docs/glossary.md) (FTS) ranks results by relevance (e.g. "wire fraud" finds case notes with both words, ranked higher if they're close). Uses `to_tsvector`, `ts_rank`, and [GIN](../../docs/glossary.md) indexes.
> - Fuzzy matching tolerates typos (e.g. a search for account "CTA-100240" still finds "CTA-100204" with the digits transposed). Uses [pg_trgm](../../docs/glossary.md) (trigram similarity) for fast substring matching.
> - Hybrid search blends keyword relevance with semantic similarity when you have embeddings. One query, two ranking signals.
>
> **You'll be able to:** search years of fraud and AML case notes by keyword and typo tolerance, and combine keyword and semantic ranking for smarter search results.
>
> **Time:** about 30 minutes  ·  **Status:** live

## The scenario

A fraud and AML analyst needs to search case notes from years of investigations. "I remember a note about a card-not-present charge and account freeze, maybe 2 years back. Find it." A naive search for "card AND compromise" across unindexed text is slow. A search that tolerates "CTA-100204" (a typo in an account ID) needs fuzzy logic. And if you have embeddings of historical case notes, you could rank by both keyword match and semantic closeness: "show me notes about wire fraud, preferring ones semantically similar to this suspected structuring case."

## Why search matters

Search is a feature, not a side effect. Every SaaS product has it. Most teams start with `LIKE '%term%'` (slow, doesn't rank well), then move to Elasticsearch (another system to run, sync, and secure). Postgres can do all three: full-text search, fuzzy matching, and hybrid ranking, natively, indexed, queryable in SQL.

## The wow moment

You write a single query that ranks case notes by full-text relevance, tolerates typos in account and instrument IDs, and uses embeddings to find semantically similar notes. The query returns results in milliseconds, ranked by a blend of keyword and semantic signals. All of that is one table and one SQL statement, with no secondary systems.

## What you'll do

1. Load case notes (free-text analyst write-ups on fraud and AML alerts).
2. Write a [full-text search](../../docs/glossary.md) query: find notes matching "wire OR fraud", ranked by relevance.
3. Add fuzzy matching: find account IDs that are close (typo-tolerant) using [trigram](../../docs/glossary.md) similarity.
4. Create a [GIN](../../docs/glossary.md) index on the FTS column and measure speedup.
5. (Optional) create a [pgvector](../../docs/glossary.md) embedding column and write a hybrid query (keyword + semantic).

Full copy-paste steps are in [`instructions.md`](instructions.md); the exact output and reference numbers are in [`expected.md`](expected.md).

## Prerequisites

Finish [`../../00-setup/`](../../00-setup/) so you have a branch with the bank schema. The [pg_trgm](../../docs/glossary.md) extension is standard; [pgvector](../../docs/glossary.md) is optional (only for the hybrid search step).

## Wrapping up

Search is one of those features that seems simple but is surprisingly deep. Full-text search (keyword ranking), fuzzy matching (typo tolerance), and hybrid ranking (blending signals) are all native to Postgres. Once you know these patterns, you stop building search features in the app layer and start building them in SQL. The next journey dives into a different kind of access control: [Row-level security](../pg-rls/), where the database itself refuses rows you're not allowed to see.
