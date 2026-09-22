# SQL you already know, instructions

Run these on your own branch. If you haven't done [`../../00-setup/`](../../00-setup/), do that first; you need `LB_PROFILE`, `LB_PROJECT`, `LB_BRANCH`, and `LB_SCHEMA` set, and the factory loaded.

Everything here is a single script you can read: [`../../common/scripts/pg_sql_parity.py`](../../common/scripts/pg_sql_parity.py). You can run it end to end, or follow the steps by hand to see each piece.

## Run it end to end

```bash
cd common/scripts
python pg_sql_parity.py
```

This walks through the entire journey and prints results. Read on for what each step does; the exact output to expect is in [`expected.md`](expected.md).

## Or step through it by hand

### Step 1, inspect the BOM data model

First, look at the schema and a sample of the bill of materials:

```bash
python lakebase.py --sql \
  "SELECT parent_id, child_part, qty FROM factory.bom_edge LIMIT 5"
```

This shows the edges of the tree: parent (a product or part) → child (always a part) with a quantity multiplier. The edges are where CONNECT BY / recursive CTE magic lives.

### Step 2, window functions: rank machines by health

Window functions run in Postgres exactly as they do in Oracle. Here's a simple one: rank all machines by health, showing each machine's health alongside the rank:

```bash
python pg_sql_parity.py --step window
```

The script runs:

```sql
SELECT machine_id, plant_id, health_pct,
       ROW_NUMBER() OVER (ORDER BY health_pct DESC) as rank,
       RANK() OVER (ORDER BY health_pct DESC) as rank_with_ties,
       LAG(health_pct, 1) OVER (ORDER BY health_pct DESC) as prev_health
  FROM factory.machine
 ORDER BY health_pct DESC
 LIMIT 10;
```

This is the same `ROW_NUMBER()`, `RANK()`, and `LAG()` you already use. No migration needed.

### Step 3, recursive CTE: explode the BOM

Now the meaty one. A recursive CTE builds a tree by starting at a root and recursively following edges. Here, we start with a product (e.g., PRD-GEARBOX-X1) and traverse to every child part, multiplying quantities as we go:

```bash
python pg_sql_parity.py --step bom
```

The script runs (against a product you specify):

```sql
WITH RECURSIVE bom_tree AS (
  -- Anchor: start with the product
  SELECT parent_id, child_part, qty as multiplier, 1 as depth
    FROM factory.bom_edge
   WHERE parent_id = 'PRD-GEARBOX-X1'

  UNION ALL

  -- Recursive: traverse child → grandchild, multiply quantities
  SELECT e.parent_id, e.child_part, t.multiplier * e.qty, t.depth + 1
    FROM factory.bom_edge e
    JOIN bom_tree t ON e.parent_id = t.child_part
   WHERE t.depth < 10  -- limit recursion depth to prevent infinite loops
)
SELECT child_part, multiplier, depth
  FROM bom_tree
 ORDER BY depth, child_part;
```

Output shows every part in the BOM (from top-level subassembly down to leaf parts) with the cumulative quantity needed.

### Step 4, Oracle idiom map

Window functions are identical. Recursive CTEs replace CONNECT BY. And a few other common Oracle idioms map directly to Postgres:

- **ROWNUM → LIMIT**: `SELECT * FROM table WHERE ROWNUM <= 10` becomes `SELECT * FROM table LIMIT 10`
- **NVL → COALESCE**: `NVL(col, default)` is just `COALESCE(col, default)` (they're identical in Postgres)
- **SYSDATE → now()**: `SYSDATE` becomes `now()` (or `CURRENT_TIMESTAMP`)
- **CONNECT BY → WITH RECURSIVE**: the tree query above

These are the core pieces. Run them:

```bash
python pg_sql_parity.py --step idioms
```

This runs a few quick examples of each and prints the results. Check them against [`expected.md`](expected.md) to confirm the shapes match.

## What you just did

You wrote window functions, a recursive CTE, and mapped a few Oracle idioms to Postgres. The recursive CTE is the most complex, it's different syntactically from CONNECT BY, but it's also more explicit (you write out the anchor and the recursion rule), which makes it easier to reason about. Window functions are straight ports; the only mental work is remembering that they run in Postgres the same as anywhere else. No surprises.
