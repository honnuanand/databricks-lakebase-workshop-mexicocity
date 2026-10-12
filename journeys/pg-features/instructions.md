# Feature store, served online, instructions

## How to run this journey

There are a few ways to work through the steps. Pick one:

- **Notebook, step by step (recommended for learning):** open [`pg_features.ipynb`](pg_features.ipynb) and run one cell at a time. Reading each result before the next step is where the learning happens.
- **In a Databricks workspace:** import [`pg_features_databricks.py`](pg_features_databricks.py) and run it cell by cell there.
- **By hand:** follow the numbered steps below, copying each command yourself.
- **Just see it work:** run `python pg_features.py` from this folder to execute the whole thing at once. Fast, but you learn the most from the notebook.

Run these on your own branch. If you haven't done [`../../00-setup/`](../../00-setup/), do that first.

Everything here is a single script: [`./pg_features.py`](./pg_features.py).

## Run it end to end

```bash
cd journeys/pg-features
python pg_features.py
```

This creates raw events, materializes features, and measures lookup latency. Read on for what each step does. The exact output is in [`expected.md`](expected.md).

## Or step through it by hand

### Step 1, create raw events table

```bash
python pg_features.py --step setup
```

Creates a raw events table:

```sql
CREATE TABLE account_events_for_features (
    event_id BIGSERIAL PRIMARY KEY,
    account_id TEXT NOT NULL,
    event_ts TIMESTAMPTZ DEFAULT now(),
    event_type TEXT,      -- purchase, wire, dispute, chargeback
    amount_usd NUMERIC(12,2),
    anomaly_score NUMERIC(6,2),
    util_pct NUMERIC(6,2)
)
```

Then seeds it with 10k events across 100 accounts. This is the raw transaction telemetry.

### Step 2, materialize features

```bash
python pg_features.py --step materialize
```

Aggregates events into a feature table, one row per account:

```sql
CREATE TABLE account_features_online (
    account_id TEXT PRIMARY KEY,
    txns_this_month INT,
    disputes_this_month INT,
    avg_anomaly_score NUMERIC(8,2),
    avg_util_pct NUMERIC(8,2),
    total_amount_usd NUMERIC(12,2),
    computed_at TIMESTAMPTZ
)
```

Then INSERT:

```sql
INSERT INTO account_features_online(...)
SELECT
    e.account_id,
    COUNT(CASE WHEN e.event_type = 'purchase' THEN 1 END) as txns_this_month,
    COUNT(CASE WHEN e.event_type = 'dispute' THEN 1 END) as disputes_this_month,
    ... aggregates ...
FROM account_events_for_features e
WHERE e.event_ts >= now() - interval '30 days'
GROUP BY e.account_id
```

This is the materialization step: computed offline, or on a schedule, written to the online store.

### Step 3, serve online, measure latency

```bash
python pg_features.py --step serve
```

Runs 100 primary-key lookups:

```sql
SELECT * FROM account_features_online WHERE account_id = %s
```

Each lookup is timed. The script reports average, min, max latency.

Expected: 2-5 ms per lookup.

## What you just did

You built an online feature store: materialize features from raw events, serve them keyed by account_id, and measure single-digit-millisecond latency. This is how fraud-risk models get features at inference time without re-computing them on demand.

Check the numbers against [`expected.md`](expected.md), and if anything went sideways, [`faq.md`](faq.md) has the common causes.
