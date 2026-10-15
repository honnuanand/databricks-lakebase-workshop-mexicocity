# Operational vectors, instructions

## How to run this journey

There are a few ways to work through the steps. Pick one:

- **Notebook, step by step (recommended for learning):** open [`pg_vector.ipynb`](pg_vector.ipynb) and run one cell at a time. Reading each result before the next step is where the learning happens.
- **In a Databricks workspace:** import [`pg_vector_databricks.py`](pg_vector_databricks.py) and run it cell by cell there.
- **By hand:** follow the numbered steps below, copying each command yourself.
- **Just see it work:** run `python pg_vector.py` from this folder to execute the whole thing at once. Fast, but you learn the most from the notebook.

Run these on your own branch. If you haven't done [`../../00-setup/`](../../00-setup/), do that
first; you need `LB_PROFILE`, `LB_PROJECT`, `LB_BRANCH`, and `LB_SCHEMA` set, and the bank
loaded.

Most of this journey is SQL. The script [`./pg_vector.py`](./pg_vector.py)
orchestrates the steps; you can also run them by hand in a SQL client.

## Run it end to end

```bash
cd journeys/pg-vector
python pg_vector.py
```

This walks the whole story: create the extension, populate embeddings, and run similarity search.
Read on for what each step does; the exact output to expect is in [`expected.md`](expected.md).

## Or step through it by hand

### Step 1, check the instrument table

The bank schema has an `instrument` table with specs in a JSONB column. Check it:

```bash
python ../../common/scripts/lakebase.py --sql \
  "SELECT instrument_id, name, kind FROM bank.instrument LIMIT 5"
```

You should see the 5 seed instruments: `INS-QTZL` (Quetzal Tecnologia, equity), `INS-ZAFR` (Zafiro Software, equity),
`INS-CASH-MXN` (cash), `INS-SLEEVE-EQ` (ETF), and `INS-MBONO-10Y` (Bono M, a Mexican government bond).

### Step 2, enable the pgvector extension

pgvector is a Postgres extension. Enable it in your branch:

```bash
python ../../common/scripts/lakebase.py --sql "CREATE EXTENSION IF NOT EXISTS vector"
```

This is a one-time setup per branch. Verify it's installed:

```bash
python ../../common/scripts/lakebase.py --sql "SELECT extname FROM pg_extension WHERE extname='vector'"
```

You should see one row: `vector`.

### Step 3, add an embedding column to the instrument table

Add a vector column to store 768-dimensional embeddings (matching typical embedding models):

```bash
python ../../common/scripts/lakebase.py --sql \
  "ALTER TABLE bank.instrument ADD COLUMN IF NOT EXISTS embedding vector(768)"
```

Check the column was added:

```bash
python ../../common/scripts/lakebase.py --sql \
  "SELECT column_name FROM information_schema.columns \
   WHERE table_name='instrument' AND column_name='embedding'"
```

### Step 4, populate embeddings

This is where you would normally call an embedding API (e.g., OpenAI text-embedding-3-small) to
encode each instrument's spec. For this workshop, we use a deterministic hash-based approach to generate
reproducible embeddings:

```bash
python pg_vector.py --step embed
```

The script:
1. For each instrument, reads the spec (JSONB) and name.
2. Hashes the concatenated text to generate a deterministic "embedding" (a 768-dim vector of
   standardized values derived from the hash).
3. Updates the instrument row with the embedding vector.

You should see output like:

```text
Embedding 5 instruments:
  INS-QTZL: embedded
  INS-CASH-MXN: embedded
  INS-ZAFR: embedded
  INS-SLEEVE-EQ: embedded
  INS-MBONO-10Y: embedded
```

Query to confirm:

```bash
python ../../common/scripts/lakebase.py --sql \
  "SELECT instrument_id, name, (embedding IS NOT NULL) as has_embedding FROM bank.instrument"
```

All rows should have embeddings now.

### Step 5, write a similarity search query

The key query: find instruments similar to a reference instrument using the `<=>` cosine similarity operator:

```bash
python pg_vector.py --step search
```

The script runs a query like:

```sql
SELECT
  p.instrument_id, p.name, p.kind,
  1 - (p.embedding <=> ref_embedding) AS similarity
FROM bank.instrument p
WHERE p.embedding IS NOT NULL
  AND p.instrument_id != 'INS-QTZL'  -- exclude the original
ORDER BY similarity DESC
LIMIT 5;
```

This ranks the other instruments by closeness to `INS-QTZL`. The `<=>` operator returns cosine
*distance* (0 = identical direction, 1 = orthogonal, up to 2 = opposite). We compute similarity as
`1 - distance` so higher is better; with hash embeddings that value can go slightly negative when
two vectors point apart.

You should see output like:

```text
Running similarity search:
  Reference instrument: INS-QTZL
  Top comparable instruments:
    1. INS-MBONO-10Y: similarity=0.11 (Bono M 10Y (Mexico), bond)
    2. INS-SLEEVE-EQ: similarity=0.03 (Equity Sleeve, etf)
    3. INS-ZAFR: similarity=-0.09 (Zafiro Software, equity)
    4. INS-CASH-MXN: similarity=-0.22 (Mexican Peso Cash, cash)
```

The ranking here is driven by the hash embedding, not real financial resemblance, so do not read
meaning into "the Bono M is closest to Quetzal". With a real embedding model the same query returns
semantically meaningful neighbours. See [`expected.md`](expected.md) for the honesty note in full.

### Step 6, optional: create an HNSW index

For large tables (millions of vectors), create an HNSW index to accelerate similarity search:

```bash
python pg_vector.py --step index
```

This runs:

```sql
CREATE INDEX ON bank.instrument USING hnsw (embedding vector_cosine_ops)
```

The `vector_cosine_ops` index family uses cosine similarity (the `<=>` operator). [Hierarchical Navigable Small Worlds](../../docs/glossary.md) (HNSW) keeps queries fast even with millions of vectors.

Check the index exists:

```bash
python ../../common/scripts/lakebase.py --sql \
  "SELECT indexname FROM pg_indexes WHERE tablename='instrument' AND indexname LIKE '%embedding%'"
```

## What you just did

You added pgvector to your Lakebase branch, populated embeddings on the instrument table, and ran a
similarity search to find comparable instruments in a single SQL query. No network hop, no cache miss,
no eventual consistency, the database is the vector engine.

Compare the output you saw against [`expected.md`](expected.md), and if anything went sideways,
[`faq.md`](faq.md) has the common causes.
