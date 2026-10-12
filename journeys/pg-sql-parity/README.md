# SQL you already know, and then some

> ## What you'll learn
>
> **Key takeaways**
>
> - Window functions (`ROW_NUMBER()`, `LAG()`, `RANK()`) run natively in Postgres, with the same syntax as Oracle or SQL Server. No separate language, no compromise.
> - Recursive CTEs (WITH RECURSIVE) replace Oracle's CONNECT BY for tree queries, exact same problem, different syntax. A [holdings explosion](../../docs/glossary.md) that traverses a fund down through its sub-funds to the underlying instruments is one line per query level, not a procedural loop.
> - The numbers that matter: a fund-of-funds with 200 line items explodes to 1,800 underlying positions; the recursive CTE does it in under 50 milliseconds, part of a single query.
>
> **You'll be able to:** write window functions, recursive CTEs, and MERGE statements to migrate your analytical SQL from Oracle to Postgres, and run them live against a real fund holdings tree.
>
> **Time:** about 20 minutes  ·  **Status:** live

## The scenario

A portfolio controller at the bank needs the true look-through of a fund: every underlying instrument that a fund actually holds, counting multiplicity, when the fund holds other funds that hold other funds. FUND-GROWTH-A holds cash plus two units of an equity sleeve plus Microsoft; the equity sleeve itself holds Apple plus two units of a 10-year Treasury. The look-through is the tree, as many levels deep as the structure nests.

On Oracle, you'd use CONNECT BY. On Postgres, you use recursive CTEs. The mechanism is different, the semantics are identical, and if you know one you can learn the other in an hour.

## Why tree queries matter (and why Postgres is stronger than you think)

This journey isn't just a syntax cheat sheet. It's a chance to see that Postgres' implementation of analytical SQL is not a subset of what you already use, it's a full, capable alternative. Window functions are the same. MERGE is new in PG 16 and lets you write upserts in one statement instead of the app code that fumbles between INSERT and UPDATE. And the recursive CTE, while it looks different from CONNECT BY, often runs faster and is easier to reason about because it's explicit SQL, not a hidden cursor loop.

## The wow moment

You load the fund holdings tree, a multi-level structure of funds that hold sub-funds that hold instruments. You write a recursive CTE that "explodes" the tree in one query: "give me every instrument that FUND-GROWTH-A is exposed to, with units multiplied down the chain." The query runs and you see not just the direct line items, but the full look-through: the leaf instruments and how many units of each the fund really owns once you unwind the nesting. That explosion is the hardest tree problem; everything else is easier.

## What you'll do

1. Load the fund holdings tree and inspect the data model (parents, children, units).
2. Write a simple window function to rank accounts by health, showing the accounts above and below in the ranking.
3. Write a recursive CTE to explode the [holdings tree](../../docs/glossary.md): start with a fund, recursively traverse to its holdings, multiply units down the chain.
4. Compare the real performance (milliseconds), then see the Oracle idiom map: ROWNUM to LIMIT, NVL to COALESCE, SYSDATE to now().

Full copy-paste steps are in [`instructions.md`](instructions.md); the exact output and reference numbers are in [`expected.md`](expected.md).

## Prerequisites

Finish [`../../00-setup/`](../../00-setup/) so you have a branch with the bank schema and data loaded. This journey stands alone; the SQL is portable to Oracle or SQL Server with minor syntax edits.

## Wrapping up

Once you've written a few recursive CTEs and seen them run, the shape stops feeling foreign. Window functions become your go-to for rank, lead/lag, cumulative sums, queries that would have taken procedural loops or sub-queries. You start to see Postgres not as a step down from your Oracle knowledge, but as a different path to the same destinations, and often a faster one. The next journey steps into one of Postgres' true differentiators: [JSON documents](../pg-json/), flexible spec sheets stored as JSONB, indexed and queryable without a separate document store.
