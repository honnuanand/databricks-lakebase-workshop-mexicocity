# Feature store, served online, expected results

Use this to check your run. Numbers are representative; latencies vary with network and instance load.
The shape is what matters: single-digit milliseconds for primary-key lookups.

## Setup

```text
Created machine_events_for_features with 10k events across 100 machines
```

## Materialize features

```text
Materialized features into machine_features_online
  100 machines with computed features
```

One row per machine, with aggregated statistics and a `computed_at` timestamp.

## Serve online

```text
Feature lookup latency (primary-key access):
  100 lookups across 10 machines
  Average: 2.50 ms
  Min: 1.20 ms, Max: 5.80 ms
  ✓ Fast enough for real-time model inference

Sample feature vector for M-0:
  machine_id: M-0
  runs_this_month: 45
  failures_this_month: 2
  avg_temp_c: 68.34
  avg_vibration_mm_s: 45.67
  total_cycles: 8920
  computed_at: 2026-09-22 15:30:45.123456+00
```

The feature vector the model receives at inference is a single database row, served in milliseconds.

## Full run

```text
1. Create raw events table:
Created machine_events_for_features with 10k events across 100 machines

2. Materialize features from events:
Materialized features into machine_features_online
  100 machines with computed features

3. Serve features online with measured latency:
Feature lookup latency (primary-key access):
  100 lookups across 10 machines
  Average: 2.50 ms
  Min: 1.20 ms, Max: 5.80 ms
  ✓ Fast enough for real-time model inference

Sample feature vector for M-0:
  machine_id: M-0
  runs_this_month: 45
  failures_this_month: 2
  avg_temp_c: 68.34
  avg_vibration_mm_s: 45.67
  total_cycles: 8920
  computed_at: 2026-09-22 15:30:45.123456+00

✓ Offline training in the lakehouse, online serving in Lakebase.
```

## The numbers that matter

| What | Expected | Why it matters |
| ---- | -------- | -------------- |
| Feature lookup latency | 2-5 ms | Fast enough for real-time inference (model calls this service) |
| Latency consistency | <10 ms p99 | No surprises; predictable service times |
| Freshness stamp | computed_at | Know when the features were last updated |
| One table, 100 machines | PRIMARY KEY | Scales to millions of entities with the same pattern |

> **From the field**
> This demo materializes features in Lakebase directly. In a full pattern, you'd compute features
> in the lakehouse (on historical, batch data for training), then periodically sync the latest
> features to Lakebase for serving. The lakehouse trains the model; Lakebase serves it. This journey
> shows the serving half. The LTAP journey (write-to-analytics) shows the full sync pattern.
