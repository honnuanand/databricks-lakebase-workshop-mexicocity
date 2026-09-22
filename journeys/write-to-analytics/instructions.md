# Write to analytics, instructions

Run these on your own branch. If you haven't done [`../../00-setup/`](../../00-setup/), do that first; you need `LB_PROFILE`, `LB_PROJECT`, `LB_BRANCH`, and `LB_SCHEMA` set.

This journey combines Postgres operations with Databricks workspace integration. You'll need a Unity Catalog and a SQL warehouse to run the full end-to-end. If you don't, the script will walk you through the forward path (write → read via foreign table) and show you where the reverse path (analytics → write back) happens.

Everything here is a single script you can read: [`../../common/scripts/write_to_analytics.py`](../../common/scripts/write_to_analytics.py).
You can run it end to end, or follow the steps by hand to see each piece.

## Run it end to end

```bash
cd common/scripts
python write_to_analytics.py
```

The script checks your workspace setup, walks the forward path (write through Postgres, read from lakehouse), and optionally walks the reverse path if you have warehouse permission. Read on for what each step does; the exact output to expect is in [`expected.md`](expected.md).

## Or step through it by hand

### Step 1, establish baseline sensor data

Confirm sensor_reading has a few baseline readings on Postgres:

```bash
python lakebase.py --sql \
  "SELECT machine_id, ts, temp_c, vibration_mm_s FROM factory.sensor_reading WHERE machine_id='M-204' ORDER BY ts DESC LIMIT 3"
```

You'll see recent readings from M-204. This is your baseline.

### Step 2, write a new sensor reading through Postgres

Insert a new reading (simulating a live sensor report):

```bash
python write_to_analytics.py --step write
```

The script runs:

```sql
INSERT INTO factory.sensor_reading (machine_id, ts, temp_c, vibration_mm_s, rpm, load_pct)
VALUES ('M-204', now(), 67.3, 4.2, 1165, 81.0);
```

The script captures the insert timestamp.

### Step 3, query from the lakehouse immediately

The forward-ETL path requires a foreign table. If you have a Unity Catalog set up, the script will:
- Create a managed external table in UC that maps to the sensor_reading table
- Run a lakehouse SQL query against that table
- Show the new row visible in the foreign table

```bash
python write_to_analytics.py --step read-forward
```

If you don't have UC or warehouse permission, the script will show you the SQL and skip execution.

### Step 4, compute a risk score on the lakehouse

Analytics runs a simulated query to compute a failure-risk score based on recent vibration and temperature trends:

```bash
python write_to_analytics.py --step compute-score
```

The script runs (or shows) a query like:

```sql
SELECT machine_id, 
       ROUND(100 * (vibration_mm_s / 10.0 + temp_c / 100.0), 1) AS failure_risk_pct
FROM sensor_reading
WHERE machine_id = 'M-204' AND ts > now() - interval '1 hour'
```

The result is a failure_risk_pct value.

### Step 5, write the score back to Postgres

The reverse-ETL path writes the computed score back to the sensor_reading table (or a separate risk_score table if you prefer):

```bash
python write_to_analytics.py --step write-reverse
```

The script updates the sensor_reading row with a computed failure_risk field (or creates a separate risk_score row).

### Step 6, read the score from Postgres

Query Postgres to confirm the risk score is now there:

```bash
python lakebase.py --sql \
  "SELECT machine_id, ts, temp_c, vibration_mm_s FROM factory.sensor_reading WHERE machine_id='M-204' ORDER BY ts DESC LIMIT 1"
```

The most recent reading now has the risk score, computed on the lakehouse, written back to Postgres.

## What you just did

You wrote a sensor reading through Postgres, read it immediately from the lakehouse foreign table (no CDC), computed a risk score, and wrote it back, all on one copy of the data. Compare the timings you saw against [`expected.md`](expected.md), and if anything went sideways, [`faq.md`](faq.md) has the common causes and the read-only alternatives.
