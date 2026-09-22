# Tune the planner

> ## What you'll learn
>
> **Key takeaways**
>
> - The planner assumes columns are independent; a filter on two CORRELATED columns (e.g., plant and machine_line) under-estimates rows by 2.5x or more.
> - `CREATE STATISTICS` teaches the planner column dependencies, and the row estimate snaps to reality, fixing downstream join and memory choices.
> - Extended statistics are tuning the planner's *knowledge*, not the data, they cost nothing to create or maintain.
>
> **You'll be able to:** diagnose a planner under-estimate on correlated columns and fix it with `CREATE STATISTICS`, proven by server-measured EXPLAIN ANALYZE.
>
> **Time:** about 10 minutes  ·  **Status:** live

## The scenario

You're running a multi-plant factory. The operations database tracks machines across plants, and each plant has specific production lines (a stamping plant in Detroit runs Stamping-A, Stamping-B, Stamping-C; an assembly plant in Shanghai runs Assembly-1, Assembly-2). Plant and machine_line are **correlated**: knowing the plant tells you the line.

A query filters machines by both: "Give me all machines in PL-DETROIT on Stamping-A." By default, the Postgres planner assumes the two columns are independent, it has no idea that a plant fully determines which lines exist there. So it estimates the intersection as if they were random, under-estimating by 2 to 3 times the actual rows. That estimate cascades into the rest of the query: the planner chooses the wrong join method, allocates the wrong amount of work memory, picks the wrong scan strategy.

The DBA's subtle move is to teach the planner the correlation without changing the data: `CREATE STATISTICS ... ON plant, machine_line`.

## What a bad estimate actually costs

The under-estimate feels harmless until it compounds. A query on 100k rows that should return 25k gets estimated as 10k. The planner thinks it's small, picks a nested-loop join that works for 10k rows but thrashes on 25k. The query runs 10 times slower than it should. Or it allocates the wrong amount of work_mem and spills to disk. Or it picks an index that makes sense for a 10k result but is wrong for 25k.

This journey shows the measurement: the honest numbers, from EXPLAIN ANALYZE, that prove the fix works.

## The wow moment

You run EXPLAIN ANALYZE on the query and see the estimate is wildly wrong. You create one SQL statement (`CREATE STATISTICS`), re-analyze, and run the same query again. The estimate snaps from 16k to 40k, matching reality exactly. Same data, same table, same query. You tuned the planner's knowledge.

## What you'll do

1. Create a demo table with correlated columns (plant determines machine_line).
2. Show the bad estimate: filter on both columns, and the planner guesses 2.5x too low.
3. Create statistics to teach the planner the correlation.
4. Re-run the same query and watch the estimate snap to the correct value.
5. See the EXPLAIN output for both.

Full copy-paste steps are in [`instructions.md`](instructions.md); the exact output and numbers to check against are in [`expected.md`](expected.md).

## Prerequisites

Finish [`../../00-setup/`](../../00-setup/) so you have a branch and can connect. Nothing else; this journey stands on its own.

## Wrapping up

This is the DBA's craft: tuning the *knowledge* the planner works with, not the schema or data. The next journey [`../pg-index/`](../pg-index/) moves to indexes, another tuning lever, but from a planner-choice angle: building indexes so the planner *picks* them on the queries that matter.
