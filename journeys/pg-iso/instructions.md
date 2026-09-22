# Isolation & locking, instructions

Run this on your own branch. If you haven't done [`../../00-setup/`](../../00-setup/), do that first.

This script opens **two real connections** to your branch to demonstrate row-level locking:
[`../../common/scripts/pg_iso.py`](../../common/scripts/pg_iso.py).

## Run it end to end

```bash
cd common/scripts
python pg_iso.py
```

This walks the whole story: creates a demo row, opens two sessions, shows the block, and confirms both updates landed.
Read on for what happens; the exact output is in [`expected.md`](expected.md).

## What the script does

### Setup

Creates a demo row: machine with 10 maintenance slots available.

### Session A: BEGIN + UPDATE

Opens Connection A to your branch, runs:

```sql
BEGIN;
UPDATE machine_isolation_demo SET maintenance_slots = maintenance_slots - 1 WHERE machine_id = 'M-TEST-ISOLATION'
```

Connection A holds this transaction open (the row is locked).

### Session B: UPDATE (blocked)

Opens Connection B and tries:

```sql
UPDATE machine_isolation_demo SET maintenance_slots = maintenance_slots - 5 WHERE machine_id = 'M-TEST-ISOLATION'
```

**Session B blocks.** It waits on Session A's lock. The script demonstrates the wait.

### Session A: COMMIT

Connection A commits, releasing the lock.

```sql
COMMIT;
```

### Session B: proceeds

Session B's UPDATE instantly proceeds (the lock was released).

### Final result

The script confirms: slots went from 10 → 9 (Session A) → 4 (Session B).
Both updates landed; neither was lost.

## Watch the lock in real time

If you want to see the lock visually, in a third terminal query `pg_stat_activity`:

```bash
python lakebase.py --sql "SELECT pid, usename, state, wait_event_type, wait_event FROM pg_stat_activity WHERE wait_event_type = 'Lock'"
```

You'll see Session B's PID waiting on a `Lock` event while Session A holds its transaction.

## What you just did

You demonstrated Postgres row-level locking and blocking with two real, concurrent connections.
No application-level lock management, no conflicts, no lost updates. Isolation works.

Check the numbers against [`expected.md`](expected.md), and if anything went sideways, [`faq.md`](faq.md) has the common causes.
