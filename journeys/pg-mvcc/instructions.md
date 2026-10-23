# Multi-version concurrency control and the write-ahead log, instructions

## How to run this journey

There are a few ways to work through the steps. Pick one:

- **Notebook, step by step (recommended for learning):** open [`pg_mvcc.ipynb`](pg_mvcc.ipynb) and run one cell at a time. Reading each result before the next step is where the learning happens.
- **In a Databricks workspace:** import [`pg_mvcc_databricks.py`](pg_mvcc_databricks.py) and run it cell by cell there.
- **By hand:** follow the numbered steps below, copying each command yourself.
- **Just see it work:** run `python pg_mvcc.py` from this folder to execute the whole thing at once. Fast, but you learn the most from the notebook.

Run these on your own branch. If you haven't done [`../../00-setup/`](../../00-setup/), do that first; you need `LB_PROFILE`, `LB_PROJECT`, `LB_BRANCH`, and `LB_SCHEMA` set, and the bank loaded.

Everything here is a single script you can read: [`./pg_mvcc.py`](./pg_mvcc.py). You can run it end to end, or follow the steps by hand to see each piece.

## Run it end to end

```bash
cd journeys/pg-mvcc
python pg_mvcc.py
```

This walks through the entire journey and prints results. Read on for what each step does; the exact output to expect is in [`expected.md`](expected.md).

## Or step through it by hand

### Step 1, query system columns (xmin, xmax, ctid)

Query an account row and see its internal system columns:

```bash
python ../../common/scripts/lakebase.py --sql \
  "SELECT account_id, health_pct, xmin, xmax, ctid FROM bank.account WHERE account_id='CTA-100240'"
```

Output shows:
- `account_id`, `health_pct`: normal columns
- `xmin`: transaction ID that created this version (the INSERT or UPDATE that wrote it)
- `xmax`: transaction ID that marked it as dead (UPDATE or DELETE that replaced it), or 0 if still alive
- `ctid`: physical location of the row (page number and slot within the page)

Initially, xmax=0 (row is alive), and ctid points to its physical location.

### Step 2, UPDATE the row and watch versioning

UPDATE the account's health and query again:

```bash
python pg_mvcc.py --step update
```

The script:
1. Queries the row before (see xmin, xmax, ctid)
2. Runs: `UPDATE bank.account SET health_pct = 50.0 WHERE account_id='CTA-100240'`
3. Queries the row after (see new xmin, new xmax, new ctid)

Results show:
- `xmin` changed (new transaction ID)
- `ctid` changed (new physical location)
- The old version still exists (xmax is set to mark it dead)

### Step 3, run multiple UPDATEs and observe dead tuples

Run several UPDATEs on the same row:

```bash
python pg_mvcc.py --step deadtuples
```

The script runs 10 UPDATEs on CTA-100240, then checks pg_stat_user_tables to see dead tuples accumulating:

```sql
SELECT n_live_tup, n_dead_tup FROM pg_stat_user_tables WHERE relname='account';
```

Output shows dead_tup increasing (9 old versions + the current version = many dead tuples).

### Step 4, run VACUUM and reclaim space

VACUUM removes dead tuples and reclaims space:

```bash
python pg_mvcc.py --step vacuum
```

The script:
1. Checks dead tuples before: n_dead_tup is high (9 or so)
2. Runs: `VACUUM bank.account;`
3. Checks dead tuples after: n_dead_tup is zero

The space is reclaimed and the free space map is updated so future INSERTs can reuse the space.

### Step 5, (optional) check the write-ahead log

The [write-ahead log](../../docs/glossary.md) (WAL) records every transaction. Check the current WAL position:

```bash
python ../../common/scripts/lakebase.py --sql "SELECT pg_current_wal_lsn();"
```

This shows the byte position in the WAL. Each transaction (UPDATE, DELETE, etc.) advances it. This is the machinery behind [point-in-time recovery](../../docs/glossary.md) (PITR): Postgres can recover any state by replaying the WAL up to a specific [log sequence number](../../docs/glossary.md) (LSN).

## What you just did

You watched a single row's xmin and ctid change as you UPDATEd it. You saw dead tuples accumulate as you ran multiple UPDATEs. You ran VACUUM and watched dead tuples disappear. This is multi-version concurrency control in action: Postgres never overwrites rows in place; it creates new versions and reclaims old ones. The result: readers never block writers, and writers never block readers. That's the essence of Postgres's concurrency model.
