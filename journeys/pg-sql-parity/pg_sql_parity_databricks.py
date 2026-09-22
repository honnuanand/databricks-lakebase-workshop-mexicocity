# Databricks notebook source
# MAGIC %md
# MAGIC # SQL you already know, step by step
# MAGIC
# MAGIC A hands-on lab. Run one cell at a time, read what happened, then move on. You will master window functions, recursive CTEs, and the Oracle-to-Postgres idiom map using a real bill-of-materials explosion.
# MAGIC
# MAGIC Each step shows the real interface: SQL where the step is a query, and Python for control operations.
# MAGIC
# MAGIC **Before you start:** finish `00-setup/` so `LB_PROFILE`, `LB_PROJECT`, `LB_BRANCH`, `LB_SCHEMA` are set and the factory is loaded on your branch.

# COMMAND ----------

# MAGIC %md
# MAGIC ## Setup, connect to your branch
# MAGIC
# MAGIC The shared helper lives in `common/scripts/`.

# COMMAND ----------

import os, sys
sys.path.insert(0, os.path.join(os.getcwd(), "..", "..", "common", "scripts"))
from lakebase import connect, run_sql

SCHEMA = os.environ.get("LB_SCHEMA", "factory")
print("connected; schema:", SCHEMA)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 1, inspect the BOM data model
# MAGIC
# MAGIC The `bom_edge` table stores edges in a tree: each row says "part X contains part Y, with quantity Q". The SQL:
# MAGIC
# MAGIC ```sql
# MAGIC SELECT parent_id, child_part, qty FROM factory.bom_edge LIMIT 5
# MAGIC ```

# COMMAND ----------

sql = "SELECT parent_id, child_part, qty FROM factory.bom_edge LIMIT 5"
rows = run_sql(sql)
print("BOM edges (parent -> child with qty):")
for row in rows:
    print(f"  {row}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 2, window functions rank machines by health
# MAGIC
# MAGIC Use ROW_NUMBER(), RANK(), and LAG() to rank machines by health. The OVER clause defines the window. The SQL:
# MAGIC
# MAGIC ```sql
# MAGIC SELECT machine_id, plant_id, health_pct,
# MAGIC        ROW_NUMBER() OVER (ORDER BY health_pct DESC) as rank,
# MAGIC        RANK() OVER (ORDER BY health_pct DESC) as rank_with_ties,
# MAGIC        LAG(health_pct, 1) OVER (ORDER BY health_pct DESC) as prev_health
# MAGIC   FROM factory.machine
# MAGIC  ORDER BY health_pct DESC
# MAGIC  LIMIT 10
# MAGIC ```

# COMMAND ----------

sql = """
SELECT machine_id, plant_id, health_pct,
       ROW_NUMBER() OVER (ORDER BY health_pct DESC) as rank,
       RANK() OVER (ORDER BY health_pct DESC) as rank_with_ties,
       LAG(health_pct, 1) OVER (ORDER BY health_pct DESC) as prev_health
  FROM factory.machine
 ORDER BY health_pct DESC
 LIMIT 10
"""
rows = run_sql(sql)
print("Top 10 machines by health (with window functions):")
for row in rows:
    print(f"  {row}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 3, recursive CTE explodes a BOM tree
# MAGIC
# MAGIC A recursive CTE traverses the BOM graph starting from a product, following edges downward and multiplying quantities. This is the equivalent of Oracle's CONNECT BY. The SQL:
# MAGIC
# MAGIC ```sql
# MAGIC WITH RECURSIVE bom_tree AS (
# MAGIC   -- Anchor: start with edges from the product
# MAGIC   SELECT parent_id, child_part, qty as multiplier, 1 as depth
# MAGIC     FROM factory.bom_edge
# MAGIC    WHERE parent_id = %s
# MAGIC
# MAGIC   UNION ALL
# MAGIC
# MAGIC   -- Recursive: traverse child -> grandchild, multiply quantities
# MAGIC   SELECT e.parent_id, e.child_part, t.multiplier * e.qty, t.depth + 1
# MAGIC     FROM factory.bom_edge e
# MAGIC     JOIN bom_tree t ON e.parent_id = t.child_part
# MAGIC    WHERE t.depth < 10
# MAGIC )
# MAGIC SELECT child_part, multiplier, depth
# MAGIC   FROM bom_tree
# MAGIC  ORDER BY depth, child_part
# MAGIC ```

# COMMAND ----------

# Find a product to explode
product_rows = run_sql("SELECT product_id FROM factory.product LIMIT 1")
if not product_rows:
    print("No products found; check 00-setup/load-factory.py")
else:
    product_id = product_rows[0][0]
    print(f"Exploding BOM for {product_id}")

    sql = """
    WITH RECURSIVE bom_tree AS (
      SELECT parent_id, child_part, qty as multiplier, 1 as depth
        FROM factory.bom_edge
       WHERE parent_id = %s

      UNION ALL

      SELECT e.parent_id, e.child_part, t.multiplier * e.qty, t.depth + 1
        FROM factory.bom_edge e
        JOIN bom_tree t ON e.parent_id = t.child_part
       WHERE t.depth < 10
    )
    SELECT child_part, multiplier, depth
      FROM bom_tree
     ORDER BY depth, child_part
    """

    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (product_id,))
            rows = cur.fetchall()

    print(f"BOM explosion for {product_id} (first 15 rows):")
    for row in rows[:15]:
        print(f"  part={row[0]}, qty={row[1]}, depth={row[2]}")
    if len(rows) > 15:
        print(f"  ... and {len(rows) - 15} more rows")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 4, Oracle idiom map: ROWNUM to LIMIT
# MAGIC
# MAGIC Postgres uses LIMIT to fetch the first N rows, while Oracle uses WHERE ROWNUM <= N. They are equivalent. The SQL:
# MAGIC
# MAGIC ```sql
# MAGIC SELECT machine_id, health_pct FROM factory.machine LIMIT 3
# MAGIC ```

# COMMAND ----------

sql = "SELECT machine_id, health_pct FROM factory.machine LIMIT 3"
rows = run_sql(sql)
print("LIMIT 3 returns (same as WHERE ROWNUM <= 3 on Oracle):")
for row in rows:
    print(f"  {row}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 5, Oracle idiom map: NVL to COALESCE
# MAGIC
# MAGIC Postgres uses COALESCE(col, default_val) to return a default when a value is NULL. Oracle calls it NVL(). They are equivalent. The SQL:
# MAGIC
# MAGIC ```sql
# MAGIC SELECT machine_id,
# MAGIC        COALESCE(health_pct, 0.0) as health_or_zero
# MAGIC   FROM factory.machine
# MAGIC  LIMIT 3
# MAGIC ```

# COMMAND ----------

sql = """
SELECT machine_id,
       COALESCE(health_pct, 0.0) as health_or_zero
  FROM factory.machine
 LIMIT 3
"""
rows = run_sql(sql)
print("COALESCE(health_pct, 0.0) works the same as NVL():")
for row in rows:
    print(f"  {row}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 6, Oracle idiom map: SYSDATE to now()
# MAGIC
# MAGIC Postgres uses now() (or CURRENT_TIMESTAMP) to get the current timestamp. Oracle uses SYSDATE. They are equivalent. The SQL:
# MAGIC
# MAGIC ```sql
# MAGIC SELECT now() as current_time, CURRENT_TIMESTAMP as alt_form
# MAGIC ```

# COMMAND ----------

sql = "SELECT now() as current_time, CURRENT_TIMESTAMP as alt_form"
rows = run_sql(sql)
if rows:
    print("now() returns:", rows[0][0])
    print("CURRENT_TIMESTAMP also works:", rows[0][1])

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 7, Oracle idiom map: CONNECT BY to WITH RECURSIVE
# MAGIC
# MAGIC We already showed the full BOM explosion in Step 3. Postgres WITH RECURSIVE is more explicit and often faster than Oracle CONNECT BY. The transformation:
# MAGIC
# MAGIC **Oracle (CONNECT BY):**
# MAGIC ```sql
# MAGIC SELECT * FROM bom_edge
# MAGIC  START WITH parent_id = 'PRD-X'
# MAGIC  CONNECT BY parent_id = PRIOR child_part
# MAGIC ```
# MAGIC
# MAGIC **Postgres (WITH RECURSIVE):** See Step 3 above.

# COMMAND ----------

print("Oracle CONNECT BY pattern:")
print("  SELECT * FROM bom_edge START WITH parent_id = 'PRD-X' CONNECT BY parent_id = PRIOR child_part")
print()
print("Postgres WITH RECURSIVE (Step 3) is the equivalent.")
print("It is more explicit: you see the anchor (base case) and recursion (inductive case) clearly.")

# COMMAND ----------

# MAGIC %md
# MAGIC ## What you learned
# MAGIC
# MAGIC You migrated core SQL patterns from Oracle to Postgres: window functions (ROW_NUMBER, RANK, LAG), recursive CTEs for tree traversal, and the idiom map (ROWNUM to LIMIT, NVL to COALESCE, SYSDATE to now(), CONNECT BY to WITH RECURSIVE).
# MAGIC
# MAGIC Next: **JSON documents** stores flexible schema (JSONB) with operators to query and index semi-structured data.
