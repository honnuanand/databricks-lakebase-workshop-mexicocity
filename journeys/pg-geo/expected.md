# Geospatial, expected results

Use this to check your run. The numbers here are from our measurements; yours will be close but not identical. The *shape* of the results and the general magnitudes are what matter.

## Step 1, PostGIS enabled

```text
CREATE EXTENSION IF NOT EXISTS postgis CASCADE;
```

Returns quietly. PostGIS is now available. Geography columns are added to branch, custodian, and counterparty tables (if not already present).

## Step 2, within N km

```text
custodian_id  distance_km
CUST-ALTA      5.67
CUST-NORTE     78.23
CUST-PONIENTE      102.45  (just outside 100 km, filtered)
```

Custodians within 100 km of the CDMX branch. Distances calculated using spherical geometry (WGS84). The exact distances depend on your seed data; the shape is a list of locations sorted by distance, with the nearest first.

## Step 3, nearest N

```text
counterparty_id  distance_meters
CP-ALTAMAR       8900
CP-CUMBRE      85000
CP-MIRADOR       350000
```

The 3 nearest counterparties to CDMX (lat/lon chosen as example; yours will vary based on seed data). The `<->` operator finds the nearest neighbors efficiently, returning them sorted by distance. Distances are in meters (PostGIS standard).

## Step 4, GiST index

```text
CREATE INDEX idx_branch_geo ON bank.branch USING gist(geo);
CREATE INDEX idx_custodian_geo ON bank.custodian USING gist(geo);
CREATE INDEX idx_counterparty_geo ON bank.counterparty USING gist(geo);
```

Indexes are created. Subsequent spatial queries will use them if the planner decides they're beneficial.

## Step 5, EXPLAIN shows index usage

```text
Limit  (cost=0.29..0.42 rows=3 width=60)
  ->  Index Scan using idx_counterparty_geo on counterparty  (...)
        Index Cond: (geo <-> <point>)
```

The plan shows "Index Scan using idx_counterparty_geo" and "Index Cond: (geo <-> <point>)". This confirms the GiST index is being used for the distance operator. On large datasets, this makes a huge difference.

## The numbers that matter

| What | Expected | Why it matters |
| ---- | -------- | -------------- |
| ST_DWithin query (20 locations) | < 5 ms | fast spatial filter |
| Nearest-neighbor query (50 counterparties) | < 2 ms | the <-> operator is optimized |
| GiST index creation | instant (for small datasets) | spatial indexes are cheap |
| Query after index | no visible change (small dataset) | but huge difference at scale (thousands of locations) |

> **From the field**
> If PostGIS is not available on your Lakebase instance (rare, but possible in some cloud regions), you can still do the queries by calculating distances manually using the Haversine formula in SQL. It's slower and more error-prone, but it works:
> ```sql
> SELECT custodian_id, 
>        6371 * 2 * ASIN(SQRT(POWER(SIN((lat2-lat1)/2*PI()/180),2) 
>             + COS(lat1*PI()/180)*COS(lat2*PI()/180)*POWER(SIN((lon2-lon1)/2*PI()/180),2))) as distance_km
>   FROM custodians;
> ```
> But PostGIS is the better way, it's optimized for this, handles edge cases (poles, datelines), and is a well-supported Postgres extension.
