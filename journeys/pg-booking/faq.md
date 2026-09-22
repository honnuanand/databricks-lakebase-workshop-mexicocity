# No double-booking, FAQ

## It failed with a "refresh token" or authentication error

Your Databricks login expired. Re-run the login from [`../../00-setup/auth.md`](../../00-setup/auth.md):

```bash
databricks auth login --host https://<your-workspace>.cloud.databricks.com --profile workshop
```

Then re-run the step.

## "Missing required env var LB_PROJECT / LB_BRANCH"

You're in a terminal that didn't load your environment. Re-source it:

```bash
source workshop.env
```

## "table factory.operation does not exist"

The factory schema was not loaded. Go back to [`../../00-setup/`](../../00-setup/) and run the load-factory step.

## btree_gist extension not found

Create it:

```sql
CREATE EXTENSION IF NOT EXISTS btree_gist;
```

This extension is required for GiST exclusion constraints on data types like integers and timestamps.

## The constraint was created, but overlapping inserts are not being rejected

Check that the constraint exists:

```sql
SELECT constraint_name FROM information_schema.table_constraints
  WHERE table_name = 'operation' AND constraint_type = 'EXCLUDE';
```

If it doesn't exist, the CREATE CONSTRAINT command may have failed silently. Try again, ensuring btree_gist is enabled. Also check that starts_at and ends_at are TIMESTAMPTZ (not just TIMESTAMP); the tstzrange type requires timestamp with time zone.

## I need to delete a row to make space for a new overlapping operation. Is that allowed?

Yes. The constraint only prevents two rows from coexisting with overlapping ranges. You can delete one and insert another:

```sql
DELETE FROM factory.operation WHERE op_id = 'OP-1';
INSERT INTO factory.operation (...) VALUES (...);  -- overlapping with where OP-1 was is now OK
```

But this requires a transaction that first deletes then inserts. Concurrent requests can't race this way because one must complete before the other starts.

## Can I use exclusion constraints on other data types?

Yes. Common use cases:
- **IP ranges**: `EXCLUDE USING gist (inet_column WITH &&)`
- **Geometric regions**: `EXCLUDE USING gist (geom_column WITH &&)`
- **Numeric ranges**: `EXCLUDE USING gist (numrange_column WITH &&)`

The `btree_gist` extension provides GiST operators for many types. Check the Postgres docs for your specific type.

## What if I want "no overlap except for the same operation"?

Add an exclusion condition:

```sql
ALTER TABLE factory.operation
  ADD CONSTRAINT no_machine_overlap
  EXCLUDE USING gist (machine_id WITH =, tstzrange(starts_at, ends_at) WITH &&)
  WHERE (status != 'cancelled');  -- don't exclude cancelled operations
```

This allows cancelled operations to have overlaps (since they won't actually run).

## The exclusion constraint doesn't allow *any* overlap. I need "non-overlapping but adjacent is OK" (e.g., 2-3pm and 3-4pm on the same day).

Use `<>` (strictly overlapping) instead of `&&` (overlapping or adjacent):

```sql
EXCLUDE USING gist (machine_id WITH =, tstzrange(starts_at, ends_at) WITH <>)
```

Actually, Postgres doesn't have `<>` for ranges in the exclusion context. Instead, use:

```sql
EXCLUDE USING gist (machine_id WITH =, tstzrange(starts_at, ends_at, '[)') WITH &&)
```

The `[)` makes the range left-closed, right-open, so `[3pm, 4pm)` and `[4pm, 5pm)` don't overlap. Verify this works for your use case.

## Can I have multiple exclusion constraints on the same table?

Yes. Each constraint is independent:

```sql
ALTER TABLE factory.operation
  ADD CONSTRAINT no_machine_overlap
  EXCLUDE USING gist (machine_id WITH =, tstzrange(starts_at, ends_at) WITH &&),
  ADD CONSTRAINT no_operator_overlap
  EXCLUDE USING gist (operator_id WITH =, tstzrange(starts_at, ends_at) WITH &&);
```

But this is rarely needed. Usually one exclusion constraint is enough.

## Performance: do exclusion constraints slow down writes?

Slightly, but negligibly. The constraint check is a GiST index lookup, which is O(log n) for n rows. For typical operation tables (thousands to tens of thousands of rows), this is < 1 millisecond. The guarantee of correctness is worth the cost.
