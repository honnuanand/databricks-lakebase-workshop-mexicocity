# One query, every type, instructions

## How to run this journey

There are a few ways to work through the steps. Pick one:

- **Notebook, step by step (recommended for learning):** open [`pg_one_database.ipynb`](pg_one_database.ipynb) and run one cell at a time. Reading each result before the next step is where the learning happens.
- **In a Databricks workspace:** import [`pg_one_database_databricks.py`](pg_one_database_databricks.py) and run it cell by cell there.
- **By hand:** follow the numbered steps below, copying each command yourself.
- **Just see it work:** run `python pg_one_database.py` from this folder to execute the whole thing at once. Fast, but you learn the most from the notebook.

Run these on your own branch. If you haven't done [`../../00-setup/`](../../00-setup/), do that first.

Everything here is a single script: [`./pg_one_database.py`](./pg_one_database.py).

## Run it end to end

```bash
cd journeys/pg-one-database
python pg_one_database.py
```

This builds a unified table with all four data types and runs a single query across them. Read on for
what each step does; the exact output is in [`expected.md`](expected.md).

## Or step through it by hand

### Step 1, create unified table

```bash
python pg_one_database.py --step sql
```

Shows (without running) the setup SQL that creates the unified table and populates it with 1000 accounts.

### Step 2, build and query

```bash
python pg_one_database.py
```

Creates the table:

```sql
CREATE TABLE account_unified_demo (
    account_id TEXT PRIMARY KEY,
    branch_id TEXT NOT NULL,
    line TEXT NOT NULL,
    spec JSONB,                      -- JSON data type
    embedding VECTOR(64),             -- pgvector embedding
    location GEOMETRY(POINT, 4326)    -- geospatial point
)
```

Then runs a unified query:

```sql
SELECT
    account_id,
    branch_id,
    line,
    (spec->>'type') as account_type,
    (spec->>'year')::int as vintage,
    (embedding <-> reference_embedding) as embedding_distance,
    ST_Distance(location, reference_point) as km_from_ref
FROM account_unified_demo
WHERE
    branch_id = 'BR-CDMX'
    AND (spec->>'type') = 'commercial'
    AND ST_DWithin(location, reference_point, 0.1)
ORDER BY embedding_distance, km_from_ref
LIMIT 5
```

This single query:
- Filters on relational columns (branch_id, line).
- Extracts and filters on JSON (spec->>'type').
- Computes vector distance (embedding <-> reference).
- Computes geospatial distance (ST_Distance, ST_DWithin).

One query, four data types, one execution plan.

## What you just did

You built a single table carrying all four data models and ran a unified query that uses them all together.
No sync between systems, no consistency gaps, no application-layer glue code. One database.

Check the numbers against [`expected.md`](expected.md), and if anything went sideways, [`faq.md`](faq.md) has the common causes.
