# JSON documents, instructions

## How to run this journey

There are a few ways to work through the steps. Pick one:

- **Notebook, step by step (recommended for learning):** open [`pg_json.ipynb`](pg_json.ipynb) and run one cell at a time. Reading each result before the next step is where the learning happens.
- **In a Databricks workspace:** import [`pg_json_databricks.py`](pg_json_databricks.py) and run it cell by cell there.
- **By hand:** follow the numbered steps below, copying each command yourself.
- **Just see it work:** run `python pg_json.py` from this folder to execute the whole thing at once. Fast, but you learn the most from the notebook.

Run these on your own branch. If you haven't done [`../../00-setup/`](../../00-setup/), do that first; you need `LB_PROFILE`, `LB_PROJECT`, `LB_BRANCH`, and `LB_SCHEMA` set, and the bank loaded.

Everything here is a single script you can read: [`./pg_json.py`](./pg_json.py). You can run it end to end, or follow the steps by hand to see each piece.

## Run it end to end

```bash
cd journeys/pg-json
python pg_json.py
```

This walks through the entire journey and prints results. Read on for what each step does; the exact output to expect is in [`expected.md`](expected.md).

## Or step through it by hand

### Step 1, inspect JSONB specs on instruments

First, look at the spec sheets (JSONB) that different instruments carry:

```bash
python ../../common/scripts/lakebase.py --sql \
  "SELECT instrument_id, name, spec FROM bank.instrument LIMIT 3"
```

Each instrument has a `spec` column (JSONB). The contents vary: one instrument might have `{"ticker": "QTZL", "sector": "tech", "beta": 1.2}`, another might have `{"tenor": "10Y", "coupon": 4.0, "rating": "AAA"}`. No schema migration needed when a new instrument type arrives with new fields.

### Step 2, use containment operator (@>)

The `@>` operator asks "does the JSON document on the left contain the JSON sub-document on the right?" This is the workhorse for spec matching. Find instruments that match a spec:

```bash
python pg_json.py --step contains
```

The script runs:

```sql
SELECT instrument_id, name, spec
  FROM bank.instrument
 WHERE spec @> '{"sector": "tech"}'
 LIMIT 5;
```

This finds all instruments whose spec contains `"sector": "tech"`. The match is semantic, not string-based: `{"ticker": "QTZL", "sector": "tech", "beta": 1.2}` matches because it contains the sub-document `{"sector": "tech"}`.

### Step 3, use path extraction (#>>)

The `#>>` operator extracts a value from a path in the JSON. Use it to extract a field for filtering or display:

```bash
python pg_json.py --step extract
```

The script runs:

```sql
SELECT instrument_id, name, spec #>> '{sector}' as sector
  FROM bank.instrument
 WHERE spec ? 'sector'
 LIMIT 5;
```

The `#>> '{sector}'` extracts the value of the `sector` key as text. The `?` operator checks if a key exists. Together, they let you filter and display JSON fields like columns.

### Step 4, create a GIN index

JSONB queries are fast even without an index. With a [GIN](../../docs/glossary.md) (Generalized Inverted Index) on the JSONB column, they're faster. Create an index:

```bash
python pg_json.py --step index
```

The script creates:

```sql
CREATE INDEX IF NOT EXISTS idx_instrument_spec_gin ON bank.instrument
  USING gin(spec jsonb_path_ops);
```

This index accelerates `@>` queries (the containment checks). Run a query before and after and compare; you'll likely see no visible difference on small datasets, but on large datasets (millions of instruments) the difference is night and day.

### Step 5, screening query

Write a realistic query: "which instruments are equities in the tech sector?" or "which bonds are rated AAA?":

```bash
python pg_json.py --step screening
```

The script runs:

```sql
SELECT instrument_id, name, spec
  FROM bank.instrument
 WHERE spec @> '{"sector": "tech"}'
   AND kind = 'equity'
 LIMIT 10;
```

This finds instruments with kind 'equity' and a spec that contains sector 'tech'. A single query, no app code to filter rows.

## What you just did

You loaded JSONB specs, queried them with `@>` (containment), extracted fields with `#>>`, and created a GIN index. The specs are flexible, each instrument documents exactly what it has, and Postgres answers screening questions at database speed. No separate document store to run, sync, or govern.
