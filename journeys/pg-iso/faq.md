# Isolation & locking, FAQ

## The script timed out waiting for Session B

Session B may have hung due to a network issue or session crash. This is rare but can happen if your connection to the branch is interrupted. Try running the script again; if it persists, check:

```bash
python lakebase.py --check
```

to confirm your connection to the branch works.

## I ran it but didn't see the "blocked" message

The script may have run too fast (especially on a warm connection). The blocking is real, but the wait time was very short, under 100 ms. Re-run it; you may see a longer wait on the second run or on a cold project.

The core point: both updates landed without loss, which you can confirm from the final available credit.

## Can I watch the lock without running the script?

Yes. In one terminal, run the script. In another terminal, while it's running, query `pg_stat_activity`:

```bash
python lakebase.py --sql "SELECT pid, usename, state, wait_event_type FROM pg_stat_activity LIMIT 5"
```

You'll see Session B's PID with `wait_event_type = 'Lock'` while Session A is in a transaction.

## What if I don't want Session B to block? Can I use SELECT ... FOR UPDATE to get a quicker error?

Yes, but that's a different pattern. You could use:

```sql
UPDATE account_isolation_demo SET available_credit = ... WHERE account_id = 'ACCT-TEST-ISOLATION' NOWAIT
```

`NOWAIT` tells the database to fail immediately if the row is locked, instead of waiting. But this
requires application-level retry logic. Postgres's default (wait and proceed) is safer for most systems.

## This demo is synchronous (Session B waits). What about async / non-blocking?

Postgres's concurrency model is pessimistic locking: hold a lock until committed. This ensures
ACID but blocks conflicting transactions.

Some systems use optimistic locking (check versions, retry on conflict) or eventually-consistent
models. Those trade off different guarantees. Postgres's blocking model is simpler and correct; it's
why it powers operational (not just analytical) systems.

## In production, how do I avoid long lock waits?

Keep transactions short. The longer Session A holds a lock, the longer Session B waits:

- Don't open a transaction, do some work, then SELECT. SELECT-then-UPDATE in one transaction is faster.
- Don't hold locks across network round-trips.
- Use appropriate isolation levels (the default is fine for most cases).

On Lakebase, lock contention is rare because the Postgres node has no external latency, it's all
in-region on the instance.

## Does this work across branches?

No. Each branch is its own Postgres server; locks don't span branches. This journey locks a row on
*your* branch. If someone else updates the same account ID on the production branch, that's a separate
row, separate lock. Branches are isolated by design.

(See [`../branch-the-brain/`](../branch-the-brain/) for the branching story.)
