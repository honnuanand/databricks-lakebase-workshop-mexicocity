# Multi-version concurrency control and the write-ahead log

> ## What you'll learn
>
> **Key takeaways**
>
> - [Multi-version concurrency control](../../docs/glossary.md) (MVCC) means Postgres never overwrites a row in place. When you UPDATE an account's health score, Postgres writes a new version of the row with a new xmin (transaction ID). The old version becomes a "dead tuple" and readers on old snapshots still see it.
> - Every row has system columns: `xmin` (creation TID), `xmax` (deletion TID), `ctid` (physical location). These are invisible by default but you can query them with `SELECT xmin, xmax, ctid FROM table`.
> - The numbers that matter: dead tuples accumulate until [VACUUM](../../docs/glossary.md) reclaims them. A table with 1 million rows and 1 million updates has 2 million physical versions until vacuumed. VACUUM is fast (under a second for typical workloads) and essential for long-running systems.
>
> **You'll be able to:** watch a single account row get UPDATEd, see the xmin change and ctid move, watch dead tuples accumulate in pg_stat_user_tables, and run VACUUM to reclaim space.
>
> **Time:** about 25 minutes  ·  **Status:** live

## The scenario

An account's health score drifts as a fraud review closes out, so a risk process writes a new value. Where does the old value go? It doesn't disappear, it becomes a dead tuple, still there on disk, occupying space. If you run a million updates on that account over a week, there are a million dead tuples. The table bloats. VACUUM reclaims the space by removing dead tuples, compacting the table, and updating the free space map so future INSERTs can reuse the space.

But here's the kicker: while a long-running transaction is reading the table, it still sees the old versions of rows it started reading before the UPDATEs. MVCC guarantees it never sees a partial update. Readers never block writers, and writers never block readers. That's the genius of multi-version concurrency control.

## Why MVCC matters

Most database systems use locking: a writer locks a row, updates it, unlocks. Readers wait. Postgres uses versioning: writers create new versions, readers see snapshots. The result: Postgres scales better under concurrent read-write workloads because readers and writers don't interfere. The write-ahead log (WAL) makes this durable: every write is recorded to the log first, so a crash never loses committed data.

## The wow moment

You query a single account row and see its system columns: xmin=1000, ctid=(0,1). You UPDATE the row. You query it again: xmin=1005 (new transaction), ctid=(0,2) (new physical location). The old version still exists (xmin=1000, xmax=1005). You run `SELECT COUNT(*) FROM pg_stat_user_tables WHERE n_dead_tup > 0` and see the dead tuples accumulating. Then you run VACUUM and watch `n_dead_tup` drop to zero and the table size shrink. The machinery is visible, measurable, and elegant.

## What you'll do

1. Query an account row and see its system columns (xmin, xmax, ctid).
2. UPDATE the row and query again. Watch xmin and ctid change, and see the old version become xmax-marked (dead).
3. Run multiple UPDATEs and observe dead tuples accumulating in pg_stat_user_tables.
4. Run VACUUM and watch dead tuples disappear and space reclaim.
5. (Optional) query the WAL log to see how Postgres's write-ahead log records these transactions (WAL is also called logical decoding when you tap the commit stream).

Full copy-paste steps are in [`instructions.md`](instructions.md); the exact output and reference numbers are in [`expected.md`](expected.md).

## Prerequisites

Finish [`../../00-setup/`](../../00-setup/) so you have a branch with the bank schema loaded. This journey doesn't require any special setup; it runs against the existing account table.

## Wrapping up

MVCC and VACUUM are the invisible machinery that makes Postgres's concurrency model work. Once you understand them, you see why Postgres never blocks readers (they see snapshots), why updates are fast (new versions, no locking), and why maintenance (VACUUM, ANALYZE) matters. The workshop's Postgres journeys culminate in this understanding: not just what Postgres can do, but how it does it. You've gone from SQL features to concurrency guarantees to the write-ahead log, the full depth of how a modern database stays fast, consistent, and correct. Next, learn how Postgres taps that write-ahead log for real-time data pipelines: [Change data capture](../pg-cdc/).
