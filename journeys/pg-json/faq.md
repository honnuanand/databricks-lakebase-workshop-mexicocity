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

## "table bank.instrument does not exist" or spec column is NULL

The bank schema was not loaded, or the instrument specs were not seeded. Go back to [`../../00-setup/`](../../00-setup/) and run the load-bank step. If the column exists but contains NULLs, update a few rows with test specs:

```sql
UPDATE bank.instrument SET spec = '{"sector": "tech", "beta": 1.2}'
  WHERE instrument_id = 'INS-AAPL';
```

## What's the difference between ->> and #>>?

- **`->`** returns JSONB (Postgres JSON type). Use it when you want to chain operations or work with nested structures.
- **`->>`** returns text. Use it when you want to extract a value as a string for filtering or display.
- **`#>>`** is an alias for `->>`; both return text.

Example:

```sql
SELECT spec -> 'sector' FROM bank.instrument;  -- returns JSONB '{"sector": "tech"}'
SELECT spec ->> 'sector' FROM bank.instrument; -- returns text 'tech'
SELECT spec #>> '{sector}' FROM bank.instrument; -- same as ->> ; also returns text 'tech'
```

## Can I create an index on a path inside the JSON?

Yes. Instead of indexing the entire JSONB column, you can index a specific path:

```sql
CREATE INDEX idx_instrument_spec_sector ON bank.instrument
  USING gin((spec #>> '{sector}'));
```

This indexes just the sector field as text. Use this when you have a few hot query paths that dominate your workload.

## What if my JSON has nested objects (e.g., `{"properties": {"rating": "AAA"}}`)?

Postgres handles nested JSON naturally. Extract nested values with path arrays:

```sql
SELECT spec #>> '{properties, rating}' FROM bank.instrument;
```

This extracts the rating from the properties object. The path is an array of keys: `'{properties, rating}'`.

## How do I check if a JSON key exists?

Use the `?` operator:

```sql
SELECT * FROM bank.instrument WHERE spec ? 'sector';
```

This returns rows where the spec has a top-level key named 'sector'. For nested keys:

```sql
SELECT * FROM bank.instrument WHERE spec -> 'properties' ? 'rating';
```

## Can I update a specific field in JSONB without rewriting the whole document?

Yes, use the `||` (merge) operator or the `jsonb_set()` function:

```sql
-- Merge (shallow; overwrites matching keys at top level)
UPDATE bank.instrument SET spec = spec || '{"sector": "energy"}'
  WHERE instrument_id = 'INS-AAPL';

-- jsonb_set (deep; set a specific path)
UPDATE bank.instrument SET spec = jsonb_set(spec, '{sector}', '"energy"')
  WHERE instrument_id = 'INS-AAPL';
```

The `||` operator is simpler for top-level updates. Use `jsonb_set()` for nested paths.

## Why doesn't JSONB work like a document store (e.g., MongoDB)?

It does, mostly. But Postgres is optimized for relational queries, not document queries. If you need heavy document operations (frequent schema changes, ad-hoc queries on nested structures), a document store might be a better fit. But for [OLTP](../../docs/glossary.md) (online transaction processing) systems where you need a mix of relational and flexible data, JSONB is a great middle ground: you get relational performance, ACID guarantees, and schema flexibility in one system.

## Do I need to manually vacuum JSONB columns?

No. Postgres handles that automatically (unless you have autovacuum turned off, which you shouldn't). JSONB is stored like any other column; the same vacuuming process reclaims dead versions.
