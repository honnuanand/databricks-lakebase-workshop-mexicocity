# Write to analytics, FAQ

## I don't have Unity Catalog access or a SQL warehouse

The forward-ETL path (write through Postgres, read from foreign table) requires UC and warehouse permission. If you don't have these, the script will:
1. Show you the SQL for creating the external table (MANAGED_ONLINE_CATALOG).
2. Show the query SQL for reading from the foreign table.
3. Skip execution and provide example results.

You can still learn the concept by following the shown SQL and results. The reverse-ETL step (writing back) requires direct warehouse SQL execution, which also won't run without permissions, the script shows the SQL instead.

If this is a shared workspace and you need permissions, ask your workspace admin for:
- `catalog.tables:create` on a specific Unity Catalog (or at workspace level).
- Access to a SQL warehouse (or create one on your own).

## My workspace doesn't have a Unity Catalog set up

The journey requires UC for the foreign-table integration. If UC isn't enabled:
1. Contact your workspace admin to enable it.
2. Or, use a linked external catalog (Databricks can connect to external Hive metastores or other catalogs).

Without UC or an external catalog, the foreign-table path won't work. The script will offer the read-only walkthrough instead.

## The warehouse query was really slow

Cold warehouses take time to warm up (30–60 seconds first run, then faster). If the query was slow:
- Run it again; warm warehouses are typically 10x faster.
- Use a larger warehouse size (more clusters provision faster).
- Simplify the query (fewer joins, smaller result sets).

The first query in this journey is small and on recently-inserted data, so it should be fast once the warehouse is warm.

## Can I use Streaming Table (ST) instead of external table (ET)?

Yes, but the setup is different. Streaming Tables with APPLY CHANGES INTO are designed for CDC scenarios (capturing deletes, updates over time). For this journey's live-query scenario (read the current state of Postgres table), an external table is simpler. Streaming Tables shine when you have a append-only change stream to materialize.

## The reverse-ETL write failed

The reverse write (analytics → Postgres) is a direct write to the Postgres database. If it failed:
- Check that your user has INSERT or UPDATE permission on the sensor_reading table (your branch's grants should allow this).
- If the write timed out, the Postgres connection may have dropped. Re-run the step.
- If the warehouse query produced no rows, there's nothing to write back; check the compute score step first.

## What if my lakehouse is slow or in a different region?

If the lakehouse and Lakebase instance are in different regions, network latency will add to query time (typically 50–200 ms one-way). The foreign-table query will be slower. For production, co-locate the lakehouse and Lakebase instance in the same region.

Lakebase instance region is set at provisioning time. Lakehouse region (workspace) is also set at provisioning. Both are cloud-provider and region specific.

## Is this a real setup, or is it simulated?

This is a real setup against live databases. The writes are real INSERTs to Postgres. The reads are real SQL queries against the lakehouse warehouse. The foreign table is a real UC integration. The only "simulation" is the analytics query (the risk-score calculation), which in a real system would be a complex ML model. You're using real infrastructure and real data flow, the intelligence is simplified for the walkthrough.

## Can I do this without Databricks Lakehouse (using an external lakehouse)?

Lakebase can integrate with external catalogs (Hive metastores, Iceberg catalogs, etc.) via UC's multi-catalog federation. The setup is more involved (you'd need to register the external catalog in UC first), but the concept is the same. The runnable script assumes Databricks UC; if you want to use an external catalog, you'll need to set it up separately and adapt the script.

## Is there a CDC alternative for real-time capture?

Yes. Databricks is building logical decoding support on Lakebase, which will let you capture a change stream directly from the Postgres WAL. That's on the roadmap. For now, the foreign-table path (live query) is the supported live-integration approach, and it has zero pipeline, it's as close to real-time as a query latency allows.
