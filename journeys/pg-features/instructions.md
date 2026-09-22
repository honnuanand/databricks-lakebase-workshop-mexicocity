# Feature store, served online, instructions

Run these on your own branch. If you haven't done [`../../00-setup/`](../../00-setup/), do that first.

Everything here is a single script: [`./pg_features.py`](./pg_features.py).

## Run it end to end

```bash
cd journeys/pg-features
python pg_features.py
```

This creates raw events, materializes features, and measures lookup latency. Read on for what each step does;
the exact output is in [`expected.md`](expected.md).

## Or step through it by hand

### Step 1, create raw events table

```bash
python pg_features.py --step setup
```

Creates a raw events table:

```sql
CREATE TABLE machine_events_for_features (
    event_id BIGSERIAL PRIMARY KEY,
    machine_id TEXT NOT NULL,
    event_ts TIMESTAMPTZ DEFAULT now(),
    event_type TEXT,      -- run, failure, maintenance
    cycles INT,
    temp_c NUMERIC(6,2),
    vibration_mm_s NUMERIC(6,2)
)
```

Then seeds it with 10k events across 100 machines. This is the raw telemetry.

### Step 2, materialize features

```bash
python pg_features.py --step materialize
```

Aggregates events into a feature table (one row per machine):

```sql
CREATE TABLE machine_features_online (
    machine_id TEXT PRIMARY KEY,
    runs_this_month INT,
    failures_this_month INT,
    avg_temp_c NUMERIC(8,2),
    avg_vibration_mm_s NUMERIC(8,2),
    total_cycles INT,
    computed_at TIMESTAMPTZ
)
```

Then INSERT:

```sql
INSERT INTO machine_features_online(...)
SELECT
    e.machine_id,
    COUNT(CASE WHEN e.event_type = 'run' THEN 1 END) as runs_this_month,
    COUNT(CASE WHEN e.event_type = 'failure' THEN 1 END) as failures_this_month,
    ... aggregates ...
FROM machine_events_for_features e
WHERE e.event_ts >= now() - interval '30 days'
GROUP BY e.machine_id
```

This is the materialization step: computed offline (or on a schedule), written to the online store.

### Step 3, serve online (measure latency)

```bash
python pg_features.py --step serve
```

Runs 100 primary-key lookups:

```sql
SELECT * FROM machine_features_online WHERE machine_id = %s
```

Each lookup is timed. The script reports average, min, max latency.

Expected: 2-5 ms per lookup.

## What you just did

You built an online feature store: materialize features from raw events, serve them keyed by machine_id,
and measure single-digit-millisecond latency. This is how models get features at inference time without
re-computing them on demand.

Check the numbers against [`expected.md`](expected.md), and if anything went sideways, [`faq.md`](faq.md) has the common causes.
