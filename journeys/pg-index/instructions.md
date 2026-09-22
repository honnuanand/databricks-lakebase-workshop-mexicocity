# One engine, every index, instructions

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
CREATE TABLE machine_index_demo (
    machine_id TEXT PRIMARY KEY,           -- btree (equality lookups)
    status_code INT NOT NULL,               -- hash (integer equality)
    spec JSONB DEFAULT '{}'::jsonb,        -- gin (JSON containment)
    created_at TIMESTAMPTZ NOT NULL,        -- brin (time ranges)
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
CREATE INDEX idx_btree_machine_id ON machine_index_demo USING BTREE (machine_id)
CREATE INDEX idx_hash_status ON machine_index_demo USING HASH (status_code)
CREATE INDEX idx_gin_spec ON machine_index_demo USING GIN (spec)
CREATE INDEX idx_brin_created ON machine_index_demo USING BRIN (created_at)
CREATE INDEX idx_gist_location ON machine_index_demo USING GIST (location)
CREATE INDEX idx_hnsw_embedding ON machine_index_demo USING HNSW (embedding vector_cosine_ops)
```

Each access method (AM) is optimized for a different query pattern.

### Step 3, show EXPLAIN for each query type

```bash
python pg_index.py --step explain
```

Runs EXPLAIN on six queries:

1. **BTREE**: `WHERE machine_id = 'M-100'` (exact match) → picks btree
2. **HASH**: `WHERE status_code = 5` (integer equality) → picks hash
3. **GIN**: `WHERE spec @> '{"model": "CNC-X1"}` (JSON containment) → picks gin
4. **BRIN**: `WHERE created_at > now() - interval '90 days'` (time range) → picks brin
5. **GIST**: `WHERE location <-> point(45, -73) < 1` (spatial distance) → picks gist
6. *(HNSW)*: Vector similarity (if pgvector available)

Each EXPLAIN shows the matching index was used.

## What you just did

You built one table carrying six completely different data types and six index access methods, and proved the planner uses each on the right query. One engine, not six systems.

Check the numbers against [`expected.md`](expected.md), and if anything went sideways, [`faq.md`](faq.md) has the common causes.
