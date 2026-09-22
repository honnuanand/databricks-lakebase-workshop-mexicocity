# Databricks notebook source
# COMMAND ----------

# MAGIC # Your commits are a change feed, step by step
# MAGIC
# MAGIC PREVIEW: Logical replication is on the Lakebase roadmap (not GA yet). This journey previews the Postgres capability.
# MAGIC
# MAGIC A hands-on lab. Run one cell at a time. You will create a logical replication slot, make writes, and decode the changes as an ordered stream.
# MAGIC
# MAGIC **Before you start:** finish `00-setup/`.
# COMMAND ----------

# MAGIC ## What is logical decoding?
# MAGIC
# MAGIC Postgres maintains a [write-ahead log](../../docs/glossary.md) (WAL): a durable, ordered, byte-exact record of every change. Logical decoding exposes that log as readable records: every committed transaction becomes an INSERT/UPDATE/DELETE record with a log sequence number (LSN). This is [change data capture](../../docs/glossary.md) (CDC) — the changelog is native to Postgres.
# COMMAND ----------

# MAGIC ## Setup — connect
# COMMAND ----------

import os, sys
sys.path.insert(0, os.path.join(os.getcwd(), '..', '..', 'common', 'scripts'))
from lakebase import connect, _env

DEMO_TABLE = 'machine_cdc_demo'
SCHEMA = _env('LB_SCHEMA', 'factory')
SLOT_NAME = 'workshop_slot'

print('Ready.')
print('Note: This is a preview. Logical decoding is on the Lakebase roadmap.')

# COMMAND ----------

# MAGIC ## Step 1 — Create demo table
# MAGIC
# MAGIC ```sql
# MAGIC CREATE TABLE machine_cdc_demo (
# MAGIC     machine_id TEXT PRIMARY KEY,
# MAGIC     status TEXT NOT NULL,
# MAGIC     health_pct NUMERIC(5,2)
# MAGIC );
# MAGIC INSERT INTO machine_cdc_demo VALUES ('M-001', 'operational', 98.0),
# MAGIC     ('M-002', 'healthy', 94.5), ('M-003', 'maintenance', 50.0),
# MAGIC     ('M-004', 'derated', 75.0), ('M-005', 'operational', 99.0);
# MAGIC ```
# COMMAND ----------

with connect() as conn:
    with conn.cursor() as cur:
        cur.execute(f"DROP TABLE IF EXISTS {SCHEMA}.{DEMO_TABLE}")
        cur.execute(f"""
            CREATE TABLE {SCHEMA}.{DEMO_TABLE} (
                machine_id TEXT PRIMARY KEY,
                status TEXT NOT NULL,
                health_pct NUMERIC(5,2)
            )
        """)
        cur.execute(f"""
            INSERT INTO {SCHEMA}.{DEMO_TABLE} VALUES
            ('M-001', 'operational', 98.0),
            ('M-002', 'healthy', 94.5),
            ('M-003', 'maintenance', 50.0),
            ('M-004', 'derated', 75.0),
            ('M-005', 'operational', 99.0)
        """)
        print(f'✓ Created demo table with 5 machines')

# COMMAND ----------

# MAGIC ## Step 2 — Create logical replication slot
# MAGIC
# MAGIC Create a slot that captures committed changes from this point forward:
# MAGIC
# MAGIC ```sql
# MAGIC CREATE_REPLICATION_SLOT workshop_slot LOGICAL test_decoding
# MAGIC ```
# COMMAND ----------

with connect() as conn:
    with conn.cursor() as cur:
        try:
            cur.execute(f"SELECT * FROM pg_replication_slots WHERE slot_name = '{SLOT_NAME}'")
            if cur.fetchone():
                print(f'  Slot {SLOT_NAME} already exists')
            else:
                cur.execute(f"SELECT * FROM pg_create_logical_replication_slot('{SLOT_NAME}', 'test_decoding')")
                print(f'✓ Created logical replication slot {SLOT_NAME}')
        except Exception as e:
            print(f'  Note: {e}')
            print(f'  (Logical decoding requires REPLICATION role — see FAQ)')

# COMMAND ----------

# MAGIC ## Step 3 — Make committed writes
# MAGIC
# MAGIC ```sql
# MAGIC INSERT INTO machine_cdc_demo VALUES ('M-100', 'operational', 99.5);
# MAGIC COMMIT;
# MAGIC
# MAGIC UPDATE machine_cdc_demo SET status = 'maintenance' WHERE machine_id = 'M-001';
# MAGIC COMMIT;
# MAGIC
# MAGIC DELETE FROM machine_cdc_demo WHERE machine_id = 'M-003';
# MAGIC COMMIT;
# MAGIC ```
# COMMAND ----------

with connect() as conn:
    with conn.cursor() as cur:
        # Each transaction auto-commits in this connection
        cur.execute(f"INSERT INTO {SCHEMA}.{DEMO_TABLE} VALUES ('M-100', 'operational', 99.5)")
        print(f'✓ INSERT committed')
        
        cur.execute(f"UPDATE {SCHEMA}.{DEMO_TABLE} SET status = 'maintenance' WHERE machine_id = 'M-001'")
        print(f'✓ UPDATE committed')
        
        cur.execute(f"DELETE FROM {SCHEMA}.{DEMO_TABLE} WHERE machine_id = 'M-003'")
        print(f'✓ DELETE committed')
        print(f'\n  Each COMMIT flushes a record to the slot')

# COMMAND ----------

# MAGIC ## Step 4 — Decode changes from the slot
# MAGIC
# MAGIC ```sql
# MAGIC SELECT lsn, data FROM pg_logical_slot_get_changes('workshop_slot', NULL, NULL)
# MAGIC ```
# COMMAND ----------

with connect() as conn:
    with conn.cursor() as cur:
        try:
            cur.execute(f"SELECT lsn, data FROM pg_logical_slot_get_changes('{SLOT_NAME}', NULL, NULL)")
            rows = cur.fetchall()
            if rows:
                print(f'✓ Decoded {len(rows)} changes:')
                for lsn, data in rows[:3]:
                    print(f'  {lsn}: {data[:80]}...')
            else:
                print(f'  No changes decoded (slot may not be active)')
        except Exception as e:
            print(f'  Could not decode: {e}')
            print(f'  (Logical decoding is preview on Lakebase)')

# COMMAND ----------

# MAGIC ## What you learned
# MAGIC
# MAGIC Postgres logical decoding exposes the write-ahead log as a stream of decoded changes: INSERT, UPDATE, DELETE records with LSN timestamps. No polling, no external CDC pipeline, no consistency gaps. The changelog is native to Postgres and on the Lakebase roadmap.
# MAGIC
# MAGIC When logical replication ships on Lakebase, you will use it the same way: create a slot, write to the table, decode the slot. Your commits are a change feed.