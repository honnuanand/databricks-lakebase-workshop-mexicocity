# Your commits are a change feed

> ## What you'll learn
>
> **Key takeaways**
>
> - **PREVIEW: Logical replication is on the Lakebase roadmap (not GA yet).** This journey shows the Postgres capability on a standard instance, and will be first-class on Lakebase.
> - Tap the commit log directly: every INSERT, UPDATE, DELETE becomes an ordered, [LSN](../../docs/glossary.md)-stamped record via logical decoding (a [change data capture](../../docs/glossary.md) or CDC capability).
> - No external Debezium/Kafka pipeline; the change feed is native to the database engine, readable as an ordered stream off the [write-ahead log](../../docs/glossary.md).
>
> **You'll be able to:** create a logical replication slot, make writes, and decode them as an ordered stream of changes.
>
> **Time:** about 12 minutes  ·  **Status:** preview

## The scenario

You're running an account operations system. Accounts open, change status (good standing to watch to frozen), and close. Each state change (a new account, a fraud hold, an account closure) is a committed row change. Down the line, you have systems that need to know: "an account just moved to frozen status, update the risk cache, notify compliance, refresh the anomaly detector, trigger AML review."

The naive approach: poll the database every second or two and ask "what changed since last check?" At scale, polling breaks: you miss changes if you're slow, or you query too often and overload the database.

The Postgres answer: logical decoding (a [change data capture](../../docs/glossary.md) capability). Tap the commit log itself, the durable, ordered [write-ahead log](../../docs/glossary.md). Every change emerges as a record you can read, ordered by [LSN](../../docs/glossary.md) (log sequence number), with the exact BEGIN/DML/COMMIT structure.

This is roadmap on Lakebase. This journey previews the capability against a Postgres instance, and will migrate to first-class on Lakebase.

## The wow moment

You create a logical replication slot. You make three committed writes (INSERT, UPDATE, DELETE). You decode the slot and see the exact stream: `BEGIN → INSERT(ACCT-100, good_standing) → COMMIT`, then `BEGIN → UPDATE(ACCT-100, frozen) → COMMIT`, then `BEGIN → DELETE(ACCT-003) → COMMIT`. Each record [LSN](../../docs/glossary.md)-stamped, orderable, durable.

## What you'll do

1. Create a demo table.
2. Create a logical replication slot (captures changes from this LSN forward).
3. Make three committed writes (INSERT, UPDATE, DELETE).
4. Decode the slot and show the change stream.
5. Clean up the slot.

Full copy-paste steps are in [`instructions.md`](instructions.md); the exact output is in [`expected.md`](expected.md).

## Prerequisites

Finish [`../../00-setup/`](../../00-setup/) so you have a branch and can connect. Logical decoding (a [change data capture](../../docs/glossary.md) feature) requires special permissions; see the FAQ if you hit permission errors.

## Wrapping up

Logical decoding (the [change data capture](../../docs/glossary.md) foundation) is the roadmap for outbox patterns, cache invalidation, and downstream sync on Lakebase.
You've now seen the full Postgres track: performance tuning (pg-perf), indexes (pg-index), isolation (pg-iso),
partitioning (pg-partition), online serving (pg-features), unified queries (pg-one-database), and change data feeds (here).
This is the end of the Postgres-power journeys (part B).
