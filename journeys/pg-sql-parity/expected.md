# SQL you already know, expected results

Use this to check your run. The numbers here are from our measurements; yours will be close but not identical. The *shape* of the results and the general magnitudes are what matter.

## Step 1, BOM data model

```text
('PRD-GEARBOX-X1', 'PT-SHAFT-A', 4)
('PRD-GEARBOX-X1', 'PT-BEARING-6204', 8)
('PT-SHAFT-A', 'PT-RING-STEEL', 1)
('PT-BEARING-6204', 'PT-CAGE-BRASS', 2)
('PT-CAGE-BRASS', 'PT-FASTENER-M5', 3)
```

A few rows showing the parent-child-quantity structure. Each row is an edge in the BOM tree.

## Step 2, window function ranking

```text
machine_id  health_pct  rank  rank_with_ties  prev_health
M-001       98.50        1       1             NULL
M-203       96.25        2       2             98.50
M-204       91.00        3       3             96.25
M-301       89.75        4       4             91.00
M-405       87.50        5       5             89.75
```

The `ROW_NUMBER()` gives a unique rank (1, 2, 3...). The `RANK()` would give ties the same rank and skip the next rank. The `LAG()` shows the previous row's health when sorted by health descending. All three are standard Postgres window functions.

## Step 3, BOM explosion (recursive CTE)

Starting from PRD-GEARBOX-X1, the tree expands down to all leaf parts:

```text
child_part         multiplier  depth
PT-RING-STEEL      4           2
PT-BEARING-6204    8           2
PT-CAGE-BRASS      16          3
PT-FASTENER-M5     48          4
PT-SEAL-RUBBER     16          3
```

(Your output will have more rows; this is a sample.) The `multiplier` is the cumulative quantity: if the gearbox needs 4 shafts, and each shaft needs 1 ring, then the gearbox needs 4 rings total. If each shaft also needs 2 bearings, the gearbox needs 8 bearings. The multiplier multiplies down the chain.

The `depth` column shows how many levels deep each part is. Leaf parts will have higher depths. The recursion stops after 10 levels (to prevent infinite loops on circular structures, though the factory BOM is a clean tree).

## Step 4, Oracle idiom map

```text
1. ROWNUM → LIMIT:
   SELECT * FROM factory.machine LIMIT 3
   (Returns 3 rows, same as WHERE ROWNUM <= 3 on Oracle)

2. NVL → COALESCE:
   COALESCE(health_pct, 0.0)  -- same as NVL(health_pct, 0.0)

3. SYSDATE → now():
   now()  -- same as SYSDATE; CURRENT_TIMESTAMP also works

4. CONNECT BY → WITH RECURSIVE:
   (The BOM explosion above; no equivalent in a single line)
```

## The numbers that matter

| What | Expected | Why it matters |
| ---- | -------- | -------------- |
| Window function execution | < 10 ms for 200 machines | same as Oracle or SQL Server |
| Recursive CTE (100-part BOM) | 40-60 ms | a single query, no app loops |
| BOM explosion size | 1,000-2,000 leaf parts | typical manufacturing product has many parts |
| Recursion depth | < 10 for clean BOMs | deep recursion is rare; check for circular edges |

> **From the field**
> The recursive CTE is the piece that often surprises people migrating from Oracle. It looks verbose (anchor + union all + recursion rule), but that explicitness is a feature: you can see exactly what the query is doing, add WHERE filters at each stage, and reason about depth limits. The performance is often *better* than Oracle's CONNECT BY, especially on large trees, because Postgres can parallelize and push predicates down.
