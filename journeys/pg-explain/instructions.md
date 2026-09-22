# Watch the planner, instructions

## How to run this journey

There are a few ways to work through the steps. Pick one:

- **Notebook, step by step (recommended for learning):** open [`pg_explain.ipynb`](pg_explain.ipynb) and run one cell at a time. Reading each result before the next step is where the learning happens.
- **In a Databricks workspace:** import [`pg_explain_databricks.py`](pg_explain_databricks.py) and run it cell by cell there.
- **By hand:** follow the numbered steps below, copying each command yourself.
- **Just see it work:** run `python pg_explain.py` from this folder to execute the whole thing at once. Fast, but you learn the most from the notebook.

Run these on your own branch. If you haven't done [`../../00-setup/`](../../00-setup/), do that first; you need `LB_PROFILE`, `LB_PROJECT`, `LB_BRANCH`, and `LB_SCHEMA` set.

Everything here is a single script you can read: [`./pg_explain.py`](./pg_explain.py). You can run it end to end, or follow the steps by hand to see each piece.

## Run it end to end

```bash
cd journeys/pg-explain
python pg_explain.py
```

This walks through the entire journey and prints results. Read on for what each step does; the exact output to expect is in [`expected.md`](expected.md).

## Or step through it by hand

### Step 1, create and seed a table with 50k rows

Create a synthetic table to make the seq scan expensive:

```bash
python pg_explain.py --step seed
```

The script creates a table with 50,000 synthetic sensor readings, each with an unindexed `machine_id` column. The goal: a seq scan that reads all 50,000 rows will be visible in EXPLAIN.

### Step 2, query unindexed column, run EXPLAIN ANALYZE

Query the table filtering on machine_id (unindexed):

```bash
python pg_explain.py --step explain-before
```

The script runs:

```sql
EXPLAIN (ANALYZE, BUFFERS) SELECT COUNT(*) FROM sensor_readings WHERE machine_id = 'M-204';
```

Output shows:
- Plan: `Seq Scan on sensor_readings`
- Rows: all 50,000 are scanned
- Actual Time: ~50 milliseconds
- Buffers: ~500 pages hit

This is the baseline: unindexed, expensive.

### Step 3, create an index

Create a btree index on machine_id:

```bash
python pg_explain.py --step index
```

The script runs:

```sql
CREATE INDEX idx_sensor_machine_id ON sensor_readings (machine_id);
ANALYZE sensor_readings;
```

The ANALYZE updates planner statistics so the planner knows the index will help.

### Step 4, re-query and run EXPLAIN ANALYZE

Run the same query again:

```bash
python pg_explain.py --step explain-after
```

Output now shows:
- Plan: `Index Scan using idx_sensor_machine_id`
- Rows: only ~56 rows are scanned (the matching ones)
- Actual Time: ~1 millisecond
- Buffers: ~5 pages hit

The planner flipped from sequential scan to index scan. The time improved 50x.

### Step 5, side-by-side comparison

The script prints before/after numbers:

```bash
python pg_explain.py --step compare
```

Results show the exact cost, time, and buffer statistics for both plans. This is how you prove an index helped, and decide whether the improvement justifies the maintenance cost.

## What you just did

You wrote a query, saw it was slow with EXPLAIN ANALYZE (seq scan, 50 ms), added an index, and re-ran EXPLAIN to see the planner flip to an index scan (1 ms). You measured the before/after, proving the index helped. This is the DBA's real workflow.
