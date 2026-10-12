# Geospatial, instructions

## How to run this journey

There are a few ways to work through the steps. Pick one:

- **Notebook, step by step (recommended for learning):** open [`pg_geo.ipynb`](pg_geo.ipynb) and run one cell at a time. Reading each result before the next step is where the learning happens.
- **In a Databricks workspace:** import [`pg_geo_databricks.py`](pg_geo_databricks.py) and run it cell by cell there.
- **By hand:** follow the numbered steps below, copying each command yourself.
- **Just see it work:** run `python pg_geo.py` from this folder to execute the whole thing at once. Fast, but you learn the most from the notebook.

Run these on your own branch. If you haven't done [`../../00-setup/`](../../00-setup/), do that first; you need `LB_PROFILE`, `LB_PROJECT`, `LB_BRANCH`, and `LB_SCHEMA` set, and the bank loaded.

Everything here is a single script you can read: [`./pg_geo.py`](./pg_geo.py). You can run it end to end, or follow the steps by hand to see each piece.

## Run it end to end

```bash
cd journeys/pg-geo
python pg_geo.py
```

This walks through the entire journey and prints results. Read on for what each step does; the exact output to expect is in [`expected.md`](expected.md).

## Or step through it by hand

### Step 1, enable PostGIS and create geography columns

[PostGIS](../../docs/glossary.md) is a Postgres extension. Enable it:

```bash
python ../../common/scripts/lakebase.py --sql "CREATE EXTENSION IF NOT EXISTS postgis CASCADE"
```

This installs the PostGIS types and functions. Then add geography columns to branches, custodians, and counterparties (if not already present):

```bash
python ../../common/scripts/lakebase.py --sql \
  "ALTER TABLE bank.branch ADD COLUMN geo GEOGRAPHY(POINT) DEFAULT NULL"
```

(This is idempotent; if the column exists, it does nothing.)

### Step 2, query "within N km" using ST_DWithin

Find all custodians within 100 km of a branch:

```bash
python pg_geo.py --step within
```

The script runs:

```sql
SELECT custodian_id, branch_id, lat, lon,
       ST_Distance(geography(POINT(lon, lat)), 
                   geography(POINT(branch_lon, branch_lat))) / 1000.0 as distance_km
  FROM bank.custodian c, bank.branch b
 WHERE b.branch_id = 'BR-NYC'
   AND ST_DWithin(geography(POINT(c.lon, c.lat)),
                  geography(POINT(b.lon, b.lat)),
                  100000)  -- 100 km in meters
 ORDER BY distance_km
 LIMIT 10;
```

The `geography(POINT(lon, lat))` constructor turns lat/lon numbers into geographic points. `ST_DWithin` returns rows within a distance (in meters). `ST_Distance` calculates the exact distance. Result: custodians near New York.

### Step 3, query "nearest N" using the <-> operator

Find the 3 nearest counterparties to a branch:

```bash
python pg_geo.py --step nearest
```

The script runs:

```sql
SELECT counterparty_id, name, lat, lon,
       geography(POINT(lon, lat)) <-> geography(POINT(-74.0060, 40.7128)) as distance_meters
  FROM bank.counterparty
 ORDER BY geography(POINT(lon, lat)) <-> geography(POINT(-74.0060, 40.7128))
 LIMIT 3;
```

The `<->` operator calculates distance between two geography points and sorts by it. This is the nearest-neighbor query, it finds the closest points without calculating distance to every candidate.

### Step 4, create a GiST index

Spatial queries are fast even without an index. With a [GiST](../../docs/glossary.md) index, they're faster:

```bash
python pg_geo.py --step index
```

The script creates:

```sql
CREATE INDEX IF NOT EXISTS idx_branch_geo ON bank.branch USING gist(geo);
CREATE INDEX IF NOT EXISTS idx_custodian_geo ON bank.custodian USING gist(geo);
CREATE INDEX IF NOT EXISTS idx_counterparty_geo ON bank.counterparty USING gist(geo);
```

These indexes accelerate spatial searches. Run a query before and after and compare; on the bank dataset (dozens of locations) the difference is subtle, but on a global financial network (thousands of locations) the difference is dramatic.

### Step 5, verify the index is used

Check the query plan with EXPLAIN to confirm the index is being used:

```bash
python pg_geo.py --step explain
```

The script runs EXPLAIN on a spatial query and prints the plan. Look for "Index Scan" or "GiST" in the output. If you see "Seq Scan" (sequential scan), the index is not being used, often because the dataset is too small to make indexing worthwhile, or the query planner decided a sequential scan is faster.

## What you just did

You enabled PostGIS, stored branch, custodian, and counterparty locations as geographic points, and wrote spatial queries: "within N km" and "nearest N". Then you indexed with GiST and verified the index is being used. All of that is native Postgres, no separate GIS system to run or sync.
