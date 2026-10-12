# Break it, then rewind

> ## What you'll learn
>
> **Key takeaways**
>
> - A destructive DELETE on live trading data wipes the database in an instant, with no backup job running in the background.
> - Point-in-time restore branches the database at a past LSN in seconds, recovering every row from before the mistake.
> - Recovery happens within your branch, leaving zero storage behind and production unchanged. The trade book snaps back in seconds.
>
> **You'll be able to:** delete live trade and settlement data, recover it by branching the database at a past point in time, and prove the restored data is exactly as it was.
>
> **Time:** about 15 minutes  ·  **Status:** live

## The scenario

You're the DBA for the bank's trading platform. It's late in the day, and someone runs a query to clean up old trades. A slip of the finger, and the WHERE clause is wrong: the whole trade book vanishes. The operations desk notices there are no open trades and no pending settlements. Panic.

On most databases, that's a restore-from-last-night's-backup situation. Hours to recover, or you reconstruct the book from memory and hope you don't miss a leg. On Lakebase, it's different.

## What point-in-time restore actually is

Point-in-time restore is not a special operation. It's the same zero-copy branching you used in [Branch the brain](../branch-the-brain/), but instead of branching from the current state of your branch, you branch from a *past* state. The database writes a write-ahead log (WAL) continuously, so every change is timestamped with a log sequence number (LSN). A branch from five seconds ago is a branch at the LSN that existed five seconds ago.

> **Note**
> This is exactly the machinery behind [Branch the brain](../branch-the-brain/). A branch is "the database as of an LSN." Restore is branching at a past LSN. The copy-on-write mechanism is identical; only the source LSN differs.

Here is the object model for this journey:

```text
Project (bank)
 ├─ production            the shared, protected source
 ├─ u-alex                your working branch (from 00-setup)
 └─ u-alex-restore        the point-in-time recovery branch you create, read from, then discard
```

## The wow moment

The beat worth watching: you run a destructive DELETE on your branch, watch the trade book disappear, then cut a branch at a past LSN in seconds and read the deleted rows back. No backup vault to restore from, no media recovery process, no restore window. The same copy-on-write storage mechanism that made [Branch the brain](../branch-the-brain/) fast now holds months of undo history. Delete the book at 14:32:17, branch at 14:32:10, every trade is back.

> **From the field**
> The honest number: creating a PITR branch takes the same couple of seconds as any branch creation; reading the old rows back is a SELECT query and is fast. The magic is in the machinery underneath: the database keeps the WAL, and the page server holds enough history that you can branch at any LSN within the retention window (typically 30 days on Lakebase). Compare that to a traditional Postgres, where point-in-time recovery means base backups + WAL replay on a new instance, minutes to hours, and only as granular as your backup frequency.

## What you'll do

1. Establish a small production dataset: a few trades and their settlements.
2. Note a trade's status and the timestamp of the data snapshot.
3. Delete all trades on your branch (the mistake), settlements first for the foreign key.
4. Confirm they're gone and note the delete time.
5. Create a PITR branch at a point before the delete and read the trades back.
6. Discard the PITR branch, leaving production unchanged and zero recovery data behind.

Full copy-paste steps are in [`instructions.md`](instructions.md); the exact output and timings to check against are in [`expected.md`](expected.md).

## Prerequisites

Finish [`../../00-setup/`](../../00-setup/) so you have a branch and can connect. Nothing else; this journey stands on its own. If you want the SDK calls explained, keep [`docs/lakebase-sdk.md`](../../docs/lakebase-sdk.md) open.

## Wrapping up

Once you can recover data from any point in the past by branching, disaster recovery stops feeling like a special event and starts feeling like a normal database operation. The next journey takes this same machinery and points it outward: [Write to analytics](../write-to-analytics/) wires the operational database to the lakehouse and shows how data flows both directions without a pipeline.
