# SQL you already know, expected results

Use this to check your run. The numbers here are from our measurements; yours will be close but not identical. The *shape* of the results and the general magnitudes are what matter.

## Step 1, holdings data model

```text
('FUND-GROWTH-A', 'INS-CASH-USD', 1)
('FUND-GROWTH-A', 'INS-SLEEVE-EQ', 2)
('FUND-GROWTH-A', 'INS-MSFT', 8)
('INS-SLEEVE-EQ', 'INS-AAPL', 1)
('INS-SLEEVE-EQ', 'INS-UST-10Y', 2)
```

A few rows showing the parent-child-units structure. Each row is an edge in the holdings tree.

## Step 2, window function ranking

```text
account_id    health_pct  rank  rank_with_ties  prev_health
ACCT-100241   99.10        1       1             NULL
ACCT-100234   98.50        2       2             99.10
ACCT-100235   96.20        3       3             98.50
ACCT-200310   94.70        4       4             96.20
ACCT-300420   97.30        ...
```

The `ROW_NUMBER()` gives a unique rank (1, 2, 3...). The `RANK()` would give ties the same rank and skip the next rank. The `LAG()` shows the previous row's health when sorted by health descending. All three are standard Postgres window functions.

## Step 3, holdings explosion (recursive CTE)

Starting from FUND-GROWTH-A, the tree expands down to all leaf instruments:

```text
instrument_id    multiplier  depth
INS-CASH-USD     1           1
INS-SLEEVE-EQ    2           1
INS-MSFT         8           1
INS-AAPL         2           2
INS-UST-10Y      4           2
```

(Your output will have more rows if you seed deeper structures; this is the base tree.) The `multiplier` is the cumulative units: FUND-GROWTH-A holds 2 units of the equity sleeve, and the sleeve holds 2 units of the 10-year Treasury, so the fund is really exposed to 4 units of the Treasury. The multiplier multiplies down the chain.

The `depth` column shows how many levels deep each instrument is. Leaf instruments reached through a sub-fund have higher depths. The recursion stops after 10 levels (to prevent infinite loops on circular structures, though the holdings tree is a clean tree).

## Step 4, Oracle idiom map

```text
1. ROWNUM -> LIMIT:
   SELECT * FROM bank.account LIMIT 3
   (Returns 3 rows, same as WHERE ROWNUM <= 3 on Oracle)

2. NVL -> COALESCE:
   COALESCE(health_pct, 0.0)  -- same as NVL(health_pct, 0.0)

3. SYSDATE -> now():
   now()  -- same as SYSDATE; CURRENT_TIMESTAMP also works

4. CONNECT BY -> WITH RECURSIVE:
   (The holdings explosion above; no equivalent in a single line)
```

## The numbers that matter

| What | Expected | Why it matters |
| ---- | -------- | -------------- |
| Window function execution | < 10 ms for 200 accounts | same as Oracle or SQL Server |
| Recursive CTE (200-line fund) | 40-60 ms | a single query, no app loops |
| Holdings explosion size | 1,000-2,000 underlying positions | a fund-of-funds unwinds to many positions |
| Recursion depth | < 10 for clean structures | deep recursion is rare; check for circular edges |

> **From the field**
> The recursive CTE is the piece that often surprises people migrating from Oracle. It looks verbose (anchor + union all + recursion rule), but that explicitness is a feature: you can see exactly what the query is doing, add WHERE filters at each stage, and reason about depth limits. The performance is often *better* than Oracle's CONNECT BY, especially on large trees, because Postgres can parallelize and push predicates down.
