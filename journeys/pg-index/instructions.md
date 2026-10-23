# One engine, every index, instructions

## How to run this journey

There are a few ways to work through the steps. Pick one:

- **Notebook, step by step (recommended for learning):** open [`pg_index.ipynb`](pg_index.ipynb) and run one cell at a time. Reading each result before the next step is where the learning happens.
- **In a Databricks workspace:** import [`pg_index_databricks.py`](pg_index_databricks.py) and run it cell by cell there.
- **By hand:** follow the numbered steps below, copying each command yourself.
- **Just see it work:** run `python pg_index.py` from this folder to execute the whole thing at once. Fast, but you learn the most from the notebook.

Run these on your own branch. If you haven't done [`../../00-setup/`](../../00-setup/), do that first.

Everything here is a single script: [`./pg_index.py`](./pg_index.py).

## Run it end to end

```bash
cd journeys/pg-index
python pg_index.py
```

This builds the table, creates all six indexes, and runs EXPLAIN on each query type. Read on for what each step does; the exact output is in [`expected.md`](expected.md).

## Or step through it by hand

### Step 1, create the demo table

```bash
python pg_index.py --step setup
```

Creates a 60k-row table with every data type:

```sql
CREATE TABLE account_index_demo (
    account_id TEXT PRIMARY KEY,           -- btree (equality lookups)
    mcc INT NOT NULL,                       -- hash (integer equality)
    spec JSONB DEFAULT '{}'::jsonb,        -- gin (JSON containment)
    opened_at TIMESTAMPTZ NOT NULL,         -- brin (time ranges)
    location POINT,                         -- gist (spatial distance)
    embedding VECTOR(256)                   -- hnsw (vector similarity)
)
```

Data: 60k rows with all fields populated.

### Step 2, create all six indexes

```bash
python pg_index.py --step indexes
```

The script creates six indexes:

```sql
CREATE INDEX idx_btree_account_id ON account_index_demo USING BTREE (account_id)
CREATE INDEX idx_hash_mcc ON account_index_demo USING HASH (mcc)
CREATE INDEX idx_gin_spec ON account_index_demo USING GIN (spec)
CREATE INDEX idx_brin_opened ON account_index_demo USING BRIN (opened_at)
CREATE INDEX idx_gist_location ON account_index_demo USING GIST (location)
CREATE INDEX idx_hnsw_embedding ON account_index_demo USING HNSW (embedding vector_cosine_ops)
```

Each access method (AM) is optimized for a different query pattern.

### Step 3, show EXPLAIN for each query type

```bash
python pg_index.py --step explain
```

Runs EXPLAIN on six queries:

1. **BTREE**: `WHERE account_id = 'CTA-100'` (exact match) → picks btree
2. **HASH**: `WHERE mcc = 5` (integer equality) → picks hash
3. **GIN**: `WHERE spec @> '{"product": "Checking"}` (JSON containment) → picks gin
4. **BRIN**: `WHERE opened_at > now() - interval '90 days'` (time range) → picks brin
5. **GIST**: `WHERE location <-> point(40.7549, -73.9840) < 1` (spatial distance) → picks gist
6. *(HNSW)*: Vector similarity (if pgvector available)

Each EXPLAIN shows the matching index was used.

## What you just did

You built one table carrying six completely different data types and six index access methods, and proved the planner uses each on the right query. One engine, not six systems.

Check the numbers against [`expected.md`](expected.md), and if anything went sideways, [`faq.md`](faq.md) has the common causes.
