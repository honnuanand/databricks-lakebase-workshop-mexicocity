# Watch the planner

> ## What you'll learn
>
> **Key takeaways**
>
> - EXPLAIN ANALYZE shows the real query plan and actual execution time. BUFFERS shows which indexes and tables the planner accessed (sequential scan vs index scan).
> - A sequential scan over an unindexed column reads all 50,000 rows to find 56. An index scan reads only the matching rows. The cost-based planner flips between these based on row counts and selectivity.
> - The numbers that matter: adding a single btree index can reduce query time from 50 milliseconds (seq scan over 50k rows) to 1 millisecond (index scan finding 56 rows). The speedup is 50x.
>
> **You'll be able to:** use EXPLAIN to see why a query is slow, create the right index, and watch the planner flip from sequential scan to index scan with real timing and buffer statistics.
>
> **Time:** about 20 minutes  ·  **Status:** live

## The scenario

A DBA's daily life: a query is slow. "Why?" The usual answers are hand-waving ("add an index") or trial-and-error. EXPLAIN ANALYZE is the DBA's actual tool. Run it before the index, run it after, and see the numbers. The query life: unindexed column, sequential scan, 50 milliseconds. Add the index, re-run, and the planner flips to an index scan, 1 millisecond. Real costs. Real time. Real reasons.

## Why EXPLAIN matters

Query optimization is not guesswork. EXPLAIN shows you exactly what the planner chose and why. The plan is a tree: each node is an operation (Seq Scan, Index Scan, Sort, Aggregate, Join). Each node shows estimated rows, actual rows, cost, time, buffers. If the estimate is wrong (shown as "Actual Rows" mismatching "Rows"), the planner made a bad choice and you might need ANALYZE to update statistics.

## The wow moment

You run a query and it takes 50 milliseconds. You look at EXPLAIN and see "Seq Scan, reads 50,000 rows to find 56." You create one index, re-run EXPLAIN, and the plan changes to "Index Scan, reads 56 rows." The actual time is 1 millisecond. The same query, two different plans, 50x difference in speed, and you saw it happen.

## What you'll do

1. Create a table with 50,000 synthetic sensor readings.
2. Query an unindexed column: count rows matching a condition. Run EXPLAIN ANALYZE to see the cost and time.
3. Add a btree index on that column.
4. Re-run the query and EXPLAIN. Watch the planner flip to an index scan.
5. Compare the before/after numbers: cost, time, rows scanned, buffers hit.

Full copy-paste steps are in [`instructions.md`](instructions.md); the exact output and reference numbers are in [`expected.md`](expected.md).

## Prerequisites

Finish [`../../00-setup/`](../../00-setup/) so you have a branch. This journey creates its own table (synthetic sensor data), so no other setup is needed.

## Wrapping up

EXPLAIN is the flashlight you shine into a slow query. It reveals why the planner chose what it chose, and it lets you prove that your index actually helped. The next journey dives deep into the machinery underneath: [MVCC and the WAL](../pg-mvcc/), how Postgres writes data without ever blocking readers.
