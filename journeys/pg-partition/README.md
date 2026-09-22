# Scale-out: partitioning + lakehouse

> ## What you'll learn
>
> **Key takeaways**
>
> - Declare RANGE partitioning on a time column (e.g., month), and the planner PRUNES unneeded partitions: a one-month query scans 1 of 6 partitions instead of 6.
> - A one-month query stays fast as the table grows to years of data; a full-history query legitimately scans all partitions (and belongs in the lakehouse for scale-out).
> - The honest story: Lakebase is one Postgres (operational scale), not horizontal sharding. Analytics scales to the lakehouse (Delta/Unity Catalog).
>
> **You'll be able to:** build a RANGE-partitioned table on time, run EXPLAIN to show partition pruning, and frame the split between operational and analytical.
>
> **Time:** about 10 minutes  ·  **Status:** live

## The scenario

You're running a digital twin of a manufacturing floor. Hundreds of machines stream telemetry: temperature, vibration, RPM, load, millions of readings per day. That's 365 million readings a year, billions over a decade. A single table.

How do you keep a single-month query fast on a table with years of data?

The answer is declarative RANGE partitioning: split the table by month. Logically it's one table; physically it's 12 per year. When you ask "show me March's telemetry," the planner knows to scan *only* the March partition. Pruning.

When the C-level asks for a trend analysis across 10 years of data, that query legitimately scans all 120 partitions. But that's a heavy analytical query, not an operational one. It belongs in the lakehouse, not Lakebase. (Lakebase syncs the same data to Databricks as Delta, where heavy scans run in parallel across a warehouse, not serially on a single Postgres server.)

This journey shows both: partition pruning for operational queries, and the honest edge for analytics.

## The wow moment

You create a 180k-row table spread across 6 monthly partitions. Run EXPLAIN on a one-month query: the planner shows it scanned 1 partition and pruned the other 5. Then you run EXPLAIN on a full-range query: it scans all 6. Two query shapes, two different query plans, same table.

## What you'll do

1. Create a RANGE-partitioned table by month (6 partitions, 30k rows each).
2. Run EXPLAIN on a one-month query and show partition pruning (1 of 6 scanned).
3. Run EXPLAIN on a full-range query and show all 6 are scanned.
4. Frame the split: operational (Postgres) vs. analytical (lakehouse).

Full copy-paste steps are in [`instructions.md`](instructions.md); the exact output is in [`expected.md`](expected.md).

## Prerequisites

Finish [`../../00-setup/`](../../00-setup/) so you have a branch and can connect. Nothing else; this journey is self-contained.

## Wrapping up

Partitioning is the bridge between operational scale (one Postgres) and analytical scale (lakehouse scale-out).
The next journey [`../pg-lite/`](../pg-lite/) moves to a completely different plane: Postgres at the edge, in the browser, offline-first.
