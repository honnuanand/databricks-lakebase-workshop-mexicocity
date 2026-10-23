# Your commits are a change feed, instructions

## How to run this journey

There are a few ways to work through the steps. Pick one:

- **Notebook, step by step (recommended for learning):** open [`pg_cdc.ipynb`](pg_cdc.ipynb) and run one cell at a time. Reading each result before the next step is where the learning happens.
- **In a Databricks workspace:** import [`pg_cdc_databricks.py`](pg_cdc_databricks.py) and run it cell by cell there.
- **By hand:** follow the numbered steps below, copying each command yourself.
- **Just see it work:** run `python pg_cdc.py` from this folder to execute the whole thing at once. Fast, but you learn the most from the notebook.

PREVIEW: Logical replication is on the Lakebase roadmap (not GA yet). This journey previews the Postgres capability.

Run these on your own branch. If you haven't done [`../../00-setup/`](../../00-setup/), do that first.

Everything here is a single script: [`./pg_cdc.py`](./pg_cdc.py).

## Run it end to end

```bash
cd journeys/pg-cdc
python pg_cdc.py
```

This demonstrates logical decoding: creates a slot, makes writes, decodes the changes. Read on for what each
step does; the exact output is in [`expected.md`](expected.md).

## What logical decoding is

Postgres maintains a [write-ahead log](../../docs/glossary.md) (WAL): a durable, ordered, byte-exact record of every change committed
to the database. An [LSN](../../docs/glossary.md) (log sequence number) marks every record. Normally, the WAL is internal (for crash recovery).

Logical decoding exposes the WAL as a stream of *logical* changes (not raw bytes): every committed transaction
becomes a readable record with its INSERTs/UPDATEs/DELETEs decoded. This is the [change data capture](../../docs/glossary.md) (CDC) capability.

## Or step through it by hand

### Step 1, create demo table

```bash
python pg_cdc.py --step setup
```

Creates a simple table:

```sql
CREATE TABLE account_cdc_demo (
    account_id TEXT PRIMARY KEY,
    status TEXT NOT NULL,
    health_pct NUMERIC(5,2)
)
```

Seed it with 5 accounts.

### Step 2, create logical replication slot

```bash
python pg_cdc.py --step slot
```

Creates a logical replication slot:

```sql
CREATE_REPLICATION_SLOT workshop_slot LOGICAL test_decoding
```

From this [LSN](../../docs/glossary.md) forward, the slot captures all committed changes on the table. (Requires REPLICATION role; see FAQ.)

### Step 3, make writes and decode

```bash
python pg_cdc.py --step changes
```

Makes three committed writes:

```sql
INSERT INTO account_cdc_demo VALUES ('CTA-100', 'good_standing', 99.5)
UPDATE account_cdc_demo SET status='frozen' WHERE account_id='CTA-001'
DELETE FROM account_cdc_demo WHERE account_id='CTA-003'
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
