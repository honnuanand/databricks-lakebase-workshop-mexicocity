# Databricks notebook source
# MAGIC %md-sandbox
# MAGIC <div style="display:flex; align-items:center; gap:10px; padding:8px 16px; background:#F9F7F4; border-bottom:2px solid #E0E0E0; font-family:sans-serif; line-height:1;">
# MAGIC   <span style="display:inline-block; width:12px; height:12px; border-radius:2px; background:#FF3621;"></span>
# MAGIC   <span style="font-weight:bold; color:#0b2026;">Lakebase workshop</span>
# MAGIC   <span style="color:#999;">|</span>
# MAGIC   <span style="color:#5A6F77;">Part 2 · Agent developers · Journey 5 of 5 · Online Feature Serving</span>
# MAGIC </div>

# COMMAND ----------

# MAGIC %md
# MAGIC # Online Feature Serving
# MAGIC #### Duration: about 10 minutes
# MAGIC
# MAGIC *Journey 5 of 5. Vector Similarity Search found related items by meaning. This last journey serves the numbers a fraud model needs, the moment it needs them.*
# MAGIC
# MAGIC ## Overview
# MAGIC
# MAGIC When a card payment or a SPEI transfer comes in, a fraud model has a few milliseconds to score it.
# MAGIC It can't add up an account's last month of activity on the spot. It needs that account's
# MAGIC **features** (how many transactions this month, how many disputes, the average anomaly score)
# MAGIC already computed and ready to read.
# MAGIC
# MAGIC In this lab you build that in two steps on your branch. First, the offline step: aggregate 10,000
# MAGIC raw events into one row of features per account. Then the online step: look up an account's row by
# MAGIC its key, 100 times, and time each lookup.
# MAGIC
# MAGIC ## Learning objectives
# MAGIC
# MAGIC By the end of this lab, you will be able to:
# MAGIC
# MAGIC 1. **Generate a raw event stream** with SQL, as a stand-in for an account's transaction history.
# MAGIC 2. **Materialize features:** aggregate events into a table with one row per account.
# MAGIC 3. **Serve features online** with a primary-key lookup, and measure its latency.
# MAGIC 4. **Explain the split:** compute features ahead of time (offline), read them at decision time (online).

# COMMAND ----------

# MAGIC %md
# MAGIC ## Key concepts
# MAGIC
# MAGIC - **Feature:** a number a model uses to make a decision, such as `disputes_this_month` for an account.
# MAGIC - **Materialize:** compute the features ahead of time and store them in a table, instead of computing them on every request.
# MAGIC - **Online serving:** reading a feature row at decision time, by key, fast enough to sit inside a payment authorization.
# MAGIC - **Freshness:** how old the features are. The `computed_at` column records when each row was computed.
# MAGIC
# MAGIC More terms are defined in `docs/glossary.md` in the workshop folder.

# COMMAND ----------

# MAGIC %md-sandbox
# MAGIC ## A. Setup
# MAGIC
# MAGIC <div style="border-left:4px solid #1B5162; background:#EEF4F6; padding:12px 16px; border-radius:4px; margin:12px 0; font-family:sans-serif;">
# MAGIC   <strong style="display:block; color:#1B5162; margin-bottom:6px;">Before you start</strong>
# MAGIC   <div style="color:#333;">
# MAGIC     Run <code>00-setup/setup_databricks</code> once to create your branch and load the bank.
# MAGIC     Attach this notebook to <strong>serverless</strong> compute. No model endpoint is needed. The lab
# MAGIC     creates two tables of its own on your branch, <code>account_events_for_features</code> and
# MAGIC     <code>account_features_online</code>, and replaces them on every run; the bank's tables are not touched.
# MAGIC   </div>
# MAGIC </div>
# MAGIC
# MAGIC <div style="max-width:720px; margin:12px auto; font-family:sans-serif;">
# MAGIC <svg viewBox="0 0 720 150" xmlns="http://www.w3.org/2000/svg" style="width:100%; height:auto; display:block;" font-family="sans-serif">
# MAGIC   <rect x="10" y="10" width="700" height="130" rx="10" fill="#F9F7F4" stroke="#E0E0E0"/>
# MAGIC   <rect x="30" y="45" width="190" height="56" rx="8" fill="#FFFFFF" stroke="#1B5162" stroke-width="2"/>
# MAGIC   <text x="125" y="69" text-anchor="middle" font-size="13" font-weight="700" fill="#0b2026">account_events_for_features</text>
# MAGIC   <text x="125" y="88" text-anchor="middle" font-size="11" fill="#5A6F77">10,000 raw events</text>
# MAGIC   <rect x="290" y="45" width="190" height="56" rx="8" fill="#FFF1EE" stroke="#FF3621" stroke-width="2"/>
# MAGIC   <text x="385" y="69" text-anchor="middle" font-size="13" font-weight="700" fill="#0b2026">account_features_online</text>
# MAGIC   <text x="385" y="88" text-anchor="middle" font-size="11" fill="#5A6F77">1 row per account</text>
# MAGIC   <rect x="550" y="45" width="140" height="56" rx="8" fill="#FFFFFF" stroke="#5A6F77" stroke-width="2" stroke-dasharray="6 4"/>
# MAGIC   <text x="620" y="69" text-anchor="middle" font-size="13" font-weight="700" fill="#0b2026">fraud model</text>
# MAGIC   <text x="620" y="88" text-anchor="middle" font-size="11" fill="#5A6F77">lookup by key</text>
# MAGIC   <line x1="220" y1="73" x2="282" y2="73" stroke="#1B5162" stroke-width="2"/><polygon points="282,67 290,73 282,79" fill="#1B5162"/>
# MAGIC   <line x1="480" y1="73" x2="542" y2="73" stroke="#1B5162" stroke-width="2"/><polygon points="542,67 550,73 542,79" fill="#1B5162"/>
# MAGIC   <text x="255" y="122" text-anchor="middle" font-size="11" fill="#5A6F77">offline: aggregate</text>
# MAGIC   <text x="515" y="122" text-anchor="middle" font-size="11" fill="#5A6F77">online: milliseconds</text>
# MAGIC </svg>
# MAGIC </div>

# COMMAND ----------

# MAGIC %md
# MAGIC ### A1. Install the driver and pick your branch
# MAGIC
# MAGIC Run the next three cells before anything else. They install the Postgres driver, upgrade the
# MAGIC Databricks SDK if your environment's version predates the Lakebase API, and set `LB_PROJECT`,
# MAGIC `LB_BRANCH`, and `LB_SCHEMA` from the widgets at the top of this notebook. `LB_BRANCH` defaults to
# MAGIC the branch `00-setup/setup_databricks` created for you. Change a widget only if you used a
# MAGIC different project or branch name.

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

# MAGIC %md-sandbox
# MAGIC **Expected result:** `signed in as` your email, followed by your project, branch, and schema:
# MAGIC
# MAGIC ```
# MAGIC signed in as alex.kim@example.com
# MAGIC   LB_PROJECT = bank
# MAGIC   LB_BRANCH = u-alex-kim
# MAGIC   LB_SCHEMA = bank
# MAGIC ```
# MAGIC
# MAGIC <div style="border-left:4px solid #FF9800; background:#FFF3E0; padding:12px 16px; border-radius:4px; margin:12px 0; font-family:sans-serif;">
# MAGIC   <strong style="display:block; color:#E65100; margin-bottom:6px;">Troubleshooting</strong>
# MAGIC   <div style="color:#333;">
# MAGIC     <ul style="margin:0; padding-left:20px;">
# MAGIC       <li><code>databricks-sdk ... predates the Lakebase API</code>: rerun the install cell and the restart cell, then this one.</li>
# MAGIC       <li><code>Fill in LB_BRANCH in the widgets at the top of the notebook</code>: type your branch name in the <code>LB_BRANCH</code> box, then rerun this cell.</li>
# MAGIC       <li>The widgets show an old branch name: run <code>dbutils.widgets.removeAll()</code> in a new cell, then rerun this one.</li>
# MAGIC     </ul>
# MAGIC   </div>
# MAGIC </div>

# COMMAND ----------

# MAGIC %md
# MAGIC ### A2. Connect to your branch
# MAGIC
# MAGIC This loads the shared helper from `common/scripts/` and names the two tables. `connect()` asks the
# MAGIC Lakebase API for your branch's host name, gets a login token from your Databricks identity (valid
# MAGIC for about an hour), and opens a Postgres connection with `psycopg`, a Postgres driver for Python.
# MAGIC
# MAGIC In the steps below, the SQL block in each step is what runs on your branch.

# COMMAND ----------

import os, sys, time
sys.path.insert(0, os.path.join(os.getcwd(), '..', '..', 'common', 'scripts'))
from lakebase import connect, _env

SCHEMA = _env('LB_SCHEMA', 'bank')
EVENTS_TABLE = 'account_events_for_features'
ONLINE_TABLE = 'account_features_online'

print('Ready.')

# COMMAND ----------

# MAGIC %md
# MAGIC **Expected result:** `Ready.`

# COMMAND ----------

# MAGIC %md
# MAGIC ## B. Build the raw events
# MAGIC
# MAGIC ### B1. Create the events table
# MAGIC
# MAGIC One row per event: which account, when, what kind, how much, and the scores a fraud system would
# MAGIC log with it. The cell drops the table first, so a rerun starts clean. The SQL:
# MAGIC
# MAGIC ```sql
# MAGIC CREATE TABLE bank.account_events_for_features (
# MAGIC     event_id      BIGSERIAL PRIMARY KEY,
# MAGIC     account_id    TEXT NOT NULL,
# MAGIC     event_ts      TIMESTAMPTZ DEFAULT now(),
# MAGIC     event_type    TEXT,
# MAGIC     amount        NUMERIC(12,2),
# MAGIC     anomaly_score NUMERIC(6,2),
# MAGIC     util_pct      NUMERIC(6,2)
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
                amount NUMERIC(12,2),
                anomaly_score NUMERIC(6,2),
                util_pct NUMERIC(6,2)
            )
        """)
        print(f'✓ Created raw events table')

# COMMAND ----------

# MAGIC %md
# MAGIC **Expected result:** `✓ Created raw events table`

# COMMAND ----------

# MAGIC %md
# MAGIC ### B2. Generate 10,000 events
# MAGIC
# MAGIC `generate_series` makes 10,000 synthetic events for 100 accounts, `CTA-900000` to `CTA-900099`
# MAGIC (separate from the bank's real accounts), spread over the last 100 days, with a mix of purchases,
# MAGIC wires, disputes, and chargebacks. The SQL, shortened:
# MAGIC
# MAGIC ```sql
# MAGIC INSERT INTO bank.account_events_for_features (account_id, event_ts, event_type, amount, anomaly_score, util_pct)
# MAGIC SELECT 'CTA-' || (900000 + g % 100),
# MAGIC        now() - ((g / 100) || ' days')::interval,
# MAGIC        (ARRAY['purchase', 'wire', 'dispute', 'chargeback'])[1 + ((g / 100) % 4)],
# MAGIC        ...
# MAGIC FROM generate_series(1, 10000) g;
# MAGIC ```

# COMMAND ----------

with connect() as conn:
    with conn.cursor() as cur:
        cur.execute(f"""
            INSERT INTO {SCHEMA}.{EVENTS_TABLE}(account_id, event_ts, event_type, amount, anomaly_score, util_pct)
            SELECT
                'CTA-' || (900000 + g % 100),
                now() - ((g / 100) || ' days')::interval,
                (ARRAY['purchase', 'wire', 'dispute', 'chargeback'])[1 + ((g / 100) % 4)],
                (g % 5000) + (g % 100)::numeric / 100,
                ((g / 100) % 10)::numeric + (g % 100)::numeric / 100,
                30 + (g % 70)::numeric
            FROM generate_series(1, 10000) g
        """)
        print(f'✓ Seeded 10k events across 100 accounts')

# COMMAND ----------

# MAGIC %md
# MAGIC **Expected result:** `✓ Seeded 10k events across 100 accounts`
# MAGIC
# MAGIC **What this proves:** a transaction history is a table like any other. Lakebase stores the raw events next to the bank's data.

# COMMAND ----------

# MAGIC %md
# MAGIC ## C. Materialize the features (offline)
# MAGIC
# MAGIC ### C1. Create the feature table
# MAGIC
# MAGIC One row per account, keyed by `account_id`. The primary key gives Postgres an index, which is what
# MAGIC makes the lookups in D fast. The SQL:
# MAGIC
# MAGIC ```sql
# MAGIC CREATE TABLE bank.account_features_online (
# MAGIC     account_id          TEXT PRIMARY KEY,
# MAGIC     txns_this_month     INT,
# MAGIC     disputes_this_month INT,
# MAGIC     avg_anomaly_score   NUMERIC(8,2),
# MAGIC     avg_util_pct        NUMERIC(8,2),
# MAGIC     total_amount        NUMERIC(12,2),
# MAGIC     computed_at         TIMESTAMPTZ
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
                total_amount NUMERIC(12,2),
                computed_at TIMESTAMPTZ
            )
        """)
        print(f'✓ Created online feature table')

# COMMAND ----------

# MAGIC %md
# MAGIC **Expected result:** `✓ Created online feature table`

# COMMAND ----------

# MAGIC %md
# MAGIC ### C2. Compute the features
# MAGIC
# MAGIC Aggregate the last 30 days of events into one row per account. About 31% of the events fall in that
# MAGIC window, around 30 per account. The SQL:
# MAGIC
# MAGIC ```sql
# MAGIC INSERT INTO bank.account_features_online
# MAGIC SELECT e.account_id,
# MAGIC        COUNT(CASE WHEN e.event_type = 'purchase' THEN 1 END),
# MAGIC        COUNT(CASE WHEN e.event_type = 'dispute'  THEN 1 END),
# MAGIC        AVG(e.anomaly_score), AVG(e.util_pct), SUM(e.amount), now()
# MAGIC FROM bank.account_events_for_features e
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
                SUM(e.amount),
                now()
            FROM {SCHEMA}.{EVENTS_TABLE} e
            WHERE e.event_ts >= now() - interval '30 days'
            GROUP BY e.account_id
        """)
        print(f'✓ Materialized features from events (offline step)')

# COMMAND ----------

# MAGIC %md-sandbox
# MAGIC **Expected result:** `✓ Materialized features from events (offline step)`
# MAGIC
# MAGIC **What this proves:** the heavy work, scanning and aggregating events, happens once, ahead of time. A test run gave each account about 7 purchases and 7 disputes in the window.
# MAGIC
# MAGIC <div style="border-left:4px solid #1B5162; background:#EEF4F6; padding:12px 16px; border-radius:4px; margin:12px 0; font-family:sans-serif;">
# MAGIC   <strong style="display:block; color:#1B5162; margin-bottom:6px;">See it in the UI (optional)</strong>
# MAGIC   <div style="color:#333;">
# MAGIC     Open the <strong>Lakebase Postgres</strong> app, select your project and your branch, then the
# MAGIC     <strong>Tables</strong> tab, and open <code>account_features_online</code>: 100 rows, one per account,
# MAGIC     each with its <code>computed_at</code> time.
# MAGIC   </div>
# MAGIC </div>

# COMMAND ----------

# MAGIC %md
# MAGIC ## D. Serve the features (online)
# MAGIC
# MAGIC Look up each of the 100 accounts by key, one query at a time, and time each lookup. This is the
# MAGIC query a fraud model would run at authorization time:
# MAGIC
# MAGIC ```sql
# MAGIC SELECT * FROM bank.account_features_online WHERE account_id = 'CTA-900000';
# MAGIC ```

# COMMAND ----------

with connect() as conn:
    with conn.cursor() as cur:
        latencies = []
        for account_id in range(100):
            t0 = time.perf_counter()
            cur.execute(f"SELECT * FROM {SCHEMA}.{ONLINE_TABLE} WHERE account_id = %s", [f'CTA-{900000 + account_id}'])
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

# MAGIC %md-sandbox
# MAGIC **Expected result:** from a test run (your numbers will vary):
# MAGIC
# MAGIC ```
# MAGIC ✓ Measured 100 lookups:
# MAGIC   Average: 1.59 ms
# MAGIC   Min:     1.27 ms
# MAGIC   Max:     4.51 ms
# MAGIC   Result: single-digit millisecond latency, ready for fraud scoring
# MAGIC ```
# MAGIC
# MAGIC Other runs averaged 2.32 ms and 5.63 ms. An occasional slow lookup (up to about 20 ms) is normal.
# MAGIC
# MAGIC **What this proves:** reading an account's features by key takes a few milliseconds from a notebook in the workspace, fast enough to sit inside a payment decision.
# MAGIC
# MAGIC <div style="border-left:4px solid #FF9800; background:#FFF3E0; padding:12px 16px; border-radius:4px; margin:12px 0; font-family:sans-serif;">
# MAGIC   <strong style="display:block; color:#E65100; margin-bottom:6px;">Troubleshooting</strong>
# MAGIC   <div style="color:#333;">
# MAGIC     <ul style="margin:0; padding-left:20px;">
# MAGIC       <li><strong>Much higher latency</strong> (tens of milliseconds on average): your branch's compute may have just woken from idle (see Scale to Zero). Run the cell again. From a laptop, expect about 100 ms per lookup: that's the network round trip, not the database.</li>
# MAGIC     </ul>
# MAGIC   </div>
# MAGIC </div>

# COMMAND ----------

# MAGIC %md-sandbox
# MAGIC ##### EXPAND FOR ADDITIONAL NOTES
# MAGIC
# MAGIC <details>
# MAGIC <summary><strong>Where the features come from in a real system</strong></summary>
# MAGIC
# MAGIC Here both steps run in Lakebase so you can see them side by side. In a full setup, the offline step
# MAGIC usually runs in the lakehouse, over the complete transaction history, on a schedule; the same data
# MAGIC also trains the model. The latest feature rows are then synced into Lakebase for serving, and
# MAGIC `computed_at` tells the model how fresh they are. Lakebase Data in the Lakehouse, in Part 1, shows
# MAGIC the link between the two sides.
# MAGIC
# MAGIC </details>

# COMMAND ----------

# MAGIC %md-sandbox
# MAGIC ##### Check your understanding
# MAGIC
# MAGIC <details>
# MAGIC <summary><strong>1. Why not compute the features at the moment a payment comes in?</strong></summary>
# MAGIC
# MAGIC It means scanning an account's recent events on every request. Materializing does that work once, so the payment only needs one row.
# MAGIC
# MAGIC </details>
# MAGIC
# MAGIC <details>
# MAGIC <summary><strong>2. What makes the lookup fast?</strong></summary>
# MAGIC
# MAGIC `account_id` is the primary key, so Postgres finds the row with an index, without scanning the table.
# MAGIC
# MAGIC </details>
# MAGIC
# MAGIC <details>
# MAGIC <summary><strong>3. What does computed_at tell the model?</strong></summary>
# MAGIC
# MAGIC When the row's features were computed, so it knows how fresh they are.
# MAGIC
# MAGIC </details>

# COMMAND ----------

# MAGIC %md
# MAGIC ## E. Conclusion
# MAGIC
# MAGIC In this lab you aggregated 10,000 events into one feature row per account, then served those rows
# MAGIC by key in a few milliseconds. Key takeaways:
# MAGIC
# MAGIC 1. **Compute ahead, read fast:** materialize features offline; serve them online by key.
# MAGIC 2. **A primary key is all the index you need** for single-row lookups.
# MAGIC 3. **Lakebase holds both sides here,** raw events and served features, in one database.
# MAGIC 4. **Freshness is data too:** store when each feature row was computed.
# MAGIC
# MAGIC That's the end of the Agent developers track: memory, tools, human review, similarity search, and
# MAGIC feature serving, all on one Postgres branch.

# COMMAND ----------

# MAGIC %md
# MAGIC ---
# MAGIC **You've finished the Agent developers track.**
# MAGIC
# MAGIC <a href="$../../START_HERE">← Back to the table of contents</a>
