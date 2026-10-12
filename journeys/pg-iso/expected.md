# Isolation & locking, expected results

Use this to check your run. The key: Session B blocks, then proceeds after Session A commits.

## Initial state

```text
Available credit before any update: 10000
```

## Session A: BEGIN + UPDATE

```text
Session A sees: 9500 available credit after reducing by 500
Session A is holding the transaction open (row is LOCKED)
```

Session A locked the row with its UPDATE and is holding the lock (not yet committed).

## Session B: UPDATE (blocked)

```text
Session B running UPDATE (will wait for A's lock)...
Session B proceeded after A committed (waited ~X.Xs)
```

Session B's UPDATE blocked waiting for Session A's lock. You see the wait time.

## Final state

```text
Final available credit: 7000 (10000 - 500 - 2500 = 7000)
Both writes succeeded; neither was lost. Isolation works.
```

Both updates landed: Session A reduced by 500, Session B reduced by 2,500. Total reduction = 3,000,
leaving 7,000 available. No conflict, no data corruption, no explicit application-level locks.

## Full run

```text
1. Initial state: account has 10,000 available credit
   Available credit before any update: 10000

2. Session A: BEGIN + UPDATE (reduce by 500), HOLD transaction open
   Session A sees: 9500 available credit after reducing by 500
   Session A is holding the transaction open (row is LOCKED)

3. Session B: try to UPDATE the same row (reduce by 2500), WILL BLOCK
   Session B running UPDATE (will wait for A's lock)...
   Session B proceeded after A committed (waited ~X.Xs)

4. Final state: both updates landed in order
   Final available credit: 7000 (10000 - 500 - 2500 = 7000)
   Both writes succeeded; neither was lost. Isolation works.
```

## The numbers that matter

| Step | Available Credit | Reason |
| ---- | ---- | ------ |
| Initial | 10000 | before any transaction |
| After Session A's UPDATE | 9500 | A reduced by 500 |
| After Session B's UPDATE | 7000 | B reduced by 2500 |
| Lost updates | 0 | both updates applied; nothing lost |

> **From the field**
> This demo uses two real connections held open across the script execution. Session B's
> wait is real, it's a Postgres row lock (a WAL record holds the lock until COMMIT). This
> is the concurrency control an operational system depends on: no lost updates, no corruption,
> no application code to prevent conflicts. The isolation is built in.
