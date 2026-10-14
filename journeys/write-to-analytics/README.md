# One copy, both directions

> ## What you'll learn
>
> **Key takeaways**
>
> - Your operational rows are the same rows analytics reads: one copy, no [change data capture](../../docs/glossary.md) (CDC) job copying between an [online transaction processing](../../docs/glossary.md) (OLTP) store and an [online analytical processing](../../docs/glossary.md) (OLAP) store.
> - You write a transaction through Lakebase, compute a fraud-risk score, and write it back onto the row, all live on your branch, so the authorization path serves an analytics-derived value at OLTP latency.
> - The lakehouse read of those same rows (through a Unity Catalog foreign catalog on a SQL warehouse) needs a metastore-admin catalog registration. This journey shows the exact query rather than faking output, so the "no pipeline" claim stays honest.
>
> **You'll be able to:** run the operational write-score-write-back-read round trip live, and know exactly the query that reads the same rows from the lakehouse once the database is registered in Unity Catalog.
>
> **Time:** about 20 minutes  ·  **Status:** live (operational round trip) + explainer (the lakehouse read needs a UC catalog an admin registers)

## The scenario

A card transaction lands on account ACCT-100240: a $2,200 charge, overnight, from an unfamiliar
merchant category, on an account whose utilization is already running hot. The authorization
system has milliseconds to decide. Meanwhile the fraud team's analytics run on the lakehouse,
scoring patterns across millions of transactions. The usual architecture copies operational
transactions out to an analytics store on a schedule, so the score the authorization path sees is
always a little stale.

What if the score were computed on the same copy and written straight back? The moment a
transaction lands in Lakebase, it is visible to lakehouse analytics with no pipeline. Analytics
computes a fraud-risk score and writes it back onto the transaction row, so the operational path
serves that analytics-derived value at transaction latency.

That is the Lakebase live-data-flow idea: one database copy, operational and analytical work on it
at once. No change-data-capture daemon, no ETL pipeline, no sync lag. Write through Lakebase, read
from the lakehouse, compute, write back.

## How it works

Lakebase registers its database into Unity Catalog as an online catalog. The lakehouse then reads
the Postgres rows directly through that catalog, no copy, no lag: an INSERT in Postgres is visible
to a SQL warehouse immediately. Analytics computes a value and writes it back directly to Postgres.

> **Note**
> Registering the database as a Unity Catalog catalog is a metastore-admin action (CREATE CATALOG).
> This journey runs the operational round trip live (write, score, write back, read), and shows the
> exact lakehouse query you would run once the catalog exists, rather than faking its output. See
> the FAQ for how to request the catalog registration.

## The wow moment

The beat worth watching: you INSERT a transaction in Lakebase (one SQL statement, millisecond
latency), compute a fraud-risk score from it, and write that score back onto the same row, all in a
few milliseconds, all on one copy. The operational authorization path can now read an
analytics-derived risk value with no second system in the loop. And the same row is readable from
the lakehouse the moment it is written, no pipeline to lag.

> **From the field**
> The honest shape: the operational round trip (INSERT, compute, UPDATE, SELECT) is all normal
> Postgres writes and reads, so it is milliseconds. The lakehouse read of the same rows is a live
> view through the Unity Catalog online catalog, not a replicated copy, so there is no "pipeline
> latency" to speak of; the read is network plus query planning. There is no sync job because there
> is no second copy.

## What you'll do

1. Write a new transaction through Lakebase (the $2,200 charge on ACCT-100240).
2. Compute a fraud-risk score from the transaction's anomaly score and account utilization.
3. Write that score back onto the transaction row (a `fraud_risk` column).
4. Read the scored row back from Lakebase at operational latency.
5. See the exact lakehouse query that reads the same rows once the database is registered in UC.

Full copy-paste steps are in [`instructions.md`](instructions.md); the exact output to check
against is in [`expected.md`](expected.md).

## Prerequisites

Finish [`../../00-setup/`](../../00-setup/) so you have a branch and can connect. The operational
round trip runs with just your branch. The lakehouse read step is an explainer unless your database
is registered as a Unity Catalog catalog (a metastore-admin action); see [`faq.md`](faq.md).

## Wrapping up

Once you see an analytics-derived value computed and served on one copy, the mental model shifts
from "ETL as a scheduled batch job" to "analytics as a query on the operational data." The next
journey steps back to the database mechanics: [Fits your landscape](../pg-integration/) shows that
Lakebase is just Postgres, any driver, tool, or BI system connects with no adapter.
