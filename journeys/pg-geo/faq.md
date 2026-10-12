# Geospatial, FAQ

## PostGIS is not available on my Lakebase instance

This is rare. Check by running `CREATE EXTENSION IF NOT EXISTS postgis`. If it fails with "extension not found," contact your Databricks team. In the meantime, you can use Haversine formula (documented in expected.md) as a workaround, though it's much slower and less accurate than PostGIS.

## "type geography does not exist"

PostGIS is installed but the extension isn't loaded into your schema. Run:

```sql
CREATE EXTENSION IF NOT EXISTS postgis CASCADE;
```

This makes the PostGIS types and functions available in your connection.

## My geography column is all NULLs

The branch/custodian/counterparty lat/lon columns are populated during setup, but the geography column might not be created. Create it manually:

```sql
ALTER TABLE bank.branch ADD COLUMN geo GEOGRAPHY(POINT) DEFAULT NULL;
UPDATE bank.branch SET geo = geography(POINT(lon, lat));
ALTER TABLE bank.branch ALTER COLUMN geo SET NOT NULL;
```

Then do the same for custodian and counterparty tables.

## What's the difference between geography and geometry?

- **geography**: distances are great-circle (spherical); accurate for real-world locations. Slower to compute but more correct.
- **geometry**: distances are Euclidean (flat); faster to compute but only accurate for small areas. Use for local coordinates, building floor plans.

For banking and financial operations spanning global markets, use **geography**. It handles datelines, poles, and all the earth's curves correctly.

## ST_DWithin is slow without an index

If you're seeing slow queries, check that the GiST index is actually being used. Run EXPLAIN:

```sql
EXPLAIN SELECT custodian_id FROM bank.custodian c, bank.branch b
 WHERE ST_DWithin(c.geo, b.geo, 100000);
```

Look for "Index Scan" in the output. If you see "Seq Scan", either:
1. The dataset is too small for the index to be worthwhile (< 1000 rows), and the planner chose sequential scan.
2. The index doesn't exist. Create it: `CREATE INDEX idx_custodian_geo ON bank.custodian USING gist(geo);`

## How do I store the distance result for later use?

Distances are computed on-the-fly. To store them, create a table or use a CTE:

```sql
WITH distances AS (
  SELECT custodian_id,
         ST_Distance(geo, <branch_point>) / 1000.0 as distance_km
    FROM bank.custodian
)
SELECT * FROM distances WHERE distance_km < 100;
```

Or insert into a results table:

```sql
INSERT INTO custodian_distances (custodian_id, distance_km)
SELECT custodian_id, ST_Distance(geo, <branch_point>) / 1000.0
  FROM bank.custodian;
```

## Can I query "which counterparties are near multiple branches"?

Yes, if you have branch locations defined in PostGIS. Store branches as geography points and use:

```sql
SELECT counterparty_id FROM bank.counterparty c, bank.branch b
 WHERE ST_DWithin(c.geo, b.geo, 100000)
   AND ST_DWithin(c.geo, <another_branch_point>, 100000);
```

Or use `ST_Intersects` for polygon-based regions. This is beyond the scope of this journey, but it's all native Postgres + PostGIS.

## What if my custodian table has thousands of locations?

The queries scale. A GiST index on a table with 1 million locations is the same speed as 1,000 locations, the index is logarithmic. Nearest-neighbor queries using `<->` are even faster: they use the index to prune candidates and only compute exact distances for the few closest points.

## Can I mix geography with geometry in the same query?

Not directly; you have to cast one to the other. But it's usually not a good idea. If you're working with real-world locations, use geography consistently. If you're working with local coordinates (e.g., trading floor coordinates), use geometry.

## The <-> operator looks weird. What's it doing?

`<->` is a PostGIS operator that returns the distance between two geography points. It's optimized to work with GiST indexes (it can push the comparison into the index for early termination). It's the fastest way to do nearest-neighbor queries in Postgres.
