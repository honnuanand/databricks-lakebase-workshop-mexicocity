# Feature store, served online, expected results

Use this to check your run. Latencies vary with where the code runs and with instance load. The
shape is what matters: primary-key lookups in single-digit milliseconds when the code runs in the
workspace, next to the database. The examples below are from live runs on 2026-10-15.

## Notebook (Databricks serverless)

```text
✓ Created raw events table
✓ Seeded 10k events across 100 accounts
✓ Created online feature table
✓ Materialized features from events (offline step)
✓ Measured 100 lookups:
  Average: 1.59 ms
  Min:     1.27 ms
  Max:     4.51 ms
  Result: single-digit millisecond latency, ready for fraud scoring
```

Other runs measured averages of 2.32 ms (min 2.11, max 4.61) and 5.63 ms (min 3.41, max 22.29).
An occasional slow lookup is normal; the average stays in single-digit milliseconds.

The events are spread over the last 100 days, so the 30-day feature window keeps about 31% of
them, with a mix of purchases, wires, disputes and chargebacks per account (about 7
disputes each in the window). Account ids run from `CTA-900000` to `CTA-900099` (synthetic, separate from the bank's
real accounts).

## Full run (laptop script)

Running `python pg_features.py` with no arguments from a laptop:

```text
1. Create raw events table:
Created bank.account_events_for_features with 10k events across 100 accounts

2. Materialize features from events:
Materialized features into bank.account_features_online
  100 accounts with computed features

3. Serve features online with measured latency:

Feature lookup latency (primary-key access):
  100 lookups across 100 accounts
  Average: 102.88 ms
  Min: 93.82 ms, Max: 204.29 ms
  ✓ Fast enough for real-time fraud scoring at authorization time

Sample feature vector for CTA-900000:
  account_id: CTA-900000
  txns_this_month: 7
  disputes_this_month: 7
  avg_anomaly_score: 4.66
  avg_util_pct: 60.00
  total_amount: 43500.00
  computed_at: 2026-10-16 01:13:48.215946+00:00

✓ Offline training in the lakehouse, online serving in Lakebase.
```

From a laptop, each lookup includes the network round trip to the workspace region, so the
average is far higher (about 100 ms in these runs). The database
time is the same; run the notebook to see it.

## The numbers that matter

| What | Expected | Why it matters |
| ---- | -------- | -------------- |
| Feature lookup latency (notebook) | about 1.5–6 ms average | fast enough for real-time fraud scoring |
| Freshness stamp | computed_at | know when the features were last updated |
| One table, 100 accounts | PRIMARY KEY | scales to millions of entities with the same pattern |

> **From the field**
> This demo materializes features in Lakebase directly. In a full pattern, you'd compute features
> in the lakehouse on historical, batch data for training, then periodically sync the latest
> features to Lakebase for serving. The lakehouse trains the model; Lakebase serves it. This journey
> shows the serving half. The LTAP journey (write-to-analytics) shows the full sync pattern.
