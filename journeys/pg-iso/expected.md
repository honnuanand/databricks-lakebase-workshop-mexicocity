# Isolation & locking, expected results

Use this to check your run. The key: Session B blocks, then proceeds after Session A commits.

## Initial state

```text
Slots before any update: 10
```

## Session A: BEGIN + UPDATE

```text
Session A sees: 9 slots after booking 1
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
Final slots: 4 (10 - 1 - 5 = 4)
Both writes succeeded; neither was lost. Isolation works.
```

Both updates landed: Session A booked 1 slot, Session B booked 5. Total = 6 slots booked,
leaving 4 available. No conflict, no data corruption, no explicit application-level locks.

## Full run

```text
1. Initial state: machine has 10 maintenance slots available
   Slots before any update: 10

2. Session A: BEGIN + UPDATE (book 1 slot), HOLD transaction open
   Session A sees: 9 slots after booking 1
   Session A is holding the transaction open (row is LOCKED)

3. Session B: try to UPDATE the same row (book 5 slots), WILL BLOCK
   Session B running UPDATE (will wait for A's lock)...
   Session B proceeded after A committed (waited ~X.Xs)

4. Final state: both updates landed in order
   Final slots: 4 (10 - 1 - 5 = 4)
   Both writes succeeded; neither was lost. Isolation works.
```

## The numbers that matter

| Step | Slots | Reason |
| ---- | ----- | ------ |
| Initial | 10 | before any booking |
| After Session A's UPDATE | 9 | A booked 1 slot |
| After Session B's UPDATE | 4 | B booked 5 slots |
| Lost updates | 0 | both updates applied; nothing lost |

> **From the field**
> This demo uses two real connections held open across the script execution. Session B's
> wait is real, it's a Postgres row lock (a WAL record holds the lock until COMMIT). This
> is the concurrency control an operational system depends on: no lost updates, no corruption,
> no application code to prevent conflicts. The isolation is built in.
