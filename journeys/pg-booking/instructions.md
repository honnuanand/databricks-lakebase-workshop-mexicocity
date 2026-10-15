# No settlement overlap, instructions

## How to run this journey

There are a few ways to work through the steps. Pick one:

- **Notebook, step by step (recommended for learning):** open [`pg_booking.ipynb`](pg_booking.ipynb) and run one cell at a time. Reading each result before the next step is where the learning happens.
- **In a Databricks workspace:** import [`pg_booking_databricks.py`](pg_booking_databricks.py) and run it cell by cell there.
- **By hand:** follow the numbered steps below, copying each command yourself.
- **Just see it work:** run `python pg_booking.py` from this folder to execute the whole thing at once. Fast, but you learn the most from the notebook.

Run these on your own branch. If you haven't done [`../../00-setup/`](../../00-setup/), do that first; you need `LB_PROFILE`, `LB_PROJECT`, `LB_BRANCH`, and `LB_SCHEMA` set, and the bank loaded.

Everything here is a single script you can read: [`./pg_booking.py`](./pg_booking.py). You can run it end to end, or follow the steps by hand to see each piece.

## Run it end to end

```bash
cd journeys/pg-booking
python pg_booking.py
```

This walks through the entire journey and prints results. Read on for what each step does; the exact output to expect is in [`expected.md`](expected.md).

## Or step through it by hand

### Step 1, inspect the settlement table

Examine the settlement table: settlement_id, trade_id (the originating trade), account_id (the target account), starts_at (window start), ends_at (window end):

```bash
python ../../common/scripts/lakebase.py --sql \
  "SELECT settlement_id, account_id, starts_at, ends_at FROM bank.settlement LIMIT 5"
```

This shows scheduled settlements on accounts. Each settlement occupies a time window (starts_at to ends_at).

### Step 2, create a GiST exclusion constraint

An exclusion constraint says "no two rows can have these properties at the same time." Here's the constraint:

```bash
python pg_booking.py --step constraint
```

The script runs:

```sql
CREATE EXTENSION IF NOT EXISTS btree_gist;

ALTER TABLE bank.settlement
  ADD CONSTRAINT no_account_overlap
  EXCLUDE USING gist (account_id WITH =, tstzrange(starts_at, ends_at) WITH &&);
```

Breaking this down:
- `EXCLUDE USING gist`: use a GiST index to enforce exclusion.
- `account_id WITH =`: only rows with the same account_id are excluded.
- `tstzrange(starts_at, ends_at) WITH &&`: exclude if their time ranges overlap (&&).

This constraint ensures: no two settlements on the same account can have overlapping time ranges.

### Step 3, try to insert an overlapping settlement

Insert a settlement that overlaps with an existing one and see the constraint violation:

```bash
python pg_booking.py --step overlap
```

The script finds an existing settlement, creates a new one that overlaps, and tries to insert it. The database rejects it:

```text
ERROR: conflicting key value violates exclusion constraint "no_account_overlap"
DETAIL: Key (account_id, tstzrange(starts_at, ends_at))=(CTA-100240, ["2024-01-15 14:00:00+00","2024-01-15 15:00:00+00"]) conflicts with existing key.
```

This is the guarantee: the constraint is enforced atomically by the database. No app code can allow it.

### Step 4, verify the constraint with EXPLAIN

Check that the constraint is being used:

```bash
python pg_booking.py --step explain
```

The plan shows the GiST index being used to check for conflicts. This is invisible to the app, it just works.

## What you just did

You created a GiST exclusion constraint that prevents overlapping settlements on the same account. The database rejects any attempt to insert overlapping rows, atomically, no matter how many requests race. No app code is needed; the constraint is the guarantee.
