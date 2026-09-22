# Scale-out: partitioning, expected results

Use this to check your run. Numbers are representative; exact timings vary.
The key: one-month query prunes 5 partitions; full-range query scans all 6.

## Setup

```text
Created partitioned table sensor_readings_partitioned with 6 monthly partitions
Inserted 180k sensor readings (6 months × 30k rows each)
```

## One-month query (PARTITION PRUNING)

```text
One-month query (March 2024):
EXPLAIN output:
  ...
  Subplans Removed: 5
  ...
  ✓ PARTITION PRUNING: 5 of 6 partitions removed (only March scanned)
```

The planner recognized that the WHERE clause (`ts >= '2024-03-01' AND ts < '2024-04-01'`) covers only the March partition.
It pruned the other 5 partitions without scanning them.

## Full-range query (all partitions)

```text
Full-range query (all 6 months):
EXPLAIN output:
  ...
  (All 6 partitions scanned; no pruning possible)
```

The WHERE clause covers Jan–Jun, so all 6 partitions must be scanned.

## Full run

```text
1. Creating partitioned table with 6 months of sensor data:
Created partitioned table sensor_readings_partitioned with 6 monthly partitions
Inserted 180k sensor readings (6 months × 30k rows each)

2. Running EXPLAIN on one-month query (PARTITION PRUNING):
One-month query (March 2024):
EXPLAIN output:
  ...
  ✓ PARTITION PRUNING: 5 of 6 partitions removed (only March scanned)

3. Running EXPLAIN on full-range query (all partitions scanned):
Full-range query (all 6 months):
EXPLAIN output:
  (All 6 partitions scanned; no pruning possible)

✓ [OLTP](../../docs/glossary.md) scale in Postgres, [OLAP](../../docs/glossary.md) scale-out to the lakehouse.
```

## The numbers that matter

| Query scope | Partitions scanned | Pruning | Use case |
| ----------- | ------------------- | ------- | --------- |
| One month | 1 of 6 (17%) | ✓ yes | Operational: "What happened today?" |
| One quarter | 3 of 6 (50%) | ✓ yes | Light analytics: "This season's trend" |
| Full year | 6 of 6 (100%) | none | Heavy analytics: belongs in lakehouse |

> **From the field**
> Partition pruning is the reason a Postgres table can scale to billions of rows and still
> answer operational (small, recent) queries in milliseconds. The planner does the pruning
> automatically based on the WHERE clause, no manual optimization needed. Full-history
> analytical queries (across all partitions) run slowly on a single Postgres server, which is
> why they belong in the lakehouse (Delta), where they scale out to a warehouse. Lakebase
> streams the same data; you use Postgres for [OLTP](../../docs/glossary.md), the lakehouse for [OLAP](../../docs/glossary.md).
