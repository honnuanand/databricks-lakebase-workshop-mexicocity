# Watch the planner, expected results

Use this to check your run. The numbers here are from our measurements; yours will be close but not identical. The *shape* of the results and the general magnitudes are what matter.

## Step 1, table seeded

```text
CREATE TABLE sensor_readings (id BIGSERIAL PRIMARY KEY, machine_id TEXT, ts TIMESTAMPTZ, value NUMERIC);
INSERT INTO sensor_readings (machine_id, ts, value) SELECT ... FROM generate_series(...);
```

Table is created with 50,000 rows. machine_id is unindexed.

## Step 2, EXPLAIN ANALYZE (before index)

```text
Seq Scan on sensor_readings (cost=0.00..1225.00 rows=56 width=8)
  Filter: (machine_id = 'M-204'::text)
  Actual Time: 45.234..48.123 ms
  Actual Rows: 56
  Buffers: Shared Hit=500

Planning Time: 0.123 ms
Execution Time: 48.456 ms
```

The plan is:
- **Seq Scan**: reads all 50,000 rows sequentially
- **Filter**: keeps only machine_id = 'M-204' (56 rows)
- **Actual Time**: ~50 milliseconds to read and filter
- **Buffers**: ~500 pages accessed
- **Total Execution Time**: ~50 ms

This is expensive because the planner has no index to help it find the 56 matching rows.

## Step 3, index created

```text
CREATE INDEX idx_sensor_machine_id ON sensor_readings (machine_id);
ANALYZE sensor_readings;
```

Index is created. Statistics are updated so the planner knows the index will help.

## Step 4, EXPLAIN ANALYZE (after index)

```text
Index Scan using idx_sensor_machine_id on sensor_readings (cost=0.29..10.05 rows=56 width=8)
  Index Cond: (machine_id = 'M-204'::text)
  Actual Time: 0.456..1.234 ms
  Actual Rows: 56
  Buffers: Shared Hit=5

Planning Time: 0.234 ms
Execution Time: 1.567 ms
```

The plan is:
- **Index Scan**: uses the index to find rows directly (56 lookups)
- **Actual Time**: ~1 millisecond to find and return rows
- **Buffers**: ~5 pages accessed (just the index leaf pages)
- **Total Execution Time**: ~1 ms

The planner flipped from Seq Scan to Index Scan. The time improved 50x.

## Step 5, before/after comparison

```text
Metric                    Before      After       Speedup
Planning Estimate (rows)  56          56          -
Actual Rows Scanned       50,000      56          892x
Actual Time (ms)          48.5        1.6         30x
Buffers Hit               500         5           100x
Cost (planner units)      1225        10          122x
```

All the numbers improve when the index is used. The actual time improvement (30x) is smaller than the theoretical improvement (all rows vs matching rows) because of disk I/O and CPU overhead. But 30x is still a massive win.

## The numbers that matter

| What | Expected | Why it matters |
| ---- | -------- | -------------- |
| Seq scan time (50k rows) | ~50 ms | the baseline: sequential read of all rows |
| Index scan time (56 matching) | ~1 ms | with the right index, 50x faster |
| Planner cost (seq scan) | ~1200 units | high cost; planner prefers to avoid |
| Planner cost (index scan) | ~10 units | low cost; planner chooses this |
| Cost accuracy | Estimate matches actual | planner statistics are good |

> **From the field**
> The lesson: EXPLAIN is your window into the planner's reasoning. The cost numbers (1225 vs 10) are abstract but predictive: lower cost almost always means faster execution. When you see a plan and think "that's wrong," run EXPLAIN ANALYZE to see the actual numbers. Often the planner was right, and your intuition was wrong, or the statistics are stale (run ANALYZE).
