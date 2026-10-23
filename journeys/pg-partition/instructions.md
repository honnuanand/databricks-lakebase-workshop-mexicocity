# Scale-out: partitioning, instructions

## How to run this journey

There are a few ways to work through the steps. Pick one:

- **Notebook, step by step (recommended for learning):** open [`pg_partition.ipynb`](pg_partition.ipynb) and run one cell at a time. Reading each result before the next step is where the learning happens.
- **In a Databricks workspace:** import [`pg_partition_databricks.py`](pg_partition_databricks.py) and run it cell by cell there.
- **By hand:** follow the numbered steps below, copying each command yourself.
- **Just see it work:** run `python pg_partition.py` from this folder to execute the whole thing at once. Fast, but you learn the most from the notebook.

Run these on your own branch. If you haven't done [`../../00-setup/`](../../00-setup/), do that first.

Everything here is a single script: [`./pg_partition.py`](./pg_partition.py).

## Run it end to end

```bash
cd journeys/pg-partition
python pg_partition.py
```

This builds a 6-partition table, loads 180k rows, and runs EXPLAIN on both a one-month and a full-range query.
Read on for what each step does; the exact output is in [`expected.md`](expected.md).

## Or step through it by hand

### Step 1, create partitioned table

```bash
python pg_partition.py --step setup
```

Creates a RANGE-partitioned table on the month of `ts`:

```sql
CREATE TABLE txn_partitioned (
    txn_id BIGSERIAL,
    account_id TEXT NOT NULL,
    ts TIMESTAMPTZ NOT NULL,
    amount NUMERIC(12,2),
    anomaly_score NUMERIC(6,2),
    PRIMARY KEY (txn_id, ts)
) PARTITION BY RANGE (ts)
```

Then creates 6 monthly partitions (Jan–Jun 2024), each holding 30k rows (180k total).

Logically one table, physically 6 sub-tables, one per month.

### Step 2, run EXPLAIN on a one-month query

```bash
python pg_partition.py --step explain
```

This runs two queries and shows their EXPLAIN plans:

**One-month query:**

```sql
SELECT COUNT(*) FROM txn_partitioned
WHERE ts >= '2024-03-01' AND ts < '2024-04-01'
```

EXPLAIN output shows: `Subplans Removed: 5`, the planner pruned 5 of 6 partitions. It scanned only March.

**Full-range query:**

```sql
SELECT COUNT(*) FROM txn_partitioned
WHERE ts >= '2024-01-01' AND ts < '2024-07-01'
```

EXPLAIN output shows no pruning, all 6 partitions must be scanned.

## What you just did

You built a partitioned table, showed how the planner prunes unneeded partitions on targeted
queries, and demonstrated that full-range analytical queries necessarily scan all partitions
(and belong in the lakehouse for scale-out).

Check the numbers against [`expected.md`](expected.md), and if anything went sideways, [`faq.md`](faq.md) has the common causes.
