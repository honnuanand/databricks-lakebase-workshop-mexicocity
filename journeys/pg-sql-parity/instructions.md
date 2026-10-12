# SQL you already know, instructions

## How to run this journey

There are a few ways to work through the steps. Pick one:

- **Notebook, step by step (recommended for learning):** open [`pg_sql_parity.ipynb`](pg_sql_parity.ipynb) and run one cell at a time. Reading each result before the next step is where the learning happens.
- **In a Databricks workspace:** import [`pg_sql_parity_databricks.py`](pg_sql_parity_databricks.py) and run it cell by cell there.
- **By hand:** follow the numbered steps below, copying each command yourself.
- **Just see it work:** run `python pg_sql_parity.py` from this folder to execute the whole thing at once. Fast, but you learn the most from the notebook.

Run these on your own branch. If you haven't done [`../../00-setup/`](../../00-setup/), do that first; you need `LB_PROFILE`, `LB_PROJECT`, `LB_BRANCH`, and `LB_SCHEMA` set, and the bank loaded.

Everything here is a single script you can read: [`./pg_sql_parity.py`](./pg_sql_parity.py). You can run it end to end, or follow the steps by hand to see each piece.

## Run it end to end

```bash
cd journeys/pg-sql-parity
python pg_sql_parity.py
```

This walks through the entire journey and prints results. Read on for what each step does; the exact output to expect is in [`expected.md`](expected.md).

## Or step through it by hand

### Step 1, inspect the holdings data model

First, look at the schema and a sample of the fund holdings tree:

```bash
python ../../common/scripts/lakebase.py --sql \
  "SELECT parent_id, instrument_id, qty FROM bank.holding LIMIT 5"
```

This shows the edges of the tree: parent (a fund or a sub-fund) to child (an instrument) with a units multiplier. The edges are where CONNECT BY / recursive CTE magic lives.

### Step 2, window functions: rank accounts by health

Window functions run in Postgres exactly as they do in Oracle. Here's a simple one: rank all accounts by health, showing each account's health alongside the rank:

```bash
python pg_sql_parity.py --step window
```

The script runs:

```sql
SELECT account_id, branch_id, health_pct,
       ROW_NUMBER() OVER (ORDER BY health_pct DESC) as rank,
       RANK() OVER (ORDER BY health_pct DESC) as rank_with_ties,
       LAG(health_pct, 1) OVER (ORDER BY health_pct DESC) as prev_health
  FROM bank.account
 ORDER BY health_pct DESC
 LIMIT 10;
```

This is the same `ROW_NUMBER()`, `RANK()`, and `LAG()` you already use. No migration needed.

### Step 3, recursive CTE: explode the holdings tree

Now the meaty one. A recursive CTE builds a tree by starting at a root and recursively following edges. Here, we start with a fund (e.g., FUND-GROWTH-A) and traverse to every underlying instrument, multiplying units as we go:

```bash
python pg_sql_parity.py --step holdings
```

The script runs (against a fund you specify):

```sql
WITH RECURSIVE holdings_tree AS (
  -- Anchor: start with the fund
  SELECT parent_id, instrument_id, qty as multiplier, 1 as depth
    FROM bank.holding
   WHERE parent_id = 'FUND-GROWTH-A'

  UNION ALL

  -- Recursive: traverse holding -> sub-holding, multiply units
  SELECT h.parent_id, h.instrument_id, t.multiplier * h.qty, t.depth + 1
    FROM bank.holding h
    JOIN holdings_tree t ON h.parent_id = t.instrument_id
   WHERE t.depth < 10  -- limit recursion depth to prevent infinite loops
)
SELECT instrument_id, multiplier, depth
  FROM holdings_tree
 ORDER BY depth, instrument_id;
```

Output shows every instrument in the fund (from the top-level line items down to the leaf instruments) with the cumulative units held.

### Step 4, Oracle idiom map

Window functions are identical. Recursive CTEs replace CONNECT BY. And a few other common Oracle idioms map directly to Postgres:

- **ROWNUM to LIMIT**: `SELECT * FROM table WHERE ROWNUM <= 10` becomes `SELECT * FROM table LIMIT 10`
- **NVL to COALESCE**: `NVL(col, default)` is just `COALESCE(col, default)` (they're identical in Postgres)
- **SYSDATE to now()**: `SYSDATE` becomes `now()` (or `CURRENT_TIMESTAMP`)
- **CONNECT BY to WITH RECURSIVE**: the tree query above

These are the core pieces. Run them:

```bash
python pg_sql_parity.py --step idioms
```

This runs a few quick examples of each and prints the results. Check them against [`expected.md`](expected.md) to confirm the shapes match.

## What you just did

You wrote window functions, a recursive CTE, and mapped a few Oracle idioms to Postgres. The recursive CTE is the most complex, it's different syntactically from CONNECT BY, but it's also more explicit (you write out the anchor and the recursion rule), which makes it easier to reason about. Window functions are straight ports; the only mental work is remembering that they run in Postgres the same as anywhere else. No surprises.
