# Your commits are a change feed

> ## What you'll learn
>
> **Key takeaways**
>
> - **PREVIEW: Logical replication is on the Lakebase roadmap (not GA yet).** This journey shows the Postgres capability on a standard instance, and will be first-class on Lakebase.
> - Tap the commit log directly: every INSERT, UPDATE, DELETE becomes an ordered, LSN-stamped record via logical decoding.
> - No external Debezium/Kafka pipeline; the change feed is native to the database engine.
>
> **You'll be able to:** create a logical replication slot, make writes, and decode them as an ordered stream of changes.
>
> **Time:** about 12 minutes  ·  **Status:** preview

## The scenario

You're running a digital-twin system. Machines go down, get repaired, come back online. Each state change (a booking, a status flip, a maintenance log entry) is a committed row change. Down the line, you have systems that need to know: "a machine just went into maintenance, update the cache, notify ops, update the search index, call the partner API."

The naive approach: poll the database every second or two and ask "what changed since last check?" At scale, polling breaks: you miss changes if you're slow, or you query too often and overload the database.

The Postgres answer: logical decoding. Tap the commit log itself, the durable, ordered write-ahead log (WAL). Every change emerges as a record you can read, ordered by LSN (log sequence number), with the exact BEGIN/DML/COMMIT structure.

This is roadmap on Lakebase. This journey previews the capability against a Postgres instance, and will migrate to first-class on Lakebase.

## The wow moment

You create a logical replication slot. You make three committed writes (INSERT, UPDATE, DELETE). You decode the slot and see the exact stream: `BEGIN → INSERT(M-100, operational) → COMMIT`, then `BEGIN → UPDATE(M-100, maintenance) → COMMIT`, then `BEGIN → DELETE(M-100) → COMMIT`. Each record LSN-stamped, orderable, durable.

## What you'll do

1. Create a demo table.
2. Create a logical replication slot (captures changes from this LSN forward).
3. Make three committed writes (INSERT, UPDATE, DELETE).
4. Decode the slot and show the change stream.
5. Clean up the slot.

Full copy-paste steps are in [`instructions.md`](instructions.md); the exact output is in [`expected.md`](expected.md).

## Prerequisites

Finish [`../../00-setup/`](../../00-setup/) so you have a branch and can connect. Logical decoding requires special permissions; see the FAQ if you hit permission errors.

## Wrapping up

Logical decoding is the roadmap foundation for outbox patterns, cache invalidation, and downstream sync on Lakebase.
You've now seen the full Postgres track: performance tuning (pg-perf), indexes (pg-index), isolation (pg-iso),
partitioning (pg-partition), online serving (pg-features), unified queries (pg-one-database), and change-feeds (here).
This is the end of the Postgres-power journeys (part B).
