# Write to analytics

> ## What you'll learn
>
> **Key takeaways**
>
> - Write a sensor reading through Postgres ([online transaction processing](../../docs/glossary.md) (OLTP) milliseconds) and the same row appears in a lakehouse foreign table immediately, no [change data capture](../../docs/glossary.md) (CDC), no pipeline.
> - Analytics runs a SQL query on the lakehouse to compute a failure-risk score from the readings.
> - The score is written back directly to Postgres. Two workloads, one copy, both engines, round-trip closed.
>
> **You'll be able to:** demonstrate live data flowing both directions between Postgres ([online transaction processing](../../docs/glossary.md) (OLTP)) and the lakehouse ([online analytical processing](../../docs/glossary.md) (OLAP)) with no sync pipeline in between.
>
> **Time:** about 20 minutes  ·  **Status:** live

## The scenario

The stamping plant runs live. Sensors on machine M-204 stream temperature, vibration, RPM, and load every few seconds. Right now those readings pile up in Postgres, and analysts run nightly queries to spot anomalies. By morning, a failing machine might have wrecked the night shift.

What if the analytics ran live? The moment a sensor reading arrives at Postgres, it's visible to the lakehouse. Analytics computes a risk score, probability of failure in the next hour, and pushes that score back to Postgres so the MES system can route new work away from risky machines.

That's [LTAP](../../docs/glossary.md) (Live Tables as Analytics-Powered): one database copy, both the [online transaction processing](../../docs/glossary.md) (OLTP) and analytics engines running on it simultaneously. No [change data capture](../../docs/glossary.md) (CDC) daemon, no ETL pipeline, no sync lag. Write through Postgres, read from the lakehouse, compute analytics, write back.

## How it works

Lakebase connects to a Unity Catalog in your workspace (or a linked external catalog). Inside that catalog, you define a MANAGED_ONLINE_CATALOG foreign table that maps to the Postgres table on Lakebase. When you INSERT a row in Postgres, the lakehouse sees it immediately via that foreign table, no copy, no lag. When analytics computes a value, it writes back directly to Postgres (bypassing the read-only foreign table with a direct write).

> **Note**
> This journey assumes you have a Unity Catalog workspace and permission to create external tables. If you don't, the runnable script will flag this and show you the read-only path (you can read and follow along, but won't be able to write back). See the FAQ for alternatives.

## The wow moment

The beat worth watching: you INSERT a sensor reading in Postgres (one SQL statement, millisecond latency), and then query the same table from the lakehouse, same row, same moment, no pipeline. The timer between write and read shows query latency, not sync lag: there is no pipeline to lag. Then analytics computes a risk score and writes it back, and you read the new score from Postgres.

> **From the field**
> The honest numbers: the forward path (Postgres → foreign table → lakehouse read) is a live view onto the same rows, so read latency is network + query planning, typically tens to hundreds of milliseconds. The reverse path (analytics query → write back to Postgres) is a direct INSERT or UPDATE, which is a normal write, also milliseconds. There's no "pipeline latency" because there's no pipeline, the foreign table is a direct query, not a replicated copy. If you have a slow lakehouse warehouse (e.g. 1–2 nodes), the analytics query itself may take seconds; the write-back is still fast.

## What you'll do

1. Establish a small sensor_reading table on Postgres (a few baseline readings for M-204).
2. Write a new sensor reading through Postgres.
3. Query the same table from the lakehouse and confirm the new row is visible immediately.
4. Run an analytics query on the lakehouse to compute a failure-risk score (simulated; you may run pre-canned SQL if you don't have analytics workspace).
5. Write the risk score back to Postgres and read it live.

Full copy-paste steps are in [`instructions.md`](instructions.md); the exact output and timings to check against are in [`expected.md`](expected.md).

## Prerequisites

Finish [`../../00-setup/`](../../00-setup/) so you have a branch and can connect. You'll also need:
- A Unity Catalog in your Databricks workspace with permission to create external tables.
- A SQL warehouse (compute) to run analytics queries.
- If you don't have these, the script provides a read-only walkthrough.

> **Note**
> The full end-to-end write-back requires Databricks workspace privileges (Unity Catalog admin, warehouse permission). If you're on a shared workspace without these, you can still run the forward (write-to-read) part and follow the reverse-ETL step by hand with pre-computed results. See [`faq.md`](faq.md).

## Wrapping up

Once you see live data flowing both directions without a pipeline, the mental model shifts from "ETL as a scheduled batch job" to "data integration as a query." The next journey steps back to the database mechanics: [Pg integration](../pg-integration/) shows that Lakebase is just Postgres, any driver, tool, or BI system connects with no adapter.
