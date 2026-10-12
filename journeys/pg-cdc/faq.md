# Your commits are a change feed, FAQ

## "Could not create logical replication slot" or permission error

Logical decoding requires the **REPLICATION** role (or superuser). On a managed Lakebase instance, the default
user may not have this. Options:

1. Ask your instance admin to grant REPLICATION role:
   ```sql
   ALTER ROLE your_user WITH REPLICATION
   ```

2. Or, acknowledge that this is a **preview**, logical decoding is not yet GA on Lakebase. The script
   gracefully skips the demo if permissions are missing.

This journey is a capability preview. When logical decoding ships on Lakebase, this will just work.

## Why do I need REPLICATION role?

Logical replication slots are a powerful primitive: they can hold the WAL indefinitely (preventing cleanup),
consume significant resources, and expose the internal structure of committed transactions. Only trusted roles
get access.

## The slot never captured my changes

Make sure you:
1. Created the slot (it will print "Created logical replication slot: ...").
2. Made the writes *after* creating the slot. Changes before the slot's LSN aren't captured.
3. Each write is in its own transaction (or explicitly COMMIT).

If the slot is old and WAL has been cleaned up, the slot becomes invalid. Create a fresh slot.

## Can I have multiple slots?

Yes. Each slot has its own cursor into the WAL. Useful for multiple consumers:
- Slot A feeds a fraud risk scoring system.
- Slot B feeds an AML compliance pipeline.
- Slot C feeds a ledger sync processor.

Each advances independently. An idle slot may hold WAL (preventing cleanup), so monitor and drop unused slots.

## What if the slot gets too far behind?

If a slot isn't read frequently, the WAL log builds up on disk (since the slot holds it). Eventually, the disk
fills or the server stops accepting writes. This is rare in production if your CDC consumer is actively reading,
but monitor slot lag:

```sql
SELECT slot_name, restart_lsn, now() - pg_xact_xmin_age(xmin) AS age
FROM pg_replication_slots WHERE slot_type = 'logical'
```

Drop unused slots promptly.

## Is this available on Lakebase now?

**No, this is roadmap.** Logical replication/decoding is not GA on Lakebase Autoscaling yet. This journey
demonstrates the Postgres capability so you know what's coming. Once GA, you'll use logical decoding on Lakebase
exactly as shown here.

## When will it ship on Lakebase?

Check the [Lakebase roadmap](https://docs.databricks.com/aws/en/oltp/projects/roadmap). Logical replication
is planned; timing is TBD.

## What can I use for CDC today (before logical replication ships)?

Some options:
1. **Polling query**: "SELECT * WHERE created_at > last_check". Simple, okay for low-frequency changes.
2. **Trigger-based log**: INSERT into a change-log table on every DML. Works but is application overhead.
3. **PITR + diff**: Branch at past LSN, EXCEPT to compare (from [break-and-rewind](../break-and-rewind/)). Clunky but works.
4. **Kafka + Debezium** (external): Debezium can tail Postgres WAL (if exposed), push to Kafka. Overkill for Lakebase.

Once logical decoding ships on Lakebase, use that, it's the native solution.

## Why LSN and not timestamps?

LSNs are:
- **Ordered**: strictly increasing; you can compare them.
- **Durable**: tied to the WAL; survive server restart.
- **Precise**: no clock-skew issues; exact position in the log.

Timestamps can be imprecise (clock adjustments, multiple updates in the same millisecond). LSNs are the right primitive
for a durable, ordered change feed.

## Can I decode specific tables only?

Logical decoding as shown here captures all changes. You can filter in the decoder (the `test_decoding` output handler
filters by table/type), or you can have the downstream consumer filter (subscribe to only the topics you care about).

When GA on Lakebase, there may be table-level slot options; check the docs.
