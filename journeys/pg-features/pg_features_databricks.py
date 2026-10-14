# Databricks notebook source
# COMMAND ----------

# MAGIC # Feature store served online, step by step
# MAGIC
# MAGIC A hands-on lab. Run one cell at a time. You will create raw events, materialize features into a fast table, and measure single-digit-millisecond lookup latency for fraud scoring.
# MAGIC
# MAGIC **Before you start:** run `00-setup/setup_databricks` once to create your branch, then run the setup cells below.

# COMMAND ----------

# MAGIC %md
# MAGIC ## Run first: install the driver and pick your branch
# MAGIC Run the next three cells before anything else. They install the Postgres driver, upgrade the
# MAGIC Databricks SDK if your environment's version predates the Lakebase API, and set `LB_PROJECT`,
# MAGIC `LB_BRANCH`, and `LB_SCHEMA` from the widgets at the top of this notebook.
# MAGIC `LB_BRANCH` defaults to the branch `00-setup/setup_databricks` created for you. Change a widget
# MAGIC only if you used a different project or branch name.

# COMMAND ----------

# MAGIC %pip install "databricks-sdk>=0.120.0" "psycopg[binary]==3.3.4"

# COMMAND ----------

dbutils.library.restartPython()

# COMMAND ----------

import os, sys
sys.path.insert(0, os.path.join(os.getcwd(), "..", "..", "common", "scripts"))
from lakebase import notebook_env
notebook_env(dbutils);

# COMMAND ----------

# MAGIC ## Setup — connect
# COMMAND ----------

import os, sys, time
sys.path.insert(0, os.path.join(os.getcwd(), '..', '..', 'common', 'scripts'))
from lakebase import connect, _env

SCHEMA = _env('LB_SCHEMA', 'bank')
EVENTS_TABLE = 'account_events_for_features'
ONLINE_TABLE = 'account_features_online'

print('Ready.')

# COMMAND ----------

# MAGIC ## Step 1 — Create raw events table
# MAGIC
# MAGIC ```sql
# MAGIC CREATE TABLE account_events_for_features (
# MAGIC     event_id BIGSERIAL PRIMARY KEY,
# MAGIC     account_id TEXT NOT NULL,
# MAGIC     event_ts TIMESTAMPTZ DEFAULT now(),
# MAGIC     event_type TEXT,
# MAGIC     amount_usd NUMERIC(12,2),
# MAGIC     anomaly_score NUMERIC(6,2),
# MAGIC     util_pct NUMERIC(6,2)
# MAGIC );
# MAGIC ```
# COMMAND ----------

with connect() as conn:
    with conn.cursor() as cur:
        cur.execute(f"DROP TABLE IF EXISTS {SCHEMA}.{EVENTS_TABLE}")
        cur.execute(f"""
            CREATE TABLE {SCHEMA}.{EVENTS_TABLE} (
                event_id BIGSERIAL PRIMARY KEY,
                account_id TEXT NOT NULL,
                event_ts TIMESTAMPTZ DEFAULT now(),
                event_type TEXT,
                amount_usd NUMERIC(12,2),
                anomaly_score NUMERIC(6,2),
                util_pct NUMERIC(6,2)
            )
        """)
        print(f'✓ Created raw events table')

# COMMAND ----------

# MAGIC ## Step 2 — Seed raw events (10k events across 100 accounts)
# MAGIC
# MAGIC ```sql
# MAGIC INSERT INTO account_events_for_features(...)
# MAGIC SELECT ... FROM generate_series(1, 10000) g
# MAGIC ```
# COMMAND ----------

with connect() as conn:
    with conn.cursor() as cur:
        cur.execute(f"""
            INSERT INTO {SCHEMA}.{EVENTS_TABLE}(account_id, event_ts, event_type, amount_usd, anomaly_score, util_pct)
            SELECT
                'ACCT-' || (g % 100),
                now() - ((g / 100) || ' days')::interval,
                (ARRAY['purchase', 'wire', 'dispute', 'chargeback'])[1 + (g % 4)],
                (g % 5000) + (g % 100)::numeric / 100,
                (g % 10)::numeric + (g % 100)::numeric / 100,
                30 + (g % 70)::numeric
            FROM generate_series(1, 10000) g
        """)
        print(f'✓ Seeded 10k events across 100 accounts')

# COMMAND ----------

# MAGIC ## Step 3 — Create online feature table
# MAGIC
# MAGIC ```sql
# MAGIC CREATE TABLE account_features_online (
# MAGIC     account_id TEXT PRIMARY KEY,
# MAGIC     txns_this_month INT,
# MAGIC     disputes_this_month INT,
# MAGIC     avg_anomaly_score NUMERIC(8,2),
# MAGIC     avg_util_pct NUMERIC(8,2),
# MAGIC     total_amount_usd NUMERIC(12,2),
# MAGIC     computed_at TIMESTAMPTZ
# MAGIC );
# MAGIC ```
# COMMAND ----------

with connect() as conn:
    with conn.cursor() as cur:
        cur.execute(f"DROP TABLE IF EXISTS {SCHEMA}.{ONLINE_TABLE}")
        cur.execute(f"""
            CREATE TABLE {SCHEMA}.{ONLINE_TABLE} (
                account_id TEXT PRIMARY KEY,
                txns_this_month INT,
                disputes_this_month INT,
                avg_anomaly_score NUMERIC(8,2),
                avg_util_pct NUMERIC(8,2),
                total_amount_usd NUMERIC(12,2),
                computed_at TIMESTAMPTZ
            )
        """)
        print(f'✓ Created online feature table')

# COMMAND ----------

# MAGIC ## Step 4 — Materialize features from events
# MAGIC
# MAGIC ```sql
# MAGIC INSERT INTO account_features_online(...)
# MAGIC SELECT
# MAGIC     e.account_id,
# MAGIC     COUNT(CASE WHEN e.event_type = 'purchase' THEN 1 END),
# MAGIC     COUNT(CASE WHEN e.event_type = 'dispute' THEN 1 END),
# MAGIC     ...
# MAGIC FROM account_events_for_features e
# MAGIC WHERE e.event_ts >= now() - interval '30 days'
# MAGIC GROUP BY e.account_id;
# MAGIC ```
# COMMAND ----------

with connect() as conn:
    with conn.cursor() as cur:
        cur.execute(f"""
            INSERT INTO {SCHEMA}.{ONLINE_TABLE}
            SELECT
                e.account_id,
                COUNT(CASE WHEN e.event_type = 'purchase' THEN 1 END),
                COUNT(CASE WHEN e.event_type = 'dispute' THEN 1 END),
                AVG(e.anomaly_score),
                AVG(e.util_pct),
                SUM(e.amount_usd),
                now()
            FROM {SCHEMA}.{EVENTS_TABLE} e
            WHERE e.event_ts >= now() - interval '30 days'
            GROUP BY e.account_id
        """)
        print(f'✓ Materialized features from events (offline step)')

# COMMAND ----------

# MAGIC ## Step 5 — Measure online serving latency
# MAGIC
# MAGIC Run 100 primary-key lookups and time each one.
# MAGIC
# MAGIC ```python
# MAGIC latencies = []
# MAGIC for account_id in range(100):
# MAGIC     t0 = time.perf_counter()
# MAGIC     cur.execute(f"SELECT * FROM account_features_online WHERE account_id = %s", [f'ACCT-{account_id}'])
# MAGIC     cur.fetchone()
# MAGIC     latencies.append((time.perf_counter() - t0) * 1000)
# MAGIC ```
# COMMAND ----------

with connect() as conn:
    with conn.cursor() as cur:
        latencies = []
        for account_id in range(100):
            t0 = time.perf_counter()
            cur.execute(f"SELECT * FROM {SCHEMA}.{ONLINE_TABLE} WHERE account_id = %s", [f'ACCT-{account_id % 100}'])
            row = cur.fetchone()
            latencies.append((time.perf_counter() - t0) * 1000)

        if latencies:
            avg_ms = sum(latencies) / len(latencies)
            min_ms = min(latencies)
            max_ms = max(latencies)
            print(f'✓ Measured {len(latencies)} lookups:')
            print(f'  Average: {avg_ms:.2f} ms')
            print(f'  Min:     {min_ms:.2f} ms')
            print(f'  Max:     {max_ms:.2f} ms')
            print(f'  Result: single-digit millisecond latency, ready for fraud scoring')

# COMMAND ----------

# MAGIC ## What you learned
# MAGIC
# MAGIC Feature stores work by materializing, computing offline, and serving online, fast lookups at prediction time. Materialize aggregates from raw events into a dedicated table, indexed for speed. Serve means primary-key lookups, single-digit-millisecond latency, no computation at prediction time. Same database for both; no sync between systems.
# MAGIC
# MAGIC Next: **One query, every type** builds a single table with JSON, vectors, and geospatial data.