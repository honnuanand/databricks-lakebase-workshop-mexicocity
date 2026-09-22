# Geospatial

> ## What you'll learn
>
> **Key takeaways**
>
> - PostGIS turns Postgres into a full GIS database. `geography(POINT)` types store lat/lon as real geographic coordinates, not just numbers.
> - Spatial operators like `ST_DWithin` ("within N kilometers") and `<->` (nearest neighbor) run natively in SQL, indexed by GiST.
> - The numbers that matter: finding all warehouses within 100 km of a plant or the nearest supplier among 50 candidates takes under 10 milliseconds with a GiST index.
>
> **You'll be able to:** plot plants, machines, warehouses, and suppliers on a map; answer "which warehouses are within N km of plant P?" and "what's the nearest supplier?" in a single SQL query.
>
> **Time:** about 25 minutes  ·  **Status:** live

## The scenario

A stranded part at the Detroit plant. The urgent question: which warehouses have the replacement in stock, and which one is closest? On a traditional database, you'd calculate distances manually (Haversine formula in the app), fetch candidates, sort by distance, and pick the closest. PostGIS does all of that in SQL. You store plants, warehouses, and suppliers as geographic points, index them, and let the database answer location questions at line speed.

## Why PostGIS matters

Geography is real in supply chain, field service, logistics, and any operation spanning a map. Most databases make you handle it yourself: store lat/lon as numbers, write distance logic in the app, and hope nobody notices the edge cases (wrapping at datelines, polar distortions). PostGIS is PostgreSQL's native GIS, it understands spherical geometry, projections, and all the gotchas. Queries read like geography, not math.

## The wow moment

You create a geography column on your warehouse table, store the coordinates, and index it with GiST. Then you write "find the 3 nearest warehouses to plant P", and the query takes the same time whether there are 10 warehouses or 10,000. The operator `<->` finds the nearest neighbor in a single pass. Compare that to the app that fetches all rows, calculates distances in a loop, and sorts, PostGIS wins every time.

## What you'll do

1. Enable PostGIS and inspect the geography columns (plant, warehouse, supplier locations).
2. Query "warehouses within 100 km of plant P" using `ST_DWithin`.
3. Query "nearest 3 suppliers to plant P" using the `<->` distance operator.
4. Create a GiST index on geography columns and measure the performance difference.
5. Verify the index is being used with EXPLAIN.

Full copy-paste steps are in [`instructions.md`](instructions.md); the exact output and reference numbers are in [`expected.md`](expected.md).

## Prerequisites

Finish [`../../00-setup/`](../../00-setup/) so you have a branch. PostGIS must be available (most Postgres installations have it; if not, the journey includes an explainer fallback).

## Wrapping up

Once PostGIS is in your toolkit, spatial queries become routine. `ST_DWithin` for range searches, `<->` for nearest-neighbor, `ST_Intersects` for polygon containment, all read like geography and run fast with a GiST index. The next journey takes a different angle on fast searching: [Search, three ways](../pg-search/), full-text, fuzzy, and hybrid semantic search over maintenance logs.
