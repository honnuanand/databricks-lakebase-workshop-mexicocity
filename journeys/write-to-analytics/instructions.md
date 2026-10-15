# Write to analytics, instructions

## How to run this journey

There are a few ways to work through the steps. Pick one:

- **Notebook, step by step (recommended for learning):** open [`write_to_analytics.ipynb`](write_to_analytics.ipynb) and run one cell at a time. Reading each result before the next step is where the learning happens.
- **In a Databricks workspace:** import [`write_to_analytics_databricks.py`](write_to_analytics_databricks.py) and run it cell by cell there.
- **By hand:** follow the numbered steps below, copying each command yourself.
- **Just see it work:** run `python write_to_analytics.py` from this folder to execute the whole thing at once. Fast, but you learn the most from the notebook.

Run these on your own branch. If you haven't done [`../../00-setup/`](../../00-setup/), do that first; you need `LB_PROFILE`, `LB_PROJECT`, `LB_BRANCH`, and `LB_SCHEMA` set.

The operational round trip (write, score, write back, read) runs live on your branch. The
lakehouse read of the same rows is an explainer (it needs the database registered as a Unity
Catalog catalog, a metastore-admin action), so the script shows that query rather than faking it.

Everything here is a single script you can read: [`./write_to_analytics.py`](./write_to_analytics.py).
You can run it end to end, or follow the steps by hand to see each piece.

## Run it end to end

```bash
cd journeys/write-to-analytics
python write_to_analytics.py
```

Read on for what each step does; the exact output to expect is in [`expected.md`](expected.md).

## Or step through it by hand

### Step 1, write a transaction through Lakebase (OLTP)

Insert a new transaction, a MXN 38,500 SPEI transfer from CTA-100240 with a high anomaly score:

```bash
python write_to_analytics.py --step write
```

The script runs:

```sql
INSERT INTO bank.txn (account_id, ts, amount, channel, anomaly_score, mcc, util_pct)
VALUES ('CTA-100240', now(), 38500.00, 'SPEI', 8.7, NULL, 92.0)
RETURNING txn_id;
```

A millisecond operational write. The script keeps the new `txn_id`.

### Step 2, compute a fraud-risk score and write it back

Score the transaction from its anomaly score and the account's utilization, and write the score
back onto the same row:

```bash
python write_to_analytics.py --step score
```

The script runs:

```sql
UPDATE bank.txn
SET fraud_risk = ROUND(100 * (anomaly_score / 10.0 + util_pct / 100.0), 1)
WHERE txn_id = <the id from step 1>;
```

Then reads the row back. The operational path now serves an analytics-derived value (`fraud_risk`)
at transaction latency.

### Step 3, the lakehouse read (explainer)

The full run prints the exact query you would run on a SQL warehouse to read the same rows from
the lakehouse, once the database is registered as a Unity Catalog online catalog:

```sql
SELECT account_id, ts, amount, anomaly_score, fraud_risk
FROM <catalog>.bank.txn
WHERE account_id = 'CTA-100240' ORDER BY ts DESC LIMIT 1;
```

The transaction you wrote in Step 1 appears there immediately, the same copy, no pipeline.
Registering the catalog needs CREATE CATALOG on the metastore (see [`faq.md`](faq.md)); the
workshop shows the query rather than faking its output.

### Step 6, read the score from Postgres

Query Postgres to confirm the risk score is now there:

```bash
python ../../common/scripts/lakebase.py --sql \
  "SELECT account_id, ts, amount, anomaly_score, fraud_risk FROM bank.txn WHERE account_id='CTA-100240' ORDER BY ts DESC LIMIT 1"
```

The most recent transaction now has the fraud-risk score, computed on the lakehouse, written back to Postgres.

## What you just did

You wrote a sensor reading through Postgres, read it immediately from the lakehouse foreign table (no CDC), computed a risk score, and wrote it back, all on one copy of the data. Compare the timings you saw against [`expected.md`](expected.md), and if anything went sideways, [`faq.md`](faq.md) has the common causes and the read-only alternatives.
