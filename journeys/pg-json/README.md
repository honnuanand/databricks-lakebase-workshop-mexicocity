# JSON documents

> ## What you'll learn
>
> **Key takeaways**
>
> - JSONB stores flexible, schema-free documents natively in Postgres. No schema migration; no separate document store.
> - Queries use simple operators: `@>` (contains), `#>>` (extract path), `?` (key exists). They run at database speed, indexed by GIN.
> - The numbers that matter: a compliance query over 500 parts with varying capability specs (some have SATVOICE, others don't; some specify an altitude limit, others don't) runs in under 50 milliseconds with a GIN index.
>
> **You'll be able to:** store flexible product and part specification sheets as JSONB, query them to find compatible parts and products without schema changes, and index them for fast searches.
>
> **Time:** about 20 minutes  ·  **Status:** live

## The scenario

At the stamping plant, every part has a capability sheet, dimensions, materials, certifications. But the sheets are not uniform. A bearing has a "load_capacity_kg" and a "temperature_range" (min and max temps). A fastener has "tensile_strength_mpa" and a "coating". A shaft might have a "runout_mm" and "surface_finish_ra". If you create a schema column for every possible field, you end up with hundreds of NULLs. If you store it as JSONB, every part documents exactly what it has, and the database answers questions like "which parts are certified for -20°C to +80°C?" in a single query.

## Why JSONB matters

Traditional relational schemas are rigid. JSONB is flexible. The real power is not just storage, it's that Postgres treats JSON as a first-class citizen. You can index it with GIN (Generalized Inverted Index), extract nested fields with SQL operators, and query it as fast as you'd query a normalized table. No separate document store, no sync layer, no extra system to operate.

## The wow moment

You load a batch of 500 parts, each with a different spec sheet in JSONB. You write a query to find all parts that meet a certain spec (e.g., "temperature range includes -20°C AND coating includes 'zinc'"). The query runs in under 50 milliseconds with an index. Then you add an index and re-run, the time barely changes, because GIN is already doing the work. The whole thing lives in one Postgres table, queried in SQL, backed up with the database.

## What you'll do

1. Inspect the JSONB spec sheets on parts and products (unstructured, varying fields).
2. Use the `@>` containment operator to find parts that match a specification.
3. Use the `#>>` path operator to extract nested fields and filter on them.
4. Create a GIN index on JSONB and measure the difference (usually negligible, but you'll see it).
5. Write a compliance query: "which parts meet our harsh-environment spec?" in one line.

Full copy-paste steps are in [`instructions.md`](instructions.md); the exact output and reference numbers are in [`expected.md`](expected.md).

## Prerequisites

Finish [`../../00-setup/`](../../00-setup/) so you have a branch with the factory schema and data loaded. This journey stands alone; no other journey is a prerequisite.

## Wrapping up

Once you've written a few JSONB queries, the pattern becomes routine. The `@>` operator is your go-to for "does this JSON document contain this sub-document?" The `#>>` path operator extracts values for filtering or display. And the GIN index sits transparently in the background, making queries fast without changing your SQL. The next journey moves from data stored in tables to data located in space: [Geospatial](../pg-geo/), warehouses, suppliers, and plants on a map, with "within N km" and "nearest to" queries.
