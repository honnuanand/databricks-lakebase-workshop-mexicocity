# Watch the planner, FAQ

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

## The planner didn't flip to Index Scan after I added the index

Check that the index was created:

```sql
SELECT indexname FROM pg_indexes WHERE tablename = 'txn_history';
```

If it's missing, the CREATE INDEX command may have failed. Try again.

Also check that statistics were updated:

```sql
ANALYZE bank.txn_history;
```

The planner makes decisions based on statistics (row counts, selectivity). If statistics are stale, the planner might still choose Seq Scan. After ANALYZE, re-run EXPLAIN.

## The query is still slow even with the index

The planner might have chosen a different plan because the query selectivity is low. If the filter matches many rows (e.g., account_id = 'ACCT-100010' matches 25% of all rows), a Seq Scan can be faster than an Index Scan + random I/O.

Check EXPLAIN to see what the planner chose and why. If EXPLAIN shows the index is not being used, you can force it:

```sql
SET enable_seqscan = off;
SELECT COUNT(*) FROM bank.txn_history WHERE account_id = 'ACCT-100010';
```

This disables sequential scans, forcing the planner to use the index. If the query is still slow, the index isn't helping (and you might not need it).

## How do I read a query plan?

A query plan is a tree. Each node is an operation. Read from the bottom up (the innermost, most specific operation first). For example:

```
Seq Scan on txn
  Filter: (account_id = 'ACCT-100240')
```

This means: "Seq Scan the entire table, then apply a Filter."

For a more complex plan with joins:

```
Nested Loop
  -> Seq Scan on machine
  -> Index Scan on txn
       Index Cond: (account_id = ...)
```

This means: "For each row from the machine table, do an Index Scan on txn."

## What does "cost" mean in EXPLAIN?

Cost is a planner unit (not milliseconds). It's an estimate of the relative expense of a plan. Lower cost means the planner thinks it will be faster. The actual cost is a combination of:
- `startup_cost`: cost before the first row is returned
- `total_cost`: cost to return all rows

For optimization, compare the total_cost of different plans and pick the one with lower cost.

## What's the difference between EXPLAIN and EXPLAIN ANALYZE?

- **EXPLAIN**: shows the plan the planner chose. No actual execution; it's just the plan, not the real numbers.
- **EXPLAIN ANALYZE**: executes the query and shows actual execution time, actual rows, and buffer stats. This is what you use to verify the plan is good.

Use EXPLAIN for quick "what plan will it choose?" and EXPLAIN ANALYZE for "how long did it actually take?"

## The BUFFERS line says "Shared Hit" vs "Shared Read". What's the difference?

- **Shared Hit**: the page was in the shared buffer cache, so no disk I/O was needed.
- **Shared Read**: the page had to be read from disk.

A plan with mostly "Hit" is good (data was cached). A plan with many "Read" means slow disk I/O.

## Can I save the EXPLAIN output for later analysis?

Yes. Use FORMAT JSON:

```sql
EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) SELECT COUNT(*) FROM txn WHERE account_id = 'ACCT-100240';
```

This returns JSON, which you can pipe to a file or tool for later analysis. Tools like PEV (postgres explain visualizer) and depesz can parse and visualize the plan.

## How do I know if an index is actually being used?

Look at EXPLAIN. If you see "Index Scan" (or "Index Only Scan"), the index is being used. If you see "Seq Scan", it's not.

If an index exists but isn't being used, either:
1. The planner thinks a Seq Scan is faster (might be right; check the cost).
2. The query is not selective enough (filtering matches too many rows).
3. Statistics are stale (run ANALYZE).

## Can I use EXPLAIN to check a query without running it (no side effects)?

Yes. EXPLAIN shows the plan without executing. But EXPLAIN ANALYZE *does* execute the query. If the query has side effects (INSERT, UPDATE, DELETE), wrap it in a transaction you can roll back:

```sql
BEGIN;
EXPLAIN ANALYZE INSERT INTO table VALUES (...);
ROLLBACK;
```

This shows the plan and execution but doesn't commit the changes.
