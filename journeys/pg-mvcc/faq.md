# Multi-version concurrency control and the write-ahead log, FAQ

## It failed with a "refresh token" or authentication error

Your Databricks login expired. Re-run the login from [`../../00-setup/auth.md`](../../00-setup/auth.md):

```bash
databricks auth login --host https://<your-workspace>.cloud.databricks.com --profile workshop
```

Then re-run the step.

## "Missing required env var LB_PROJECT / LB_BRANCH"

You're in a terminal that didn't load your environment. Re-source it:

```bash
source workshop.env
```

## "table factory.machine does not exist"

The factory schema was not loaded. Go back to [`../../00-setup/`](../../00-setup/) and run the load-factory step.

## xmin, xmax, ctid are not showing in my query

These are system columns. They're not included in `SELECT *` by default. Query them explicitly:

```sql
SELECT xmin, xmax, ctid, machine_id FROM factory.machine;
```

Or use `SELECT *` and explicitly add them:

```sql
SELECT *, xmin, xmax, ctid FROM factory.machine;
```

## My UPDATEs don't seem to be creating new versions

Check that autovacuum hasn't cleaned up the old versions yet. If autovacuum runs frequently (typical), dead tuples disappear quickly. You can disable it temporarily to see dead tuple accumulation:

```sql
ALTER TABLE factory.machine SET (autovacuum_enabled = false);
-- Now do your UPDATEs; dead tuples will accumulate
-- Re-enable when done
ALTER TABLE factory.machine SET (autovacuum_enabled = true);
```

Or run `VACUUM` manually when you're ready to clean up.

## What's the difference between xmin and xid?

- `xmin`: the transaction ID that created (or last UPDATEd) this version of the row
- `xid`: used in different contexts (e.g., `txid_current()` returns the current transaction ID)

In the context of MVCC, `xmin` is what matters: it marks the version.

## Why does VACUUM take time?

VACUUM scans the entire table and:
1. Identifies dead tuples (rows with xmax set)
2. Removes them
3. Rebuilds the free space map
4. Updates statistics (implicit ANALYZE)

On large tables (millions of rows), this I/O is slow. That's why VACUUM is typically scheduled for off-peak hours. Autovacuum (enabled by default) runs it automatically in the background, using worker processes.

## Can I prevent dead tuples from accumulating?

Not without constant VACUUM. MVCC is inherent to Postgres: every UPDATE creates a dead tuple that must eventually be removed. The solution is regular VACUUM (autovacuum does this automatically). If you're running a system with very high UPDATE rates and can't afford to VACUUM regularly, you might need to tune autovacuum parameters or upgrade your hardware.

## What's the relationship between MVCC and isolation levels?

MVCC is the mechanism; isolation levels (READ UNCOMMITTED, READ COMMITTED, REPEATABLE READ, SERIALIZABLE) are the contract. MVCC ensures that readers see consistent snapshots, which enables isolation levels to work as designed. In REPEATABLE READ, you see the snapshot from the start of your transaction. In READ COMMITTED, you see committed changes as of each statement start.

## How do I know if a long-running transaction is causing table bloat?

Long-running transactions prevent VACUUM from reclaiming tuples because the transaction might still need to see old versions. If you see `n_dead_tup` growing without bound (and autovacuum isn't catching up), you might have a long-running query. Check:

```sql
SELECT pid, usename, application_name, state, query_start
  FROM pg_stat_activity
 WHERE state != 'idle'
   AND query_start < now() - INTERVAL '10 minutes';
```

This shows queries running longer than 10 minutes. If one is reading a table that has high bloat, that might be your culprit.

## What's the write-ahead log? Do I need to understand it for MVCC?

The [write-ahead log](../../docs/glossary.md) (WAL) is Postgres's transaction log. Every transaction is recorded in the WAL before being applied to the table. This ensures durability: even if the server crashes, the WAL can replay committed transactions and recover the database.

For MVCC, the WAL is important because it records the [log sequence number](../../docs/glossary.md) (LSN) of every transaction. This is the foundation of [point-in-time recovery](../../docs/glossary.md) (PITR): Postgres can recover to any point in time by replaying the WAL up to that LSN. But you don't need to understand WAL details to understand MVCC, just know that multi-version concurrency control uses transaction IDs (xmin/xmax) to manage versions, and PITR uses LSNs to record transaction order.

## Can I query the WAL directly?

Not in a user-friendly way. The WAL is a binary log. To examine it, you'd use `pg_waldump` (a Postgres utility) or logical decoding (an advanced feature). For most purposes, you don't need to. `pg_current_wal_lsn()` shows the current position; that's usually enough.
