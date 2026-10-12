# Databricks notebook source
# COMMAND ----------

# MAGIC # Tune the planner, step by step
# MAGIC
# MAGIC A hands-on lab. Run one cell at a time, read what happened, then move on. You will create a demo table with correlated columns, measure the planner's bad row estimate, create extended statistics, and prove the fix.
# MAGIC
# MAGIC Each step shows the plain SQL too, so you can copy it and run it in psql, the Lakebase SQL editor, or any tool. The Python just runs that SQL against your branch.
# MAGIC
# MAGIC **Before you start:** finish `00-setup/` so `LB_PROFILE`, `LB_PROJECT`, `LB_BRANCH`, `LB_SCHEMA` are set and the bank is loaded on your branch.
# COMMAND ----------

# MAGIC ## Setup, connect
# COMMAND ----------

import os, sys
sys.path.insert(0, os.path.join(os.getcwd(), '..', '..', 'common', 'scripts'))
from lakebase import connect, _env

DEMO_TABLE = 'account_perf_demo'
DEMO_STAT = 'account_perf_stat'
SCHEMA = _env('LB_SCHEMA', 'bank')

def _explain(cur, query: str) -> tuple[int, int]:
    cur.execute(f"EXPLAIN (ANALYZE, FORMAT JSON) {query}")
    raw = cur.fetchone()[0][0]
    p = raw['Plan']
    while p.get('Plans'):
        p = p['Plans'][0]
    est = p.get('Plan Rows', 0)
    act = p.get('Actual Rows', 0)
    return est, act

print('Ready.')

# COMMAND ----------

# MAGIC ## Step 1, Create demo table
# MAGIC
# MAGIC Create a table where region is 100 percent correlated with branch_id. Branch BR-NYC is US-Northeast, BR-SFO is US-West.
# MAGIC
# MAGIC ```sql
# MAGIC CREATE TABLE account_perf_demo (
# MAGIC     id BIGSERIAL PRIMARY KEY,
# MAGIC     account_id TEXT,
# MAGIC     branch_id TEXT,
# MAGIC     region TEXT,
# MAGIC     amount_usd NUMERIC,
# MAGIC     health_pct NUMERIC
# MAGIC );
# MAGIC ```
# COMMAND ----------

with connect() as conn:
    with conn.cursor() as cur:
        cur.execute(f"DROP TABLE IF EXISTS {SCHEMA}.{DEMO_TABLE} CASCADE")
        cur.execute(f"DROP STATISTICS IF EXISTS {SCHEMA}.{DEMO_STAT}")
        cur.execute(f"""
            CREATE TABLE {SCHEMA}.{DEMO_TABLE} (
                id BIGSERIAL PRIMARY KEY,
                account_id TEXT,
                branch_id TEXT,
                region TEXT,
                amount_usd NUMERIC,
                health_pct NUMERIC
            )
        """)
        cur.execute(f"""
            INSERT INTO {SCHEMA}.{DEMO_TABLE}(account_id, branch_id, region, amount_usd, health_pct)
            SELECT
                'ACCT-' || g,
                (ARRAY['BR-NYC', 'BR-NYC', 'BR-SFO', 'BR-SFO'])[1 + (g % 4)],
                CASE (g % 4)
                    WHEN 0 THEN 'US-Northeast'
                    WHEN 1 THEN 'US-Northeast'
                    WHEN 2 THEN 'US-West'
                    ELSE 'US-West'
                END,
                50.0 + (g % 30),
                80.0 + (g % 20)
            FROM generate_series(1, 100000) g
        """)
        cur.execute(f"ANALYZE {SCHEMA}.{DEMO_TABLE}")
        print(f'✓ Created {SCHEMA}.{DEMO_TABLE} (100k rows, correlated columns)')

# COMMAND ----------

# MAGIC ## Step 2, Bad estimate (no statistics)
# MAGIC
# MAGIC Query with a correlated filter. Planner assumes independence and underestimates rows.
# MAGIC
# MAGIC ```sql
# MAGIC EXPLAIN ANALYZE
# MAGIC SELECT account_id FROM account_perf_demo
# MAGIC WHERE branch_id = 'BR-NYC' AND region = 'US-Northeast'
# MAGIC ```
# COMMAND ----------

with connect() as conn:
    with conn.cursor() as cur:
        query = f"SELECT account_id FROM {SCHEMA}.{DEMO_TABLE} WHERE branch_id = 'BR-NYC' AND region = 'US-Northeast'"
        est, act = _explain(cur, query)
        if est > 0:
            ratio = act / est
            print(f'Before CREATE STATISTICS:')
            print(f'  Estimated: {est:,}')
            print(f'  Actual:    {act:,}')
            print(f'  Error:     {ratio:.1f}x off')

# COMMAND ----------

# MAGIC ## Step 3, Create statistics
# MAGIC
# MAGIC Teach the planner about the correlation.
# MAGIC
# MAGIC ```sql
# MAGIC CREATE STATISTICS account_perf_stat
# MAGIC ON branch_id, region
# MAGIC FROM account_perf_demo;
# MAGIC
# MAGIC ANALYZE account_perf_demo;
# MAGIC ```
# COMMAND ----------

with connect() as conn:
    with conn.cursor() as cur:
        cur.execute(f"""
            CREATE STATISTICS {SCHEMA}.{DEMO_STAT}
            ON branch_id, region
            FROM {SCHEMA}.{DEMO_TABLE}
        """)
        cur.execute(f"ANALYZE {SCHEMA}.{DEMO_TABLE}")
        print(f'✓ Created statistics; planner now knows the correlation')

# COMMAND ----------

# MAGIC ## Step 4, Fixed estimate (with statistics)
# MAGIC
# MAGIC Same query. Now the planner estimates accurately.
# MAGIC
# MAGIC ```sql
# MAGIC EXPLAIN ANALYZE
# MAGIC SELECT account_id FROM account_perf_demo
# MAGIC WHERE branch_id = 'BR-NYC' AND region = 'US-Northeast'
# MAGIC ```
# COMMAND ----------

with connect() as conn:
    with conn.cursor() as cur:
        query = f"SELECT account_id FROM {SCHEMA}.{DEMO_TABLE} WHERE branch_id = 'BR-NYC' AND region = 'US-Northeast'"
        est, act = _explain(cur, query)
        print(f'After CREATE STATISTICS:')
        print(f'  Estimated: {est:,}')
        print(f'  Actual:    {act:,}')
        print(f'  Accurate: {est == act}')

# COMMAND ----------

# MAGIC ## What you learned
# MAGIC
# MAGIC Extended statistics teach the planner about column correlations. Without them, the planner assumes independence and badly underestimates rows, which cascades into bad execution plans. Same table, same data, same query, the difference is the statistics.
# MAGIC
# MAGIC Next: **One engine, every index** measures how different index types are selected for different queries.
