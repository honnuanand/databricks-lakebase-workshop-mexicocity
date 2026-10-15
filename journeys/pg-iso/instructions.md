# Isolation & locking, instructions

## How to run this journey

There are a few ways to work through the steps. Pick one:

- **Notebook, step by step (recommended for learning):** open [`pg_iso.ipynb`](pg_iso.ipynb) and run one cell at a time. Reading each result before the next step is where the learning happens.
- **In a Databricks workspace:** import [`pg_iso_databricks.py`](pg_iso_databricks.py) and run it cell by cell there.
- **By hand:** follow the numbered steps below, copying each command yourself.
- **Just see it work:** run `python pg_iso.py` from this folder to execute the whole thing at once. Fast, but you learn the most from the notebook.

Run this on your own branch. If you haven't done [`../../00-setup/`](../../00-setup/), do that first.

This script opens **two real connections** to your branch to demonstrate row-level locking:
[`./pg_iso.py`](./pg_iso.py).

## Run it end to end

```bash
cd journeys/pg-iso
python pg_iso.py
```

This walks the whole story: creates a demo row, opens two sessions, shows the block, and confirms both updates landed.
Read on for what happens; the exact output is in [`expected.md`](expected.md).

## What the script does

### Setup

Creates a demo row: account with 10,000 available credit.

### Session A: BEGIN + UPDATE

Opens Connection A to your branch, runs:

```sql
BEGIN;
UPDATE account_isolation_demo SET available_credit = available_credit - 500 WHERE account_id = 'CTA-TEST-ISOLATION'
```

Connection A holds this transaction open (the row is locked).

### Session B: UPDATE (blocked)

Opens Connection B and tries:

```sql
UPDATE account_isolation_demo SET available_credit = available_credit - 2500 WHERE account_id = 'CTA-TEST-ISOLATION'
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

The script confirms: available_credit went from 10,000 → 9,500 (Session A) → 7,000 (Session B).
Both updates landed; neither was lost.

## Watch the lock in real time

If you want to see the lock visually, in a third terminal query `pg_stat_activity`:

```bash
python ../../common/scripts/lakebase.py --sql "SELECT pid, usename, state, wait_event_type, wait_event FROM pg_stat_activity WHERE wait_event_type = 'Lock'"
```

You'll see Session B's PID waiting on a `Lock` event while Session A holds its transaction.

## What you just did

You demonstrated Postgres row-level locking and blocking with two real, concurrent connections.
No application-level lock management, no conflicts, no lost updates. Isolation works.

Check the numbers against [`expected.md`](expected.md), and if anything went sideways, [`faq.md`](faq.md) has the common causes.
