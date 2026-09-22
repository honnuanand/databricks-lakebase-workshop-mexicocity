# Write to analytics, expected results

Use this to check your run. Timings are from measurements in a live workspace; yours will be close. The *shape* is what matters: millisecond OLTP writes, immediate lakehouse visibility, analytics compute, and write-back, all on one copy.

## Step 1, baseline sensor data

```text
('M-204', 2026-09-22 14:31:00+00:00, 64.0, 3.8)
('M-204', 2026-09-22 14:26:00+00:00, 63.1, 2.4)
('M-204', 2026-09-22 14:21:00+00:00, 62.5, 2.1)
```

Baseline readings already on Postgres.

## Step 2, write new reading

```text
  inserted: ts=2026-09-22 14:35:23+00:00, temp_c=67.3, vibration_mm_s=4.2
```

The INSERT is fast (milliseconds). The script captures the exact timestamp to measure end-to-end latency.

## Step 3, read from lakehouse (forward-ETL)

If UC and warehouse are available:

```text
  created external table: factory_sensor_reading_foreign (maps to Lakebase sensor_reading)
  queried lakehouse warehouse (warm): 1.2s wall-clock
  result: ('M-204', 2026-09-22 14:35:23+00:00, 67.3, 4.2)
```

The row appears in the lakehouse immediately. The 1.2s is warehouse query planning + execution, not sync lag. If you query again, it's faster (warehouse cache).

If UC is not available, the script shows the SQL and skips execution:

```text
  (Unity Catalog not configured; showing SQL only)
  SELECT ... FROM foreign_table_sensor_reading WHERE machine_id = 'M-204' ORDER BY ts DESC LIMIT 1
```

## Step 4, compute score (analytics)

```text
  failure_risk_pct = 71.2
```

A simulated analytics query computes a risk score (here, 71.2% risk of failure in the next hour based on vibration + temperature). In a real scenario, this is a complex ML model or aggregation query running on the lakehouse warehouse.

## Step 5, write score back (reverse-ETL)

```text
  updated sensor_reading row: machine_id='M-204', failure_risk_pct=71.2
  write latency: 45 ms
```

The write is direct to Postgres (not through the foreign table, which is read-only). It's a normal INSERT or UPDATE.

## Step 6, read score from Postgres

```text
('M-204', 2026-09-22 14:35:23+00:00, 67.3, 4.2, failure_risk_pct=71.2)
```

The risk score is now visible on Postgres. The MES system can use it to route new work away from risky machines.

## Full run

Running `python write_to_analytics.py` with no arguments:

```text
1. Baseline sensor data on Postgres:
  ('M-204', ..., 64.0, 3.8)
  ('M-204', ..., 63.1, 2.4)
  ('M-204', ..., 62.5, 2.1)
2. Write a new sensor reading through Postgres:
  inserted: ts=2026-09-22 14:35:23+00:00, temp_c=67.3, vibration_mm_s=4.2
3. Read from lakehouse (forward-ETL, no CDC):
  created external table: factory_sensor_reading_foreign
  queried lakehouse warehouse: 1.2s wall-clock
  result: ('M-204', ..., 67.3, 4.2)  [SAME ROW, SAME MOMENT]
4. Compute risk score on lakehouse analytics:
  failure_risk_pct = 71.2
5. Write score back to Postgres (reverse-ETL):
  updated sensor_reading row: failure_risk_pct=71.2
  write latency: 45 ms
6. Read score from Postgres (MES system can use it):
  ('M-204', ..., 67.3, 4.2, failure_risk_pct=71.2)
Done. One copy, both engines, round-trip closed.
```

## The numbers that matter

| What | Expected | Why it matters |
| ---- | -------- | -------------- |
| OLTP write latency | ~1–5 ms | Postgres ACID write, no pipeline overhead |
| Lakehouse query latency | ~1–2 sec (first run) | warehouse planning + execution, not sync lag |
| Lakehouse query latency (warm cache) | ~200–500 ms | warehouse serving from cache |
| Reverse write latency | ~10–50 ms | direct Postgres write, not a pipeline |
| Read from Postgres (after reverse write) | ~1 ms | local read |

> **From the field**
> The end-to-end latency is dominated by the analytics query warehouse planning (warm warehouses are faster than cold ones). The writes themselves are milliseconds. The key insight: there's no "sync pipeline latency" because there's no pipeline, the foreign table is a live query, not a replicated snapshot. If someone tells you "we sync data every 5 minutes," that's 300,000 ms of delay baked in. This path is order-of-magnitude faster.
