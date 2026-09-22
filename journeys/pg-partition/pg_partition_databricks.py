# Databricks notebook source
# COMMAND ----------

# MAGIC # Scale-out: partitioning, step by step
# MAGIC
# MAGIC A hands-on lab. Run one cell at a time. You will build a RANGE-partitioned table on time, load 180k rows, and prove the planner prunes unneeded partitions.
# MAGIC
# MAGIC **Before you start:** finish `00-setup/`.
# COMMAND ----------

# MAGIC ## Setup — connect
# COMMAND ----------

import os, sys
sys.path.insert(0, os.path.join(os.getcwd(), '..', '..', 'common', 'scripts'))
from lakebase import connect, _env

DEMO_TABLE = 'sensor_readings_partitioned'
SCHEMA = _env('LB_SCHEMA', 'factory')

def show_partition_info(cur, query: str):
    cur.execute(f"EXPLAIN (FORMAT JSON) {query}")
    plan = cur.fetchone()[0][0]['Plan']
    return plan.get('Subplans Removed')

print('Ready.')

# COMMAND ----------

# MAGIC ## Step 1 — Create partitioned table
# MAGIC
# MAGIC Create a RANGE-partitioned table on the month of ts. Then create 6 monthly partitions (Jan–Jun 2024).
# MAGIC
# MAGIC ```sql
# MAGIC CREATE TABLE sensor_readings_partitioned (
# MAGIC     reading_id BIGSERIAL,
# MAGIC     machine_id TEXT NOT NULL,
# MAGIC     ts TIMESTAMPTZ NOT NULL,
# MAGIC     temp_c NUMERIC(6,2),
# MAGIC     vibration_mm_s NUMERIC(6,2),
# MAGIC     PRIMARY KEY (reading_id, ts)
# MAGIC ) PARTITION BY RANGE (ts);
# MAGIC ```
# COMMAND ----------

with connect() as conn:
    with conn.cursor() as cur:
        cur.execute(f"DROP TABLE IF EXISTS {SCHEMA}.{DEMO_TABLE} CASCADE")
        cur.execute(f"""
            CREATE TABLE {SCHEMA}.{DEMO_TABLE} (
                reading_id BIGSERIAL,
                machine_id TEXT NOT NULL,
                ts TIMESTAMPTZ NOT NULL,
                temp_c NUMERIC(6,2),
                vibration_mm_s NUMERIC(6,2),
                PRIMARY KEY (reading_id, ts)
            ) PARTITION BY RANGE (ts)
        """)
        
        # Create 6 monthly partitions
        partitions = [
            ('2024-01', '2024-01-01', '2024-02-01'),
            ('2024-02', '2024-02-01', '2024-03-01'),
            ('2024-03', '2024-03-01', '2024-04-01'),
            ('2024-04', '2024-04-01', '2024-05-01'),
            ('2024-05', '2024-05-01', '2024-06-01'),
            ('2024-06', '2024-06-01', '2024-07-01'),
        ]
        for name, start, end in partitions:
            cur.execute(f"""
                CREATE TABLE {SCHEMA}.{DEMO_TABLE}_{name} PARTITION OF {SCHEMA}.{DEMO_TABLE}
                FOR VALUES FROM ('{start}'::timestamptz) TO ('{end}'::timestamptz)
            """)
        print(f'✓ Created {SCHEMA}.{DEMO_TABLE} with 6 monthly partitions')

# COMMAND ----------

# MAGIC ## Step 2 — Load data (180k rows, 30k per month)
# MAGIC
# MAGIC ```sql
# MAGIC INSERT INTO sensor_readings_partitioned(...)
# MAGIC SELECT ... FROM generate_series(...)
# MAGIC ```
# COMMAND ----------

with connect() as conn:
    with conn.cursor() as cur:
        cur.execute(f"""
            INSERT INTO {SCHEMA}.{DEMO_TABLE}(machine_id, ts, temp_c, vibration_mm_s)
            SELECT
                'M-' || (g % 100),
                '2024-01-01'::date + (g / 100 || ' days')::interval + (g % 3600 || ' seconds')::interval,
                50.0 + (g % 30),
                2.0 + (g % 5)::numeric / 10
            FROM generate_series(1, 180000) g
        """)
        print(f'✓ Loaded 180k rows across 6 partitions (30k per month)')

# COMMAND ----------

# MAGIC ## Step 3 — Show partition pruning (one-month query)
# MAGIC
# MAGIC Query for a single month. Planner prunes 5 of 6 partitions and scans only the matching month.
# MAGIC
# MAGIC ```sql
# MAGIC EXPLAIN
# MAGIC SELECT COUNT(*) FROM sensor_readings_partitioned
# MAGIC WHERE ts >= '2024-03-01' AND ts < '2024-04-01'
# MAGIC ```
# COMMAND ----------

with connect() as conn:
    with conn.cursor() as cur:
        query = f"SELECT COUNT(*) FROM {SCHEMA}.{DEMO_TABLE} WHERE ts >= '2024-03-01' AND ts < '2024-04-01'"
        pruned = show_partition_info(cur, query)
        print(f'One-month query (March 2024):')
        print(f'  Subplans Removed: {pruned}')
        print(f'  Scanned only the March partition; skipped 5 others')

# COMMAND ----------

# MAGIC ## Step 4 — Show full-range query (no pruning)
# MAGIC
# MAGIC Query for all 6 months. Planner cannot prune; all partitions are needed.
# MAGIC
# MAGIC ```sql
# MAGIC EXPLAIN
# MAGIC SELECT COUNT(*) FROM sensor_readings_partitioned
# MAGIC WHERE ts >= '2024-01-01' AND ts < '2024-07-01'
# MAGIC ```
# COMMAND ----------

with connect() as conn:
    with conn.cursor() as cur:
        query = f"SELECT COUNT(*) FROM {SCHEMA}.{DEMO_TABLE} WHERE ts >= '2024-01-01' AND ts < '2024-07-01'"
        pruned = show_partition_info(cur, query)
        print(f'Full-range query (all 6 months):')
        print(f'  Subplans Removed: {pruned or 0}')
        print(f'  Must scan all 6 partitions')

# COMMAND ----------

# MAGIC ## What you learned
# MAGIC
# MAGIC Partitioning scales out: the planner prunes unneeded partitions on targeted queries, reducing I/O. Full-range analytical queries necessarily scan all partitions — those belong in the lakehouse, not the operational database.
# MAGIC
# MAGIC Next: **Postgres in your browser** runs Postgres in the browser using PGlite (WebAssembly).