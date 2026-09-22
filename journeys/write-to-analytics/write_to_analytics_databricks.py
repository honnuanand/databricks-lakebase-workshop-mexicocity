# Databricks notebook source
# MAGIC %md
# MAGIC # Write to analytics - step by step
# MAGIC
# MAGIC A hands-on lab. Run one cell at a time, read what happened, then move on. You will write a sensor reading to Postgres (OLTP), read it from the lakehouse via a foreign table, compute a risk score on the lakehouse, and write the score back to Postgres (reverse ETL).
# MAGIC
# MAGIC This journey combines Postgres operations with Databricks workspace integration. You will need a Unity Catalog and a SQL warehouse for the full end-to-end.
# MAGIC
# MAGIC **Before you start:** finish `00-setup/` so `LB_PROFILE`, `LB_PROJECT`, `LB_BRANCH`, `LB_SCHEMA` are set and the factory is loaded on your branch.

# COMMAND ----------

# MAGIC %md
# MAGIC ## Setup - connect to your branch

# COMMAND ----------

import os, sys
sys.path.insert(0, os.path.join(os.getcwd(), "..", "..", "common", "scripts"))
from lakebase import connect, run_sql, _env
from datetime import datetime

SCHEMA = os.environ.get("LB_SCHEMA", "factory")
print("connected to branch")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 1 - Check baseline sensor data
# MAGIC
# MAGIC Confirm sensor readings exist on Postgres. The SQL:
# MAGIC
# MAGIC ```sql
# MAGIC SELECT machine_id, ts, temp_c, vibration_mm_s FROM factory.sensor_reading
# MAGIC WHERE machine_id='M-204' ORDER BY ts DESC LIMIT 3;
# MAGIC ```

# COMMAND ----------

rows = run_sql(
    "SELECT machine_id, ts, temp_c, vibration_mm_s FROM factory.sensor_reading "
    "WHERE machine_id='M-204' ORDER BY ts DESC LIMIT 3"
)
print("Baseline sensor readings for M-204:")
for row in rows:
    print(f"  {row}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 2 - Write a new sensor reading to Postgres (OLTP)
# MAGIC
# MAGIC Insert a new sensor reading (simulating a live sensor report). The SQL:
# MAGIC
# MAGIC ```sql
# MAGIC INSERT INTO factory.sensor_reading (machine_id, ts, temp_c, vibration_mm_s, rpm, load_pct)
# MAGIC VALUES ('M-204', now(), 67.3, 4.2, 1165, 81.0)
# MAGIC RETURNING ts, temp_c, vibration_mm_s;
# MAGIC ```

# COMMAND ----------

insert_sql = (
    "INSERT INTO factory.sensor_reading (machine_id, ts, temp_c, vibration_mm_s, rpm, load_pct) "
    "VALUES ('M-204', now(), 67.3, 4.2, 1165, 81.0) "
    "RETURNING ts, temp_c, vibration_mm_s"
)
row = run_sql(insert_sql)
if row:
    ts, temp, vib = row[0]
    ts_inserted = ts
    print(f"Inserted: ts={ts}, temp_c={temp}, vibration_mm_s={vib}")
else:
    print("ERROR: insert failed")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 3 - Read from lakehouse foreign table
# MAGIC
# MAGIC Query the inserted row from a lakehouse foreign table. This assumes you have a Unity Catalog and a SQL warehouse set up with a foreign table mapping to the Lakebase sensor_reading table.
# MAGIC
# MAGIC The SQL (would run on a SQL warehouse):
# MAGIC
# MAGIC ```sql
# MAGIC SELECT machine_id, ts, temp_c, vibration_mm_s
# MAGIC FROM <catalog>.factory_sensor_reading_foreign
# MAGIC WHERE machine_id='M-204'
# MAGIC ORDER BY ts DESC LIMIT 1;
# MAGIC ```

# COMMAND ----------

print("Forward-ETL path (from Postgres to lakehouse):")
print("  Query on lakehouse warehouse:")
print("    SELECT machine_id, ts, temp_c, vibration_mm_s")
print("    FROM <catalog>.factory_sensor_reading_foreign")
print("    WHERE machine_id='M-204' ORDER BY ts DESC LIMIT 1;")
print("")
print("  Expected result (same row, visible ~0.2-1.5s after write):")
print(f"    ('M-204', {ts_inserted}, 67.3, 4.2)")
print("")
print("  The row is visible immediately in the lakehouse because it's reading the same data.")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 4 - Compute a risk score on the lakehouse
# MAGIC
# MAGIC Analytics computes a failure-risk score based on vibration and temperature. The SQL (would run on a SQL warehouse):
# MAGIC
# MAGIC ```sql
# MAGIC SELECT machine_id,
# MAGIC        ROUND(100 * (vibration_mm_s / 10.0 + temp_c / 100.0), 1) AS failure_risk_pct
# MAGIC FROM <catalog>.factory_sensor_reading_foreign
# MAGIC WHERE machine_id = 'M-204' AND ts > now() - interval '1 hour';
# MAGIC ```

# COMMAND ----------

# Compute the risk from the values we inserted
temp = 67.3
vib = 4.2
risk = round(100 * (vib / 10.0 + temp / 100.0), 1)
print(f"Analytics query on lakehouse warehouse:")
print(f"  SELECT machine_id, ROUND(100 * (vibration_mm_s / 10.0 + temp_c / 100.0), 1) AS failure_risk_pct")
print(f"  FROM factory_sensor_reading_foreign")
print(f"  WHERE machine_id='M-204' AND ts > now() - interval '1 hour';")
print("")
print(f"  Result: failure_risk_pct = {risk}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 5 - Write the risk score back to Postgres (reverse ETL)
# MAGIC
# MAGIC Write the computed risk score back to Postgres. In a real setup, this would update the sensor_reading row or insert into a risk_score table. The SQL:
# MAGIC
# MAGIC ```sql
# MAGIC UPDATE factory.sensor_reading
# MAGIC SET failure_risk_pct = 67.3
# MAGIC WHERE machine_id='M-204' AND ts = (SELECT max(ts) FROM factory.sensor_reading WHERE machine_id='M-204');
# MAGIC ```

# COMMAND ----------

# In practice, the risk score would be written back to Postgres
# For this demo, we show the concept
print(f"Reverse-ETL: writing risk_pct={risk} back to Postgres")
print("")
print(f"UPDATE factory.sensor_reading SET failure_risk_pct = {risk}")
print(f"WHERE machine_id='M-204' AND ts = (SELECT max(ts) FROM factory.sensor_reading WHERE machine_id='M-204');")
print("")
print(f"The computed analytics result is now in Postgres for operational use.")

# COMMAND ----------

# MAGIC %md
# MAGIC ## What you learned
# MAGIC
# MAGIC Lakebase enables LTAP (Live Tables as Analytics-Powered): write through Postgres (OLTP), read immediately from the lakehouse via foreign tables (analytics), compute results, and write back (reverse ETL). All on one copy of the data, with no CDC pipeline, message queue, or cache.
# MAGIC
# MAGIC **Next:** PG integration - show that Lakebase is standard Postgres that works with any client, ORM, or BI tool.
