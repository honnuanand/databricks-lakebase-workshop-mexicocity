# JSON documents, instructions

Run these on your own branch. If you haven't done [`../../00-setup/`](../../00-setup/), do that first; you need `LB_PROFILE`, `LB_PROJECT`, `LB_BRANCH`, and `LB_SCHEMA` set, and the factory loaded.

Everything here is a single script you can read: [`../../common/scripts/pg_json.py`](../../common/scripts/pg_json.py). You can run it end to end, or follow the steps by hand to see each piece.

## Run it end to end

```bash
cd common/scripts
python pg_json.py
```

This walks through the entire journey and prints results. Read on for what each step does; the exact output to expect is in [`expected.md`](expected.md).

## Or step through it by hand

### Step 1, inspect JSONB specs on parts

First, look at the spec sheets (JSONB) that different parts carry:

```bash
python lakebase.py --sql \
  "SELECT part_id, name, spec FROM factory.part LIMIT 3"
```

Each part has a `spec` column (JSONB). The contents vary: one part might have `{"load_capacity_kg": 500, "material": "steel"}`, another might have `{"tensile_strength_mpa": 1200, "coating": "zinc"}`. No schema migration needed when a new part type arrives with new fields.

### Step 2, use containment operator (@>)

The `@>` operator asks "does the JSON document on the left contain the JSON sub-document on the right?" This is the workhorse for spec matching. Find parts that match a spec:

```bash
python pg_json.py --step contains
```

The script runs:

```sql
SELECT part_id, name, spec
  FROM factory.part
 WHERE spec @> '{"material": "steel"}'
 LIMIT 5;
```

This finds all parts whose spec contains `"material": "steel"`. The match is semantic, not string-based: `{"material": "steel", "load_capacity_kg": 500}` matches because it contains the sub-document `{"material": "steel"}`.

### Step 3, use path extraction (#>>)

The `#>>` operator extracts a value from a path in the JSON. Use it to extract a field for filtering or display:

```bash
python pg_json.py --step extract
```

The script runs:

```sql
SELECT part_id, name, spec, spec #>> '{material}' as material
  FROM factory.part
 WHERE spec ? 'material'
 LIMIT 5;
```

The `#>> '{material}'` extracts the value of the `material` key as text. The `?` operator checks if a key exists. Together, they let you filter and display JSON fields like columns.

### Step 4, create a GIN index

JSONB queries are fast even without an index. With a [GIN](../../docs/glossary.md) (Generalized Inverted Index) on the JSONB column, they're faster. Create an index:

```bash
python pg_json.py --step index
```

The script creates:

```sql
CREATE INDEX IF NOT EXISTS idx_part_spec_gin ON factory.part
  USING gin(spec jsonb_path_ops);
```

This index accelerates `@>` queries (the containment checks). Run a query before and after and compare; you'll likely see no visible difference on small datasets, but on large datasets (millions of parts) the difference is night and day.

### Step 5, compliance query

Write a realistic query: "which parts are certified for a harsh-environment spec?" (e.g., temperature range -20 to +80, stainless steel):

```bash
python pg_json.py --step compliance
```

The script runs:

```sql
SELECT part_id, name, spec
  FROM factory.part
 WHERE spec @> '{"material": "stainless", "temp_min_c": -20}'
   AND (spec #>> '{temp_max_c}')::INT >= 80
 LIMIT 10;
```

This finds parts that have a spec with stainless material and a min temp of -20, *and* whose max temp (extracted from the JSON) is >= 80. A single query, no app code to filter rows.

## What you just did

You loaded JSONB specs, queried them with `@>` (containment), extracted fields with `#>>`, and created a GIN index. The specs are flexible, each part documents exactly what it has, and Postgres answers compliance questions at database speed. No separate document store to run, sync, or govern.
