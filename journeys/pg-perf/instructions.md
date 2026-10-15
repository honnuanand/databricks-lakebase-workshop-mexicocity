# Tune the planner, instructions

## How to run this journey

There are a few ways to work through the steps. Pick one:

- **Notebook, step by step (recommended for learning):** open [`pg_perf.ipynb`](pg_perf.ipynb) and run one cell at a time. Reading each result before the next step is where the learning happens.
- **In a Databricks workspace:** import [`pg_perf_databricks.py`](pg_perf_databricks.py) and run it cell by cell there.
- **By hand:** follow the numbered steps below, copying each command yourself.
- **Just see it work:** run `python pg_perf.py` from this folder to execute the whole thing at once. Fast, but you learn the most from the notebook.

Run these on your own branch. If you haven't done [`../../00-setup/`](../../00-setup/), do that
first; you need `LB_PROFILE`, `LB_PROJECT`, `LB_BRANCH`, and `LB_SCHEMA` set.

Everything here is a single script you can read: [`./pg_perf.py`](./pg_perf.py).
You can run it end to end, or follow the steps by hand to see each piece.

## Run it end to end

```bash
cd journeys/pg-perf
python pg_perf.py
```

This walks the whole story and prints the before/after row estimates. Read on for what each step does; the exact output
to expect is in [`expected.md`](expected.md).

## Or step through it by hand

### Step 1, set up the demo table

```bash
python pg_perf.py --step setup
```

Creates a table with 100k rows where `region` is fully determined by `branch_id` (100% correlated):
- Branch BR-CDMX → MX-Centro
- Branch BR-MTY → MX-Noreste

The planner has no knowledge of this correlation yet.

### Step 2, show the bad estimate (no statistics)

```bash
python pg_perf.py --step before
```

Run EXPLAIN ANALYZE on a correlated filter:

```sql
SELECT account_id FROM account_perf_demo
WHERE branch_id = 'BR-CDMX' AND region = 'MX-Centro'
```

The planner estimates around 15k-20k rows (badly wrong; actual is ~25k). It treats branch and region as
independent random columns, so the intersection estimate is tiny. This estimate cascades: the planner chooses
wrong joins and memory settings downstream.

You'll see the ratio: estimate is 40% of actual (2.5× under-estimate).

### Step 3, create statistics to teach the correlation

```bash
python pg_perf.py --step stats
```

Run:

```sql
CREATE STATISTICS account_perf_stat
ON branch_id, region
FROM account_perf_demo
```

Then re-analyze:

```sql
ANALYZE account_perf_demo
```

This teaches the planner that `branch_id` and `region` are correlated. The statistics capture the
dependency, and the planner uses them from this point forward.

### Step 4, show the fixed estimate (with statistics)

```bash
python pg_perf.py --step after
```

Run the same query again:

```sql
SELECT account_id FROM account_perf_demo
WHERE branch_id = 'BR-CDMX' AND region = 'MX-Centro'
```

The estimate now snaps to ~25k, matching the actual rows. The planner's knowledge is tuned. Same data, same table, same query; the difference is the statistics.

## What you just did

You diagnosed a planner under-estimate on two correlated columns, created extended statistics to teach the
planner the correlation, and proved the fix with server-measured EXPLAIN ANALYZE. The DBA's craft: tune
the planner's knowledge, not the schema.

Check the numbers you saw against [`expected.md`](expected.md), and if anything went sideways, [`faq.md`](faq.md)
has the common causes.
