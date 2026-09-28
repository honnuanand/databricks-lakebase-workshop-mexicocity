#!/usr/bin/env python3
"""Geospatial—PostGIS for supply chain locations.

ST_DWithin for "within N km", <-> for nearest-neighbor, GiST indexes.
Enable PostGIS, store plants/warehouses/suppliers as geographic points,
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
    """Add geography columns to plant, warehouse, supplier if missing."""
    tables = [
        ("factory.plant", "geo"),
        ("factory.warehouse", "geo"),
        ("factory.supplier", "geo")
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
    """Query: warehouses within 100 km of a plant."""
    print("\n=== Step 2: ST_DWithin (Within N km) ===")

    # Get a sample plant
    plants = run_sql("SELECT plant_id, lat, lon FROM factory.plant LIMIT 1")
    if not plants:
        print("  No plants found")
        return

    plant_id, plant_lat, plant_lon = plants[0]

    sql = f"""
    SELECT warehouse_id, plant_id,
           ROUND((ST_Distance(geo, ST_SetSRID(ST_MakePoint({plant_lon}, {plant_lat}), 4326)::geography) / 1000.0)::NUMERIC, 2) as distance_km
      FROM factory.warehouse
     WHERE ST_DWithin(geo, ST_SetSRID(ST_MakePoint({plant_lon}, {plant_lat}), 4326)::geography, 100000)
     ORDER BY distance_km
     LIMIT 10
    """
    rows = run_sql(sql)
    print(f"Warehouses within 100 km of {plant_id}:")
    for row in rows:
        print(f"  {row[0]} (distance: {row[2]} km)")

def run_nearest():
    """Query: nearest N suppliers to a plant."""
    print("\n=== Step 3: Nearest-Neighbor (<->) ===")

    # Get a sample plant
    plants = run_sql("SELECT plant_id, lat, lon FROM factory.plant LIMIT 1")
    if not plants:
        print("  No plants found")
        return

    plant_id, plant_lat, plant_lon = plants[0]

    sql = f"""
    SELECT supplier_id, name,
           ROUND((geo <-> ST_SetSRID(ST_MakePoint({plant_lon}, {plant_lat}), 4326)::geography)::NUMERIC, 0) as distance_meters
      FROM factory.supplier
     ORDER BY geo <-> ST_SetSRID(ST_MakePoint({plant_lon}, {plant_lat}), 4326)::geography
     LIMIT 3
    """
    rows = run_sql(sql)
    print(f"3 nearest suppliers to {plant_id}:")
    for row in rows:
        print(f"  {row[0]}: {row[1]} ({row[2]} meters)")

def run_index():
    """Create GiST indexes on geography columns."""
    print("\n=== Step 4: GiST Index ===")
    sqls = [
        "CREATE INDEX IF NOT EXISTS idx_plant_geo ON factory.plant USING gist(geo);",
        "CREATE INDEX IF NOT EXISTS idx_warehouse_geo ON factory.warehouse USING gist(geo);",
        "CREATE INDEX IF NOT EXISTS idx_supplier_geo ON factory.supplier USING gist(geo);"
    ]
    with connect() as conn:
        with conn.cursor() as cur:
            for sql in sqls:
                cur.execute(sql)
    print("  GiST indexes created on plant, warehouse, supplier")

def run_explain():
    """EXPLAIN a spatial query to show index usage."""
    print("\n=== Step 5: EXPLAIN (Index Usage) ===")

    plants = run_sql("SELECT plant_id, lat, lon FROM factory.plant LIMIT 1")
    if not plants:
        print("  No plants found")
        return

    plant_lat, plant_lon = plants[0][1], plants[0][2]

    sql = f"""
    EXPLAIN (ANALYZE, BUFFERS)
    SELECT supplier_id FROM factory.supplier
     ORDER BY geo <-> ST_SetSRID(ST_MakePoint({plant_lon}, {plant_lat}), 4326)::geography
     LIMIT 3
    """
    rows = run_sql(sql)
    print("  Query plan (look for 'Index Scan' or 'gist'):")
    for row in rows:
        print(f"    {row[0]}")

def run_end_to_end():
    """Run all steps end to end."""
    print("\n" + "="*60)
    print("GEOSPATIAL—POSTGIS SUPPLY CHAIN LOCATIONS")
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
    ap = argparse.ArgumentParser(description="PostGIS: spatial queries for supply chain")
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
