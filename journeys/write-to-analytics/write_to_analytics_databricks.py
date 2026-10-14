# Databricks notebook source
# MAGIC %md
# MAGIC # One copy, both directions, step by step
# MAGIC
# MAGIC A hands-on lab. The Lakebase idea here: your operational rows are the same rows analytics
# MAGIC reads. No change-data-capture job copies data between an OLTP store and an analytics store;
# MAGIC there is one copy, reachable from both sides.
# MAGIC
# MAGIC **What runs live here:** a real transaction written through Postgres, a computed fraud-risk score,
# MAGIC written back onto the row, and read back. **What is an explainer (clearly labeled, not run):**
# MAGIC reading the same rows from the lakehouse through a Unity Catalog foreign table on a SQL warehouse.
# MAGIC That needs a metastore-admin catalog registration, so we show the exact query rather than fake it.
# MAGIC
# MAGIC **Before you start:** finish `00-setup/`. ACCT-100240 is a retail credit account on your branch.

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
# MAGIC ## Step 1, add a fraud_risk column and write a transaction (OLTP)
# MAGIC
# MAGIC First make room for an analytics-derived value, then write a new card transaction through
# MAGIC Postgres, a millisecond operational write.
# MAGIC
# MAGIC ```sql
# MAGIC ALTER TABLE bank.txn ADD COLUMN IF NOT EXISTS fraud_risk NUMERIC(5,1);
# MAGIC INSERT INTO bank.txn (account_id, ts, amount_usd, anomaly_score, mcc, util_pct)
# MAGIC VALUES ('ACCT-100240', now(), 2200.00, 8.7, 6011, 92.0) RETURNING txn_id;
# MAGIC ```

# COMMAND ----------

run_sql("ALTER TABLE bank.txn ADD COLUMN IF NOT EXISTS fraud_risk NUMERIC(5,1)")
r = run_sql("""INSERT INTO bank.txn
  (account_id, ts, amount_usd, anomaly_score, mcc, util_pct)
  VALUES ('ACCT-100240', now(), 2200.00, 8.7, 6011, 92.0)
  RETURNING txn_id, amount_usd, anomaly_score""")
rid = r[0][0]
print("inserted txn_id", r[0])

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 2, compute a fraud-risk score and write it back
# MAGIC
# MAGIC Compute a score from the row and write it back onto the same row: an analytics-derived value
# MAGIC served at operational latency. A high anomaly score and a near-maxed utilization push the
# MAGIC fraud risk up.
# MAGIC
# MAGIC ```sql
# MAGIC UPDATE bank.txn
# MAGIC SET fraud_risk = ROUND(100 * (anomaly_score / 10.0 + util_pct / 100.0), 1)
# MAGIC WHERE txn_id = <rid>;
# MAGIC ```

# COMMAND ----------

run_sql(f"UPDATE bank.txn SET fraud_risk = "
        f"ROUND(100*(anomaly_score/10.0 + util_pct/100.0),1) WHERE txn_id={rid}")
row = run_sql(f"SELECT txn_id, account_id, amount_usd, anomaly_score, util_pct, fraud_risk "
              f"FROM bank.txn WHERE txn_id={rid}")[0]
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
# MAGIC SELECT account_id, ts, amount_usd, anomaly_score, fraud_risk
# MAGIC FROM <catalog>.bank.txn
# MAGIC WHERE account_id = 'ACCT-100240' ORDER BY ts DESC LIMIT 1;
# MAGIC ```
# MAGIC
# MAGIC The transaction you wrote in Step 1 appears there immediately, because it is the same copy.
# MAGIC Nothing above is simulated: the write and the score are real on your branch; only this lakehouse
# MAGIC read needs the admin catalog setup, so we show the query honestly instead of faking its output.

# COMMAND ----------

# MAGIC %md
# MAGIC ## What you learned
# MAGIC
# MAGIC One copy of the data served both the operational write and the analytics-derived fraud score, with
# MAGIC no pipeline between them. In a full setup the lakehouse reads the same rows through a UC foreign
# MAGIC catalog. Next: **Fits your landscape**, pointing standard Postgres tools at Lakebase.
