# Scale-out: partitioning, FAQ

## The partitions weren't created / queries are slow

Make sure the script ran the setup step. Partitions are only created if the table is created with `PARTITION BY RANGE`.

If you're on a very small instance or the project is scaled to zero, the queries may be slow.
Check the branch is `ACTIVE`:

```bash
python lakebase.py --check
```

## Can I partition on non-time columns?

Yes, RANGE works on any ordered column: numbers, strings, dates. Most common is time (date/timestamp),
but you can partition by:
- **Date range**: range by day, month, year.
- **Numeric range**: range by ID bands (e.g., machines 0-999, 1000-1999, etc.).
- **Geographic range** (rare): range by coordinates.

Time-based is most useful because old data naturally ages out (you can DROP old partitions to free space).

## Can I partition on multiple columns?

Yes, using composite ranges or list partitioning. For simplicity, this journey uses RANGE on one column.

## If I partition by month, do I manually manage adding new partitions?

You should. Ideally, write a script that runs monthly (or weekly, or daily) to create the next partition(s).
Some systems use `pg_partman` (an extension) to automate this.

For this journey, we created 6 fixed partitions. In production, you'd add a new partition as each month starts.

## Why not just create indexes instead of partitioning?

Different tools:
- **Index**: helps the planner choose a faster path *within* a table (e.g., "use btree on date").
- **Partition**: reduces the amount of data the planner has to scan; the pruning happens at the table level.

On a 1-year table with 365 million rows, even an index may require millions of row checks. Partition pruning
avoids scanning the table at all for 11 of the 12 months. Pruning is often faster than indexing on very large tables.

Both matter; they're complementary.

## What happens when I query across two adjacent partitions?

The planner scans both partitions. That's correct, if your query needs data from Feb and March,
both partitions must be read.

## If I partition by day instead of month, will queries be faster?

Depends. More partitions → smaller each partition → finer-grained pruning (a one-day query on
365 daily partitions prunes 364). But many small partitions also add overhead. A good rule: partition
granularity = your smallest common query scope. For most systems, monthly partitions are reasonable.

## This is 6 months. In production, how long does it take to create all the partitions upfront?

Creating the partitions themselves is fast (milliseconds). Inserting 180k rows in the script takes longer
(seconds). In production, you'd typically:
1. Create 1 partition at a time, as new data arrives.
2. Archive or drop old partitions after they age out.
3. Use a script to automate partition maintenance.

See `pg_partman` for production automation.
