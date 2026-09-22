# Break it, then rewind, instructions

Run these on your own branch. If you haven't done [`../../00-setup/`](../../00-setup/), do that first; you need `LB_PROFILE`, `LB_PROJECT`, `LB_BRANCH`, and `LB_SCHEMA` set, and the factory loaded.

Everything here is a single script you can read: [`../../common/scripts/break_and_rewind.py`](../../common/scripts/break_and_rewind.py).
You can run it end to end, or follow the steps by hand to see each piece.

## Run it end to end

```bash
cd common/scripts
python break_and_rewind.py
```

This walks the whole story, captures the LSN before the delete, runs the delete, creates a PITR branch at that LSN, recovers the data, and prints timings. Read on for what each step does; the exact output to expect is in [`expected.md`](expected.md).

## Or step through it by hand

### Step 1, establish the data

First, confirm a few work orders exist on your branch:

```bash
python lakebase.py --sql \
  "SELECT wo_id, product_id, qty, status FROM factory.work_order"
```

You'll see the seeded work orders: WO-8821 and WO-8822. This is production data. Note the timestamp.

### Step 2, capture the LSN (optional, for the curious)

The Lakebase SDK can query the current LSN. The script does this automatically, but you can see it:

```bash
python break_and_rewind.py --step capture-lsn
```

The LSN is the write-ahead log position that marks "the state of the database right now." The PITR branch will branch from this LSN to recover the data deleted seconds later.

### Step 3, make the mistake

Delete all work orders on your branch (simulating a bad query):

```bash
python break_and_rewind.py --step delete
```

The script runs:

```sql
DELETE FROM factory.work_order;
```

Then checks: the table is now empty.

### Step 4, rewind

Create a PITR branch at the captured LSN (before the delete):

```bash
python break_and_rewind.py --step recover
```

This is the core moment:
- Calls `w.postgres.create_branch()` with `source_lsn=<the LSN from before the delete>`
- The branch endpoint reaches ACTIVE in about two seconds
- The script then reads the work orders from the PITR branch
- All deleted rows are back

### Step 5, discard the restore branch

```bash
python break_and_rewind.py --step discard
```

Delete the PITR branch. Your original branch is untouched, and the recovery data is gone.

## What you just did

You deleted live data on your branch, recovered it by branching at a past LSN (point-in-time), read the data back unchanged, and discarded the recovery branch, all without touching production and leaving zero recovery data behind. Compare the timings you saw against [`expected.md`](expected.md), and if anything went sideways, [`faq.md`](faq.md) has the common causes.
