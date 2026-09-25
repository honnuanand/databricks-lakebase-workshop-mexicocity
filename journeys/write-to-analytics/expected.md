# One copy, both directions, expected results

The write, the score, and the write-back run live on your branch. The lakehouse read is an
explainer (it needs a Unity Catalog catalog registration, a metastore-admin action), so there is
no live output for that step; you see the query you would run.

## Step 1, write a reading through Postgres

```text
  inserted reading_id=12: temp_c=67.3, vibration_mm_s=4.2
```

Your `reading_id` will differ. The row is a real INSERT on your branch.

## Step 2, compute and write back the risk score

```text
  scored + wrote back: (12, 'M-204', Decimal('67.30'), Decimal('4.20'), Decimal('109.3'))
```

The failure_risk is `ROUND(100 * (vibration_mm_s/10 + temp_c/100), 1)` = `ROUND(100*(0.42+0.673),1)`
= `109.3`. It is computed and written back onto the same row, then read straight back.

## Step 3, the lakehouse explainer

There is no live output here on purpose. You see the query to run once the database is registered
in Unity Catalog:

```sql
SELECT machine_id, ts, temp_c, vibration_mm_s, failure_risk
FROM <catalog>.factory.sensor_reading
WHERE machine_id = 'M-204' ORDER BY ts DESC LIMIT 1;
```

## The numbers that matter

| What | Expected | Why it matters |
| ---- | -------- | -------------- |
| OLTP write | real INSERT, single-digit ms | operational write on the live branch |
| failure_risk | 109.3 for temp 67.3 / vib 4.2 | analytics value computed and stored |
| write-back + read | real UPDATE then SELECT | the operational side serves the derived value |
| lakehouse read | explainer, not run | needs a UC catalog registration (admin) |

> **Note**
> This journey is deliberately honest about the split. The operational round trip is fully live.
> The lakehouse read of the same rows is real in a full setup (a Unity Catalog online catalog over
> the Lakebase database, queried from a SQL warehouse), but registering that catalog needs
> CREATE CATALOG on the metastore, which a workshop learner usually will not have. So the workshop
> shows the exact query rather than faking its output. If you do have a registered catalog, run
> the Step 3 query on a SQL warehouse and you will see the row you just wrote, the same copy, no
> pipeline.
