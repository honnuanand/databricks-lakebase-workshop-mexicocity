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

## "table factory.bom_edge does not exist"

The factory schema was not loaded during setup. Go back to [`../../00-setup/`](../../00-setup/) and run the load-factory step.

## The recursive CTE is taking a long time

If the recursion hits a circular edge (e.g., part A contains part B, and part B contains part A), the query can run away. The script limits recursion to 10 levels; if your BOM has deeper structures, you may need to increase the limit. Add a WHERE clause to the recursion rule to enforce a maximum depth:

```sql
WHERE t.depth < 15   -- increase from 10 if your BOM is deeper
```

If you suspect circular edges, check for them directly:

```sql
-- Find parts that reference themselves transitively
WITH RECURSIVE find_cycles AS (
  SELECT parent_id, child_part, 0 as depth
    FROM factory.bom_edge
  UNION ALL
  SELECT f.parent_id, e.child_part, f.depth + 1
    FROM factory.bom_edge e
    JOIN find_cycles f ON e.parent_id = f.child_part
   WHERE f.depth < 20
)
SELECT DISTINCT parent_id, child_part FROM find_cycles WHERE parent_id = child_part;
```

If this returns rows, those edges create cycles.

## Why is window function performance the same as Oracle but the syntax different?

The performance is identical because both systems use the same algorithmic approach: a sort or hash aggregation, then a window computation pass. The syntax difference (OVER vs OVER) is superficial. Postgres' window functions are fully featured: PARTITION BY, ORDER BY, ROWS/RANGE frames, the full set of aggregate functions, and ranking functions. No compromises.

## Should I use CONNECT BY syntax if I'm migrating from Oracle?

No. Postgres does not support CONNECT BY. If you're migrating a CONNECT BY query from Oracle, convert it to a recursive CTE. The conversion is mechanical: the anchor part of CONNECT BY becomes the anchor SELECT of the recursive CTE, and the recursive part (START WITH ... CONNECT BY ...) becomes the UNION ALL recursion rule. Once you've done it a few times, it becomes intuitive.

## What about MERGE in PG 16?

MERGE is now available in Postgres 16+. It lets you write upserts (INSERT or UPDATE based on whether the row already exists) in one statement:

```sql
MERGE INTO factory.machine m
USING new_machines nm
  ON m.machine_id = nm.machine_id
WHEN MATCHED THEN
  UPDATE SET health_pct = nm.health_pct, status = nm.status
WHEN NOT MATCHED THEN
  INSERT (machine_id, plant_id, line, type, status, health_pct)
    VALUES (nm.machine_id, nm.plant_id, nm.line, nm.type, nm.status, nm.health_pct);
```

This is much cleaner than the old "INSERT on conflict UPDATE" pattern. Check the Postgres version in use: `SELECT version()`. If it's 16 or later, you can use MERGE. If earlier, stick with INSERT ... ON CONFLICT DO UPDATE.

## Does this journey cover CTEs (WITH)?

Yes, indirectly. Recursive CTEs are built on top of regular CTEs (WITH clauses). A regular CTE is non-recursive:

```sql
WITH healthy_machines AS (
  SELECT machine_id, health_pct
    FROM factory.machine
   WHERE health_pct > 90.0
)
SELECT * FROM healthy_machines;
```

A recursive CTE adds UNION ALL to loop. Both are CTEs; the recursion is what makes it recursive. CTEs are hugely useful for breaking up complex queries and improving readability. Use them liberally.

## Can I use Window Functions in WHERE clauses?

No. Window functions can only appear in SELECT or ORDER BY. If you need to filter based on a window function result (e.g., "only rows where ROW_NUMBER() = 1"), use a subquery:

```sql
SELECT *
  FROM (
    SELECT machine_id, health_pct,
           ROW_NUMBER() OVER (ORDER BY health_pct DESC) as rank
      FROM factory.machine
  ) sub
 WHERE rank <= 10;
```

Or better, use a CTE:

```sql
WITH ranked AS (
  SELECT machine_id, health_pct,
         ROW_NUMBER() OVER (ORDER BY health_pct DESC) as rank
    FROM factory.machine
)
SELECT * FROM ranked WHERE rank <= 10;
```
