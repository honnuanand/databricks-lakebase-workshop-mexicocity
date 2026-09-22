# Tune the planner, FAQ

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

## The estimate still looks bad after CREATE STATISTICS

Make sure you ran `ANALYZE` after creating the statistics. The script does this automatically
with `--step stats`, but if you ran the raw SQL, don't forget:

```sql
ANALYZE machine_perf_demo
```

If you did run `ANALYZE` and the estimate is still off, try:

```sql
DROP STATISTICS factory.machine_perf_stat
ANALYZE machine_perf_demo
```

Then create the statistics again. Occasionally the planner needs a fresh start.

## Why is the estimate still not exact?

Postgres uses statistical sampling, not an exact count. The planner's row estimates are never
exact, they're *educated guesses* based on statistics. An estimate that's within 10-20% is
considered good. The journey shows a 2-3× improvement from "badly wrong" to "accurate enough."

## Why does the planner assume columns are independent?

Without statistics about dependencies, the planner has to make assumptions. Independence is the
safest assumption (it assumes no correlation), so that's the default. `CREATE STATISTICS`
lets you teach it otherwise.

## Can I create statistics on more than two columns?

Yes. The syntax is:

```sql
CREATE STATISTICS stats_name ON col1, col2, col3, col4 FROM table
```

Useful when three or more columns are heavily correlated and a filter on all of them is common.

## Does CREATE STATISTICS have any maintenance cost?

Almost none. Statistics are metadata about distributions; they don't take much space. Each
`ANALYZE` re-computes them, which is fast (sampling the table). You typically run `ANALYZE`
once after loading, and then periodically as the data changes (daily, weekly, depending on
workload).

## How does this compare to adding an index?

Different tools, same goal (speed the query):
- **Index**: tells the planner a faster *path* exists (e.g., "use btree on this column").
- **Statistics**: tells the planner the *cost model* is wrong, so it makes better decisions
  on joins and memory.

Both matter. This journey is about statistics; [`../pg-index/`](../pg-index/) covers indexes.

## This is a solo factory machine table. In production, do I really need this?

Yes. In any production system, you'll have multi-column filters on correlated attributes. Plant
and line are one example; others include region and country, customer-segment and product-line,
time-of-day and traffic-pattern. Whenever one column's values determine another's, teach the
planner with statistics.
