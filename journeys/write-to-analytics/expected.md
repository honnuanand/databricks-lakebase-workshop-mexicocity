# One copy, both directions, expected results

The write, the score, and the write-back run live on your branch. The lakehouse read is an
explainer (it needs a Unity Catalog catalog registration, a metastore-admin action), so there is
no live output for that step; you see the query you would run.

## Step 1, write a transaction through Lakebase

```text
  inserted txn_id=11: amount=38500.00, anomaly_score=8.70
```

Your `txn_id` will differ. The row is a real INSERT on your branch, a MXN 38,500 SPEI transfer on
CTA-100240 with a high anomaly score.

## Step 2, compute and write back the fraud score

```text
  scored + wrote back: (11, 'CTA-100240', Decimal('38500.00'), Decimal('8.70'), Decimal('92.00'), Decimal('179.0'))
```

The fraud_risk is `ROUND(100 * (anomaly_score/10 + util_pct/100), 1)` = `ROUND(100*(0.87+0.92),1)`
= `179.0`. It is computed and written back onto the same row, then read straight back.

## Step 3, the lakehouse explainer

There is no live output here on purpose. You see the query to run once the database is registered
in Unity Catalog:

```sql
SELECT account_id, ts, amount, anomaly_score, fraud_risk
FROM <catalog>.bank.txn
WHERE account_id = 'CTA-100240' ORDER BY ts DESC LIMIT 1;
```

## The numbers that matter

| What | Expected | Why it matters |
| ---- | -------- | -------------- |
| OLTP write | real INSERT, single-digit ms | operational write on the live branch |
| fraud_risk | 179.0 for anomaly 8.7 / util 92 | analytics value computed and stored |
| write-back + read | real UPDATE then SELECT | the authorization path serves the derived value |
| lakehouse read | explainer, not run | needs a UC catalog registration (admin) |

> **Note**
> This journey is deliberately honest about the split. The operational round trip is fully live.
> The lakehouse read of the same rows is real in a full setup (a Unity Catalog online catalog over
> the Lakebase database, queried from a SQL warehouse), but registering that catalog needs
> CREATE CATALOG on the metastore, which a workshop learner usually will not have. So the workshop
> shows the exact query rather than faking its output. If you do have a registered catalog, run the
> Step 3 query on a SQL warehouse and you will see the transaction you just wrote, the same copy,
> no pipeline.
