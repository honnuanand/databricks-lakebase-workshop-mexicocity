# SQL you already know, FAQ

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

## "table bank.holding does not exist"

The bank schema was not loaded during setup. Go back to [`../../00-setup/`](../../00-setup/) and run the load-bank step.

## The recursive CTE is taking a long time

If the recursion hits a circular edge (e.g., sub-fund A holds sub-fund B, and sub-fund B holds sub-fund A), the query can run away. The script limits recursion to 10 levels; if your holdings tree has deeper structures, you may need to increase the limit. Add a WHERE clause to the recursion rule to enforce a maximum depth:

```sql
WHERE t.depth < 15   -- increase from 10 if your fund nests deeper
```

If you suspect circular edges, check for them directly:

```sql
-- Find holdings that reference themselves transitively
WITH RECURSIVE find_cycles AS (
  SELECT parent_id, instrument_id, 0 as depth
    FROM bank.holding
  UNION ALL
  SELECT f.parent_id, h.instrument_id, f.depth + 1
    FROM bank.holding h
    JOIN find_cycles f ON h.parent_id = f.instrument_id
   WHERE f.depth < 20
)
SELECT DISTINCT parent_id, instrument_id FROM find_cycles WHERE parent_id = instrument_id;
```

If this returns rows, those edges create cycles.

## Why is window function performance the same as Oracle but the syntax different?

The performance is identical because both systems use the same algorithmic approach: a sort or hash aggregation, then a window computation pass. The syntax difference (OVER vs OVER) is superficial. Postgres' window functions are fully featured: PARTITION BY, ORDER BY, ROWS/RANGE frames, the full set of aggregate functions, and ranking functions. No compromises.

## Should I use CONNECT BY syntax if I'm migrating from Oracle?

No. Postgres does not support CONNECT BY. If you're migrating a CONNECT BY query from Oracle, convert it to a recursive CTE. The conversion is mechanical: the anchor part of CONNECT BY becomes the anchor SELECT of the recursive CTE, and the recursive part (START WITH ... CONNECT BY ...) becomes the UNION ALL recursion rule. Once you've done it a few times, it becomes intuitive.

## What about MERGE in PG 16?

MERGE is now available in Postgres 16+. It lets you write upserts (INSERT or UPDATE based on whether the row already exists) in one statement:

```sql
MERGE INTO bank.account a
USING new_accounts na
  ON a.account_id = na.account_id
WHEN MATCHED THEN
  UPDATE SET health_pct = na.health_pct, status = na.status
WHEN NOT MATCHED THEN
  INSERT (account_id, branch_id, line, type, status, health_pct)
    VALUES (na.account_id, na.branch_id, na.line, na.type, na.status, na.health_pct);
```

This is much cleaner than the old "INSERT on conflict UPDATE" pattern. Check the Postgres version in use: `SELECT version()`. If it's 16 or later, you can use MERGE. If earlier, stick with INSERT ... ON CONFLICT DO UPDATE.

## Does this journey cover CTEs (WITH)?

Yes, indirectly. Recursive CTEs are built on top of regular CTEs (WITH clauses). A regular CTE is non-recursive:

```sql
WITH healthy_accounts AS (
  SELECT account_id, health_pct
    FROM bank.account
   WHERE health_pct > 90.0
)
SELECT * FROM healthy_accounts;
```

A recursive CTE adds UNION ALL to loop. Both are CTEs; the recursion is what makes it recursive. CTEs are hugely useful for breaking up complex queries and improving readability. Use them liberally.

## Can I use window functions in WHERE clauses?

No. Window functions can only appear in SELECT or ORDER BY. If you need to filter based on a window function result (e.g., "only rows where ROW_NUMBER() = 1"), use a subquery:

```sql
SELECT *
  FROM (
    SELECT account_id, health_pct,
           ROW_NUMBER() OVER (ORDER BY health_pct DESC) as rank
      FROM bank.account
  ) sub
 WHERE rank <= 10;
```

Or better, use a CTE:

```sql
WITH ranked AS (
  SELECT account_id, health_pct,
         ROW_NUMBER() OVER (ORDER BY health_pct DESC) as rank
    FROM bank.account
)
SELECT * FROM ranked WHERE rank <= 10;
```
