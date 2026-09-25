# Databricks notebook source
# MAGIC %md
# MAGIC # One copy, both directions, step by step
# MAGIC
# MAGIC A hands-on lab. The Lakebase idea here: your operational rows are the same rows analytics
# MAGIC reads. No change-data-capture job copies data between an OLTP store and an analytics store;
# MAGIC there is one copy, reachable from both sides.
# MAGIC
# MAGIC **What runs live here:** a real write through Postgres, a computed failure-risk score, written
# MAGIC back onto the row, and read back. **What is an explainer (clearly labeled, not run):** reading
# MAGIC the same rows from the lakehouse through a Unity Catalog foreign table on a SQL warehouse. That
# MAGIC needs a metastore-admin catalog registration, so we show the exact query rather than fake it.
# MAGIC
# MAGIC **Before you start:** finish `00-setup/`. M-204 is a stamping press on your factory branch.

# COMMAND ----------

# MAGIC %md
# MAGIC ## Setup, connect

# COMMAND ----------

import os, sys
sys.path.insert(0, os.path.join(os.getcwd(), "..", "..", "common", "scripts"))
from lakebase import run_sql
print("ready")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 1, add a failure_risk column and write a reading (OLTP)
# MAGIC
# MAGIC First make room for an analytics-derived value, then write a new sensor reading through
# MAGIC Postgres, a millisecond operational write.
# MAGIC
# MAGIC ```sql
# MAGIC ALTER TABLE factory.sensor_reading ADD COLUMN IF NOT EXISTS failure_risk NUMERIC(5,1);
# MAGIC INSERT INTO factory.sensor_reading (machine_id, ts, temp_c, vibration_mm_s, rpm, load_pct)
# MAGIC VALUES ('M-204', now(), 67.3, 4.2, 1165, 81.0) RETURNING reading_id;
# MAGIC ```

# COMMAND ----------

run_sql("ALTER TABLE factory.sensor_reading ADD COLUMN IF NOT EXISTS failure_risk NUMERIC(5,1)")
r = run_sql("""INSERT INTO factory.sensor_reading
  (machine_id, ts, temp_c, vibration_mm_s, rpm, load_pct)
  VALUES ('M-204', now(), 67.3, 4.2, 1165, 81.0)
  RETURNING reading_id, temp_c, vibration_mm_s""")
rid = r[0][0]
print("inserted reading_id", r[0])

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 2, compute a failure-risk score and write it back
# MAGIC
# MAGIC Compute a score from the row and write it back onto the same row: an analytics-derived value
# MAGIC served at operational latency.
# MAGIC
# MAGIC ```sql
# MAGIC UPDATE factory.sensor_reading
# MAGIC SET failure_risk = ROUND(100 * (vibration_mm_s / 10.0 + temp_c / 100.0), 1)
# MAGIC WHERE reading_id = <rid>;
# MAGIC ```

# COMMAND ----------

run_sql(f"UPDATE factory.sensor_reading SET failure_risk = "
        f"ROUND(100*(vibration_mm_s/10.0 + temp_c/100.0),1) WHERE reading_id={rid}")
row = run_sql(f"SELECT reading_id, machine_id, temp_c, vibration_mm_s, failure_risk "
              f"FROM factory.sensor_reading WHERE reading_id={rid}")[0]
print("scored + wrote back:", row)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 3, the lakehouse side (same copy, no pipeline), EXPLAINER
# MAGIC
# MAGIC This step is not run here: it needs the Lakebase database registered as a Unity Catalog online
# MAGIC catalog, which is a metastore-admin action (CREATE CATALOG). Once it exists, the SAME rows are
# MAGIC visible to a SQL warehouse with no pipeline and no synced copy. The query you would run:
# MAGIC
# MAGIC ```sql
# MAGIC -- on a SQL warehouse, against the UC foreign catalog for this database:
# MAGIC SELECT machine_id, ts, temp_c, vibration_mm_s, failure_risk
# MAGIC FROM <catalog>.factory.sensor_reading
# MAGIC WHERE machine_id = 'M-204' ORDER BY ts DESC LIMIT 1;
# MAGIC ```
# MAGIC
# MAGIC The row you wrote in Step 1 appears there immediately, because it is the same copy. Nothing
# MAGIC above is simulated: the write and the score are real on your branch; only this lakehouse read
# MAGIC needs the admin catalog setup, so we show the query honestly instead of faking its output.

# COMMAND ----------

# MAGIC %md
# MAGIC ## What you learned
# MAGIC
# MAGIC One copy of the data served both the operational write and the analytics-derived score, with no
# MAGIC pipeline between them. In a full setup the lakehouse reads the same rows through a UC foreign
# MAGIC catalog. Next: **Fits your landscape**, pointing standard Postgres tools at Lakebase.
