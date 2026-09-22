# One query, every type, expected results

Use this to check your run. Numbers are representative; exact values vary with random data generation.
The key: one query, one result set, unified data from all four types.

## Setup

```text
Created machine_unified_demo with 1000 machines (relational + JSON + vector + geo)
```

## Query results

```text
One SELECT spanning relational + JSON + vector + geo:

Query:
SELECT
    machine_id,
    plant_id,
    line,
    (spec->>'type') as machine_type,
    (spec->>'year')::int as manufacture_year,
    (embedding <-> reference_embedding)::numeric(6,4) as embedding_distance,
    ST_Distance(location, reference_point) * 111.0 as km_from_ref
FROM machine_unified_demo
WHERE
    plant_id = 'PL-DETROIT'
    AND (spec->>'type') = 'Press'
    AND ST_DWithin(location, reference_point, 0.1)
ORDER BY embedding_distance, km_from_ref
LIMIT 5

Results (single query, single plan):
  M-0042 | PL-DETROIT | Stamping-A | Press | 2021 | dist=0.0123 | km=0.0234
  M-0089 | PL-DETROIT | Stamping-A | Press | 2023 | dist=0.0167 | km=0.0456
  M-0156 | PL-DETROIT | Stamping-B | Press | 2022 | dist=0.0198 | km=0.0678

✓ All four data models (relational, JSON, vector, geo) in one query
✓ One execution plan, one snapshot, one transaction
```

## EXPLAIN plan

```text
EXPLAIN shows single plan across all types:
  Seq Scan on machine_unified_demo
    Filter: (plant_id = 'PL-DETROIT') AND ((spec->>'type') = 'Press') AND st_dwithin(location, ...
```

One plan, four filters. Not four sub-queries stitched together.

## Full run

```text
1. Creating unified table (relational + JSON + vector + geo):
Created machine_unified_demo with 1000 machines (relational + JSON + vector + geo)

2. Running the unified query:
One SELECT spanning relational + JSON + vector + geo:

Query:
[SQL query shown above]

Results (single query, single plan):
  M-0042 | PL-DETROIT | Stamping-A | Press | 2021 | dist=0.0123 | km=0.0234
  M-0089 | PL-DETROIT | Stamping-A | Press | 2023 | dist=0.0167 | km=0.0456
  M-0156 | PL-DETROIT | Stamping-B | Press | 2022 | dist=0.0198 | km=0.0678

✓ All four data models (relational, JSON, vector, geo) in one query
✓ One execution plan, one snapshot, one transaction

3. EXPLAIN shows single plan across all types:
  Seq Scan on machine_unified_demo
    Filter: (plant_id = 'PL-DETROIT') AND ((spec->>'type') = 'Press') AND st_dwithin(...)

✓ Not four products. One database.
```

## The numbers that matter

| What | Metric | Significance |
| ---- | ------ | ------------ |
| Rows returned | 3 | All four filters applied in one query |
| Query plans | 1 | No sub-query orchestration |
| Consistency | 1 snapshot | No cross-system sync gaps |
| Data types united | 4 | relational + JSON + vector + geo |

> **From the field**
> This is why Postgres scales to so many workloads. It's not a "relational database that can kinda do JSON."
> It's one engine that treats JSON, vectors, and geography as first-class types, indexes them natively,
> and lets the planner optimize a query using any or all of them. You don't need a relational database,
> a separate JSON service, a vector database, and a geospatial engine. One instance, one schema, one
> query language, one transaction.
