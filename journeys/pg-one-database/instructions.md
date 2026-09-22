# One query, every type, instructions

Run these on your own branch. If you haven't done [`../../00-setup/`](../../00-setup/), do that first.

Everything here is a single script: [`../../common/scripts/pg_one_database.py`](../../common/scripts/pg_one_database.py).

## Run it end to end

```bash
cd common/scripts
python pg_one_database.py
```

This builds a unified table with all four data types and runs a single query across them. Read on for
what each step does; the exact output is in [`expected.md`](expected.md).

## Or step through it by hand

### Step 1, create unified table

```bash
python pg_one_database.py --step sql
```

Shows (without running) the setup SQL that creates the unified table and populates it with 1000 machines.

### Step 2, build and query

```bash
python pg_one_database.py
```

Creates the table:

```sql
CREATE TABLE machine_unified_demo (
    machine_id TEXT PRIMARY KEY,
    plant_id TEXT NOT NULL,
    line TEXT NOT NULL,
    spec JSONB,                      -- JSON data type
    embedding VECTOR(64),             -- pgvector embedding
    location GEOMETRY(POINT, 4326)    -- geospatial point
)
```

Then runs a unified query:

```sql
SELECT
    machine_id,
    plant_id,
    line,
    (spec->>'type') as machine_type,
    (spec->>'year')::int as manufacture_year,
    (embedding <-> reference_embedding) as embedding_distance,
    ST_Distance(location, reference_point) as km_from_ref
FROM machine_unified_demo
WHERE
    plant_id = 'PL-DETROIT'
    AND (spec->>'type') = 'Press'
    AND ST_DWithin(location, reference_point, 0.1)
ORDER BY embedding_distance, km_from_ref
LIMIT 5
```

This single query:
- Filters on relational columns (plant_id, line).
- Extracts and filters on JSON (spec->>'type').
- Computes vector distance (embedding <-> reference).
- Computes geospatial distance (ST_Distance, ST_DWithin).

One query, four data types, one execution plan.

## What you just did

You built a single table carrying all four data models and ran a unified query that uses them all together.
No sync between systems, no consistency gaps, no application-layer glue code. One database.

Check the numbers against [`expected.md`](expected.md), and if anything went sideways, [`faq.md`](faq.md) has the common causes.
