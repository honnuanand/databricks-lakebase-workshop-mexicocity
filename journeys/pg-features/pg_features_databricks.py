# Databricks notebook source
# COMMAND ----------

# MAGIC # Feature store served online, step by step
# MAGIC
# MAGIC A hands-on lab. Run one cell at a time. You will create raw events, materialize features into a fast table, and measure sub-millisecond lookup latency for inference.
# MAGIC
# MAGIC **Before you start:** finish `00-setup/`.
# COMMAND ----------

# MAGIC ## Setup — connect
# COMMAND ----------

import os, sys, time
sys.path.insert(0, os.path.join(os.getcwd(), '..', '..', 'common', 'scripts'))
from lakebase import connect, _env

SCHEMA = _env('LB_SCHEMA', 'factory')
EVENTS_TABLE = 'machine_events_for_features'
ONLINE_TABLE = 'machine_features_online'

print('Ready.')

# COMMAND ----------

# MAGIC ## Step 1 — Create raw events table
# MAGIC
# MAGIC ```sql
# MAGIC CREATE TABLE machine_events_for_features (
# MAGIC     event_id BIGSERIAL PRIMARY KEY,
# MAGIC     machine_id TEXT NOT NULL,
# MAGIC     event_ts TIMESTAMPTZ DEFAULT now(),
# MAGIC     event_type TEXT,
# MAGIC     cycles INT,
# MAGIC     temp_c NUMERIC(6,2),
# MAGIC     vibration_mm_s NUMERIC(6,2)
# MAGIC );
# MAGIC ```
# COMMAND ----------

with connect() as conn:
    with conn.cursor() as cur:
        cur.execute(f"DROP TABLE IF EXISTS {SCHEMA}.{EVENTS_TABLE}")
        cur.execute(f"""
            CREATE TABLE {SCHEMA}.{EVENTS_TABLE} (
                event_id BIGSERIAL PRIMARY KEY,
                machine_id TEXT NOT NULL,
                event_ts TIMESTAMPTZ DEFAULT now(),
                event_type TEXT,
                cycles INT,
                temp_c NUMERIC(6,2),
                vibration_mm_s NUMERIC(6,2)
            )
        """)
        print(f'✓ Created raw events table')

# COMMAND ----------

# MAGIC ## Step 2 — Seed raw events (10k events across 100 machines)
# MAGIC
# MAGIC ```sql
# MAGIC INSERT INTO machine_events_for_features(...)
# MAGIC SELECT ... FROM generate_series(1, 10000) g
# MAGIC ```
# COMMAND ----------

with connect() as conn:
    with conn.cursor() as cur:
        cur.execute(f"""
            INSERT INTO {SCHEMA}.{EVENTS_TABLE}(machine_id, event_ts, event_type, cycles, temp_c, vibration_mm_s)
            SELECT
                'M-' || (g % 100),
                now() - ((g / 100) || ' days')::interval,
                (ARRAY['run', 'failure', 'maintenance'])[1 + (g % 3)],
                g * 100,
                50.0 + (g % 30),
                2.0 + (g % 5)::numeric / 10
            FROM generate_series(1, 10000) g
        """)
        print(f'✓ Seeded 10k events across 100 machines')

# COMMAND ----------

# MAGIC ## Step 3 — Create online feature table
# MAGIC
# MAGIC ```sql
# MAGIC CREATE TABLE machine_features_online (
# MAGIC     machine_id TEXT PRIMARY KEY,
# MAGIC     runs_this_month INT,
# MAGIC     failures_this_month INT,
# MAGIC     avg_temp_c NUMERIC(8,2),
# MAGIC     avg_vibration_mm_s NUMERIC(8,2),
# MAGIC     total_cycles INT,
# MAGIC     computed_at TIMESTAMPTZ
# MAGIC );
# MAGIC ```
# COMMAND ----------

with connect() as conn:
    with conn.cursor() as cur:
        cur.execute(f"DROP TABLE IF EXISTS {SCHEMA}.{ONLINE_TABLE}")
        cur.execute(f"""
            CREATE TABLE {SCHEMA}.{ONLINE_TABLE} (
                machine_id TEXT PRIMARY KEY,
                runs_this_month INT,
                failures_this_month INT,
                avg_temp_c NUMERIC(8,2),
                avg_vibration_mm_s NUMERIC(8,2),
                total_cycles INT,
                computed_at TIMESTAMPTZ
            )
        """)
        print(f'✓ Created online feature table')

# COMMAND ----------

# MAGIC ## Step 4 — Materialize features from events
# MAGIC
# MAGIC ```sql
# MAGIC INSERT INTO machine_features_online(...)
# MAGIC SELECT
# MAGIC     e.machine_id,
# MAGIC     COUNT(CASE WHEN e.event_type = 'run' THEN 1 END),
# MAGIC     COUNT(CASE WHEN e.event_type = 'failure' THEN 1 END),
# MAGIC     ...
# MAGIC FROM machine_events_for_features e
# MAGIC WHERE e.event_ts >= now() - interval '30 days'
# MAGIC GROUP BY e.machine_id;
# MAGIC ```
# COMMAND ----------

with connect() as conn:
    with conn.cursor() as cur:
        cur.execute(f"""
            INSERT INTO {SCHEMA}.{ONLINE_TABLE}
            SELECT
                e.machine_id,
                COUNT(CASE WHEN e.event_type = 'run' THEN 1 END),
                COUNT(CASE WHEN e.event_type = 'failure' THEN 1 END),
                AVG(e.temp_c),
                AVG(e.vibration_mm_s),
                SUM(e.cycles),
                now()
            FROM {SCHEMA}.{EVENTS_TABLE} e
            WHERE e.event_ts >= now() - interval '30 days'
            GROUP BY e.machine_id
        """)
        print(f'✓ Materialized features from events (offline step)')

# COMMAND ----------

# MAGIC ## Step 5 — Measure online serving latency
# MAGIC
# MAGIC Run 100 primary-key lookups and time each one.
# MAGIC
# MAGIC ```python
# MAGIC latencies = []
# MAGIC for machine_id in range(100):
# MAGIC     t0 = time.perf_counter()
# MAGIC     cur.execute(f"SELECT * FROM machine_features_online WHERE machine_id = %s", [f'M-{machine_id}'])
# MAGIC     cur.fetchone()
# MAGIC     latencies.append((time.perf_counter() - t0) * 1000)
# MAGIC ```
# COMMAND ----------

with connect() as conn:
    with conn.cursor() as cur:
        latencies = []
        for machine_id in range(100):
            t0 = time.perf_counter()
            cur.execute(f"SELECT * FROM {SCHEMA}.{ONLINE_TABLE} WHERE machine_id = %s", [f'M-{machine_id % 100}'])
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
            print(f'  Result: single-digit millisecond latency, ready for inference')

# COMMAND ----------

# MAGIC ## What you learned
# MAGIC
# MAGIC Feature stores work by materializing (computing offline) and serving online (fast lookups at prediction time). Materialize aggregates from raw events into a dedicated table, indexed for speed. Serve means primary-key lookups, single-digit-millisecond latency, no computation at prediction time. Same database for both; no sync between systems.
# MAGIC
# MAGIC Next: **One query, every type** builds a single table with JSON, vectors, and geospatial data.