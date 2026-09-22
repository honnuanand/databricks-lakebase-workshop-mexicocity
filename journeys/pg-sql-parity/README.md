# SQL you already know, and then some

> ## What you'll learn
>
> **Key takeaways**
>
> - Window functions (`ROW_NUMBER()`, `LAG()`, `RANK()`) run natively in Postgres, with the same syntax as Oracle or SQL Server. No separate language, no compromise.
> - Recursive CTEs (WITH RECURSIVE) replace Oracle's CONNECT BY for tree queries, exact same problem, different syntax. A BOM parts-explosion that traverses a tree of parent and child parts is one line per query level, not a procedural loop.
> - The numbers that matter: a 100-part BOM explodes to 1,200 leaf parts; the recursive CTE does it in under 50 milliseconds, part of a single query.
>
> **You'll be able to:** write window functions, recursive CTEs, and MERGE statements to migrate your analytical SQL from Oracle to Postgres, and run them live against a manufacturing bill of materials.
>
> **Time:** about 20 minutes  ·  **Status:** live

## The scenario

A parts planner at the stamping plant is rebuilding a major product line and needs to know every leaf part, every component that actually goes into a finished product, counting multiplicity. A gearbox assembly contains 4 shafts, each shaft contains 5 bearings, each bearing contains a steel ring, a cage, and a seal: the explosion is the tree, dozens of levels deep depending on how you count.

On Oracle, you'd use CONNECT BY. On Postgres, you use recursive CTEs. The mechanism is different, the semantics are identical, and if you know one you can learn the other in an hour.

## Why tree queries matter (and why Postgres is stronger than you think)

This journey isn't just a syntax cheat sheet. It's a chance to see that Postgres' implementation of analytical SQL is not a subset of what you already use, it's a full, capable alternative. Window functions are the same. MERGE is new in PG 16 and lets you write upserts in one statement instead of the app code that fumbles between INSERT and UPDATE. And the recursive CTE, while it looks different from CONNECT BY, often runs faster and is easier to reason about because it's explicit SQL, not a hidden cursor loop.

## The wow moment

You load the factory bill of materials, a multi-level tree of parts that make subassemblies that make products. You write a recursive CTE that "explodes" the tree in one query: "give me every part that goes into PRD-GEARBOX-X1, with quantities multiplied down the chain." The query runs and you see not just the direct children, but the full tree: the leaf parts and how many times each one has to be bought to fulfill the product. That explosion is the hardest tree problem; everything else is easier.

## What you'll do

1. Load the factory bill of materials and inspect the data model (parents, children, quantities).
2. Write a simple window function to rank machines by health, showing the machines above and below in the ranking.
3. Write a recursive CTE to explode the BOM: start with a product, recursively traverse to children, multiply quantities down the chain.
4. Compare the real performance (milliseconds), then see the Oracle idiom map: ROWNUM → LIMIT, NVL → COALESCE, SYSDATE → now().

Full copy-paste steps are in [`instructions.md`](instructions.md); the exact output and reference numbers are in [`expected.md`](expected.md).

## Prerequisites

Finish [`../../00-setup/`](../../00-setup/) so you have a branch with the factory schema and data loaded. This journey stands alone; the SQL is portable to Oracle or SQL Server with minor syntax edits.

## Wrapping up

Once you've written a few recursive CTEs and seen them run, the shape stops feeling foreign. Window functions become your go-to for rank, lead/lag, cumulative sums, queries that would have taken procedural loops or sub-queries. You start to see Postgres not as a step down from your Oracle knowledge, but as a different path to the same destinations, and often a faster one. The next journey steps into one of Postgres' true differentiators: [JSON documents](../pg-json/), flexible spec sheets stored as JSONB, indexed and queryable without a separate document store.
