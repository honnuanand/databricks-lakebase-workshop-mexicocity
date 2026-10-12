# JSON documents

> ## What you'll learn
>
> **Key takeaways**
>
> - [JSONB](../../docs/glossary.md) stores flexible, schema-free documents natively in Postgres. No schema migration; no separate document store.
> - Queries use simple operators: `@>` (contains), `#>>` (extract path), `?` (key exists). They run at database speed, indexed by [GIN](../../docs/glossary.md) (Generalized Inverted Index).
> - The numbers that matter: a compliance query over fund and instrument spec sheets (some have a sector, others don't; some specify a tenor, others don't) runs in under 50 milliseconds with a GIN index.
>
> **You'll be able to:** store flexible instrument and fund specification sheets as JSONB, query them to find compliant instruments and funds without schema changes, and index them for fast searches.
>
> **Time:** about 20 minutes  ·  **Status:** live

## The scenario

At the bank, every instrument has a specification sheet, and so does every fund. But the sheets are not uniform. An equity has "ticker", "sector", and "beta". A bond has "tenor", "coupon", and "rating". A cash position has only "ccy". A fund has "mandate", "risk", and "base_ccy". If you create a schema column for every possible field, you end up with hundreds of NULLs. If you store specs as JSONB, every instrument and fund documents exactly what it has, and the database answers questions like "which equities are in the tech sector?" or "which bonds are rated AAA?" in a single query.

## Why JSONB matters

Traditional relational schemas are rigid. JSONB is flexible. The real power is not just storage, it's that Postgres treats JSON as a first-class citizen. You can index it with GIN, extract nested fields with SQL operators, and query it as fast as you'd query a normalized table. No separate document store, no sync layer, no extra system to operate.

## The wow moment

You load a batch of instruments and funds, each with a different spec sheet in JSONB. You write a query to find all equities that meet a certain criterion (e.g., "sector is tech AND beta is below 1.0"). The query runs in under 50 milliseconds with an index. Then you add a GIN index and re-run; the time barely changes because the index is already doing the work. The whole thing lives in one Postgres table, queried in SQL, backed up with the database.

## What you'll do

1. Inspect the JSONB spec sheets on instruments and funds (unstructured, varying fields).
2. Use the `@>` containment operator to find instruments that match a specification.
3. Use the `#>>` path operator to extract nested fields and filter on them.
4. Create a [GIN](../../docs/glossary.md) index on JSONB and measure the difference (usually negligible, but you'll see it).
5. Write a screening query: "which instruments meet our compliance criteria?" in one line.

Full copy-paste steps are in [`instructions.md`](instructions.md); the exact output and reference numbers are in [`expected.md`](expected.md).

## Prerequisites

Finish [`../../00-setup/`](../../00-setup/) so you have a branch with the bank schema and data loaded. This journey stands alone; no other journey is a prerequisite.

## Wrapping up

Once you've written a few JSONB queries, the pattern becomes routine. The `@>` operator is your go-to for "does this JSON document contain this sub-document?" The `#>>` path operator extracts values for filtering or display. And the GIN index sits transparently in the background, making queries fast without changing your SQL. The next journey moves from data stored in tables to data located in space: [Geospatial](../pg-geo/), branches, custodians, and counterparties on a map, with "within N km" and "nearest to" queries.
