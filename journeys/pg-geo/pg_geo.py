#!/usr/bin/env python3
"""Geospatial, PostGIS for financial network locations.

ST_DWithin for "within N km", <-> for nearest-neighbor, GiST indexes.
Enable PostGIS, store branches/custodians/counterparties as geographic points,
query and index them.
"""
import argparse
import os, sys
# The shared Lakebase helper lives in common/scripts/. Make it importable
# from this journey folder no matter where you run the script from.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "common", "scripts"))
from lakebase import connect, run_sql

def enable_postgis():
    """Enable PostGIS extension."""
    with connect() as conn:
        with conn.cursor() as cur:
            try:
                cur.execute("CREATE EXTENSION IF NOT EXISTS postgis CASCADE")
                print("  PostGIS extension enabled")
            except Exception as e:
                print(f"  Warning: PostGIS may not be available: {e}")

def add_geography_columns():
    """Add geography columns to branch, custodian, counterparty if missing."""
    tables = [
        ("bank.branch", "geo"),
        ("bank.custodian", "geo"),
        ("bank.counterparty", "geo")
    ]
    with connect() as conn:
        with conn.cursor() as cur:
            for table, col in tables:
                try:
                    cur.execute(f"""
                        ALTER TABLE {table}
                        ADD COLUMN {col} GEOGRAPHY(POINT) DEFAULT NULL
                    """)
                    print(f"  Added {col} column to {table}")
                except:
                    pass  # Column may already exist

            # Populate geography columns from lat/lon
            for table, col in tables:
                try:
                    cur.execute(f"""
                        UPDATE {table}
                        SET {col} = ST_SetSRID(ST_MakePoint(lon, lat), 4326)::geography
                        WHERE {col} IS NULL AND lat IS NOT NULL AND lon IS NOT NULL
                    """)
                    print(f"  Populated {col} on {table}")
                except:
                    pass

def run_within():
    """Query: custodians within 100 km of a branch."""
    print("\n=== Step 2: ST_DWithin (Within N km) ===")

    # Get a sample branch
    branches = run_sql("SELECT branch_id, lat, lon FROM bank.branch LIMIT 1")
    if not branches:
        print("  No branches found")
        return

    branch_id, branch_lat, branch_lon = branches[0]

    sql = f"""
    SELECT custodian_id, branch_id,
           ROUND((ST_Distance(geo, ST_SetSRID(ST_MakePoint({branch_lon}, {branch_lat}), 4326)::geography) / 1000.0)::NUMERIC, 2) as distance_km
      FROM bank.custodian
     WHERE ST_DWithin(geo, ST_SetSRID(ST_MakePoint({branch_lon}, {branch_lat}), 4326)::geography, 100000)
     ORDER BY distance_km
     LIMIT 10
    """
    rows = run_sql(sql)
    print(f"Custodians within 100 km of {branch_id}:")
    for row in rows:
        print(f"  {row[0]} (distance: {row[2]} km)")

def run_nearest():
    """Query: nearest N counterparties to a branch."""
    print("\n=== Step 3: Nearest-Neighbor (<->) ===")

    # Get a sample branch
    branches = run_sql("SELECT branch_id, lat, lon FROM bank.branch LIMIT 1")
    if not branches:
        print("  No branches found")
        return

    branch_id, branch_lat, branch_lon = branches[0]

    sql = f"""
    SELECT counterparty_id, name,
           ROUND((geo <-> ST_SetSRID(ST_MakePoint({branch_lon}, {branch_lat}), 4326)::geography)::NUMERIC, 0) as distance_meters
      FROM bank.counterparty
     ORDER BY geo <-> ST_SetSRID(ST_MakePoint({branch_lon}, {branch_lat}), 4326)::geography
     LIMIT 3
    """
    rows = run_sql(sql)
    print(f"3 nearest counterparties to {branch_id}:")
    for row in rows:
        print(f"  {row[0]}: {row[1]} ({row[2]} meters)")

def run_index():
    """Create GiST indexes on geography columns."""
    print("\n=== Step 4: GiST Index ===")
    sqls = [
        "CREATE INDEX IF NOT EXISTS idx_branch_geo ON bank.branch USING gist(geo);",
        "CREATE INDEX IF NOT EXISTS idx_custodian_geo ON bank.custodian USING gist(geo);",
        "CREATE INDEX IF NOT EXISTS idx_counterparty_geo ON bank.counterparty USING gist(geo);"
    ]
    with connect() as conn:
        with conn.cursor() as cur:
            for sql in sqls:
                cur.execute(sql)
    print("  GiST indexes created on branch, custodian, counterparty")

def run_explain():
    """EXPLAIN a spatial query to show index usage."""
    print("\n=== Step 5: EXPLAIN (Index Usage) ===")

    branches = run_sql("SELECT branch_id, lat, lon FROM bank.branch LIMIT 1")
    if not branches:
        print("  No branches found")
        return

    branch_lat, branch_lon = branches[0][1], branches[0][2]

    sql = f"""
    EXPLAIN (ANALYZE, BUFFERS)
    SELECT counterparty_id FROM bank.counterparty
     ORDER BY geo <-> ST_SetSRID(ST_MakePoint({branch_lon}, {branch_lat}), 4326)::geography
     LIMIT 3
    """
    rows = run_sql(sql)
    print("  Query plan (look for 'Index Scan' or 'gist'):")
    for row in rows:
        print(f"    {row[0]}")

def run_end_to_end():
    """Run all steps end to end."""
    print("\n" + "="*60)
    print("GEOSPATIAL, POSTGIS FINANCIAL NETWORK LOCATIONS")
    print("="*60)

    print("\n=== Step 1: Enable PostGIS ===")
    enable_postgis()
    add_geography_columns()

    run_within()
    run_nearest()
    run_index()
    run_explain()

    print("\n" + "="*60)
    print("Done. See instructions.md for detailed explanations.")
    print("="*60)

def main():
    ap = argparse.ArgumentParser(description="PostGIS: spatial queries for financial networks")
    ap.add_argument("--step", choices=["within", "nearest", "index", "explain"],
                    help="Run a specific step (default: all)")
    args = ap.parse_args()

    if args.step == "within":
        enable_postgis()
        add_geography_columns()
        run_within()
    elif args.step == "nearest":
        enable_postgis()
        add_geography_columns()
        run_nearest()
    elif args.step == "index":
        run_index()
    elif args.step == "explain":
        enable_postgis()
        add_geography_columns()
        run_explain()
    else:
        run_end_to_end()

if __name__ == "__main__":
    main()
