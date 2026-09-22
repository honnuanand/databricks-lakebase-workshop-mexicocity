# Your commits are a change feed, instructions

PREVIEW: Logical replication is on the Lakebase roadmap (not GA yet). This journey previews the Postgres capability.

Run these on your own branch. If you haven't done [`../../00-setup/`](../../00-setup/), do that first.

Everything here is a single script: [`../../common/scripts/pg_cdc.py`](../../common/scripts/pg_cdc.py).

## Run it end to end

```bash
cd common/scripts
python pg_cdc.py
```

This demonstrates logical decoding: creates a slot, makes writes, decodes the changes. Read on for what each
step does; the exact output is in [`expected.md`](expected.md).

## What logical decoding is

Postgres maintains a write-ahead log (WAL): a durable, ordered, byte-exact record of every change committed
to the database. An LSN (log sequence number) marks every record. Normally, the WAL is internal (for crash recovery).

Logical decoding exposes the WAL as a stream of *logical* changes (not raw bytes): every committed transaction
becomes a readable record with its INSERTs/UPDATEs/DELETEs decoded.

## Or step through it by hand

### Step 1, create demo table

```bash
python pg_cdc.py --step setup
```

Creates a simple table:

```sql
CREATE TABLE machine_cdc_demo (
    machine_id TEXT PRIMARY KEY,
    status TEXT NOT NULL,
    health_pct NUMERIC(5,2)
)
```

Seed it with 5 machines.

### Step 2, create logical replication slot

```bash
python pg_cdc.py --step slot
```

Creates a logical replication slot:

```sql
CREATE_REPLICATION_SLOT workshop_slot LOGICAL test_decoding
```

From this LSN forward, the slot captures all committed changes on the table. (Requires REPLICATION role; see FAQ.)

### Step 3, make writes and decode

```bash
python pg_cdc.py --step changes
```

Makes three committed writes:

```sql
INSERT INTO machine_cdc_demo VALUES ('M-100', 'operational', 99.5)
UPDATE machine_cdc_demo SET status='maintenance' WHERE machine_id='M-001'
DELETE FROM machine_cdc_demo WHERE machine_id='M-003'
```

Each COMMIT flushes a record to the slot. Then decodes:

```sql
SELECT lsn, data FROM pg_logical_slot_get_changes('workshop_slot', NULL, NULL)
```

Shows the exact LSN-stamped records: INSERT, UPDATE, DELETE as decoded text.

## What you just did

You tapped the commit log directly, captured committed changes as they happened, and decoded them as an
ordered stream. No polling, no external CDC pipeline, no consistency gaps. The changelog is native to Postgres.

Check the numbers against [`expected.md`](expected.md), and if anything went sideways, [`faq.md`](faq.md)
has the common causes.

## Note: this is roadmap on Lakebase

Logical replication is a **Postgres capability**, not yet GA on Lakebase Autoscaling. This journey shows what's
coming: when GA, you'll use logical decoding on Lakebase the same way.
