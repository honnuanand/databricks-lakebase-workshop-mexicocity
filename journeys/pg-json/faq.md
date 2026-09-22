# JSON documents, FAQ

## It failed with a "refresh token" or authentication error

Your Databricks login expired. Re-run the login from [`../../00-setup/auth.md`](../../00-setup/auth.md):

```bash
databricks auth login --host https://<your-workspace>.cloud.databricks.com --profile workshop
```

Then re-run the step.

## "Missing required env var LB_PROJECT / LB_BRANCH"

You're in a terminal that didn't load your environment. Re-source it:

```bash
source workshop.env    # the file you built in 00-setup
```

Or re-export `LB_PROFILE`, `LB_PROJECT`, `LB_BRANCH`, `LB_SCHEMA` by hand.

## "table factory.part does not exist" or spec column is NULL

The factory schema was not loaded, or the part specs were not seeded. Go back to [`../../00-setup/`](../../00-setup/) and run the load-factory step. If the column exists but contains NULLs, update a few rows with test specs:

```sql
UPDATE factory.part SET spec = '{"material": "steel", "load_capacity_kg": 500}'
  WHERE part_id = 'PT-BEARING-6204';
```

## What's the difference between ->> and #>>?

- **`->`** returns JSONB (Postgres JSON type). Use it when you want to chain operations or work with nested structures.
- **`->>`** returns text. Use it when you want to extract a value as a string for filtering or display.
- **`#>>`** is an alias for `->>`; both return text.

Example:

```sql
SELECT spec -> 'material' FROM factory.part;  -- returns JSONB '{"material": "steel"}'
SELECT spec ->> 'material' FROM factory.part; -- returns text 'steel'
SELECT spec #>> '{material}' FROM factory.part; -- same as ->> ; also returns text 'steel'
```

## Can I create an index on a path inside the JSON?

Yes. Instead of indexing the entire JSONB column, you can index a specific path:

```sql
CREATE INDEX idx_part_spec_material ON factory.part
  USING gin((spec #>> '{material}'));
```

This indexes just the material field as text. Use this when you have a few hot query paths that dominate your workload.

## What if my JSON has nested objects (e.g., `{"engine": {"horsepower": 300}}`)?

Postgres handles nested JSON naturally. Extract nested values with path arrays:

```sql
SELECT spec #>> '{engine, horsepower}' FROM factory.part;
```

This extracts the horsepower from the engine object. The path is an array of keys: `'{engine, horsepower}'`.

## How do I check if a JSON key exists?

Use the `?` operator:

```sql
SELECT * FROM factory.part WHERE spec ? 'material';
```

This returns rows where the spec has a top-level key named 'material'. For nested keys:

```sql
SELECT * FROM factory.part WHERE spec -> 'properties' ? 'material';
```

## Can I update a specific field in JSONB without rewriting the whole document?

Yes, use the `||` (merge) operator or the `jsonb_set()` function:

```sql
-- Merge (shallow; overwrites matching keys at top level)
UPDATE factory.part SET spec = spec || '{"material": "aluminum"}'
  WHERE part_id = 'PT-SHAFT-A';

-- jsonb_set (deep; set a specific path)
UPDATE factory.part SET spec = jsonb_set(spec, '{material}', '"aluminum"')
  WHERE part_id = 'PT-SHAFT-A';
```

The `||` operator is simpler for top-level updates. Use `jsonb_set()` for nested paths.

## Why doesn't JSONB work like a document store (e.g., MongoDB)?

It does, mostly. But Postgres is optimized for relational queries, not document queries. If you need heavy document operations (frequent schema changes, ad-hoc queries on nested structures), a document store might be a better fit. But for [OLTP](../../docs/glossary.md) (online transaction processing) systems where you need a mix of relational and flexible data, JSONB is a great middle ground: you get relational performance, ACID guarantees, and schema flexibility in one system.

## Do I need to manually vacuum JSONB columns?

No. Postgres handles that automatically (unless you have autovacuum turned off, which you shouldn't). JSONB is stored like any other column; the same vacuuming process reclaims dead versions.
