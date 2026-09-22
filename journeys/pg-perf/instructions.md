# Tune the planner, instructions

Run these on your own branch. If you haven't done [`../../00-setup/`](../../00-setup/), do that
first; you need `LB_PROFILE`, `LB_PROJECT`, `LB_BRANCH`, and `LB_SCHEMA` set.

Everything here is a single script you can read: [`../../common/scripts/pg_perf.py`](../../common/scripts/pg_perf.py).
You can run it end to end, or follow the steps by hand to see each piece.

## Run it end to end

```bash
cd common/scripts
python pg_perf.py
```

This walks the whole story and prints the before/after row estimates. Read on for what each step does; the exact output
to expect is in [`expected.md`](expected.md).

## Or step through it by hand

### Step 1, set up the demo table

```bash
python pg_perf.py --step setup
```

Creates a table with 100k rows where `machine_line` is fully determined by `plant_id` (100% correlated):
- Plant PL-DETROIT → Stamping-A, Stamping-B, Stamping-C
- Plant PL-SHANGHAI → Assembly-1, Assembly-2

The planner has no knowledge of this correlation yet.

### Step 2, show the bad estimate (no statistics)

```bash
python pg_perf.py --step before
```

Run EXPLAIN ANALYZE on a correlated filter:

```sql
SELECT id FROM machine_perf_demo
WHERE plant_id = 'PL-DETROIT' AND machine_line = 'Stamping-A'
```

The planner estimates around 15k-20k rows (badly wrong; actual is ~25k). It treats plant and machine_line as
independent random columns, so the intersection estimate is tiny. This estimate cascades: the planner chooses
wrong joins and memory settings downstream.

You'll see the ratio: estimate is 40% of actual (2.5× under-estimate).

### Step 3, create statistics to teach the correlation

```bash
python pg_perf.py --step stats
```

Run:

```sql
CREATE STATISTICS machine_perf_stat
ON plant_id, machine_line
FROM machine_perf_demo
```

Then re-analyze:

```sql
ANALYZE machine_perf_demo
```

This teaches the planner that `plant_id` and `machine_line` are correlated. The statistics capture the
dependency, and the planner uses them from this point forward.

### Step 4, show the fixed estimate (with statistics)

```bash
python pg_perf.py --step after
```

Run the same query again:

```sql
SELECT id FROM machine_perf_demo
WHERE plant_id = 'PL-DETROIT' AND machine_line = 'Stamping-A'
```

The estimate now snaps to ~25k, matching the actual rows. The planner's knowledge is tuned. Same data, same table, same query; the difference is the statistics.

## What you just did

You diagnosed a planner under-estimate on two correlated columns, created extended statistics to teach the
planner the correlation, and proved the fix with server-measured EXPLAIN ANALYZE. The DBA's craft: tune
the planner's knowledge, not the schema.

Check the numbers you saw against [`expected.md`](expected.md), and if anything went sideways, [`faq.md`](faq.md)
has the common causes.
