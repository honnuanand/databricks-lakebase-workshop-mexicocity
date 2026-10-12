#!/usr/bin/env python3
"""JSON documents, JSONB specs for flexible instrument and fund documentation.

JSONB operators: @> (containment), #>> (path extraction), ? (key exists).
GIN index for fast queries. Screening queries on varying spec sheets.
"""
import argparse
import os, sys
# The shared Lakebase helper lives in common/scripts/. Make it importable
# from this journey folder no matter where you run the script from.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "common", "scripts"))
from lakebase import connect, run_sql

def run_contains():
    """Step 2: Use @> (containment) to find instruments matching a spec."""
    print("\n=== Step 2: Containment Operator (@>) ===")
    sql = """
    SELECT instrument_id, name, spec
      FROM bank.instrument
     WHERE spec @> '{"sector": "tech"}'
     LIMIT 5;
    """
    rows = run_sql(sql)
    print(f"Instruments with sector='tech' (using @> containment):")
    for row in rows:
        print(f"  {row[0]}: {row[1]}")
        print(f"    spec: {row[2]}")

def run_extract():
    """Step 3: Use #>> (path extraction) and ? (key exists)."""
    print("\n=== Step 3: Path Extraction (#>>) ===")
    sql = """
    SELECT instrument_id, name, spec #>> '{sector}' as sector
      FROM bank.instrument
     WHERE spec ? 'sector'
     LIMIT 5;
    """
    rows = run_sql(sql)
    print(f"Extracted sector field from JSONB spec:")
    for row in rows:
        print(f"  {row[0]}: sector={row[2]}")

def run_index():
    """Step 4: Create a GIN index on JSONB."""
    print("\n=== Step 4: GIN Index ===")
    sql = "CREATE INDEX IF NOT EXISTS idx_instrument_spec_gin ON bank.instrument USING gin(spec jsonb_path_ops);"
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute(sql)
    print("  GIN index created on bank.instrument(spec)")
    print("  (Queries will use the index if beneficial)")

def run_screening():
    """Step 5: Realistic screening query, equities in tech sector."""
    print("\n=== Step 5: Screening Query ===")
    sql = """
    SELECT instrument_id, name, spec
      FROM bank.instrument
     WHERE spec @> '{"sector": "tech"}'
       AND kind = 'equity'
     LIMIT 10;
    """
    rows = run_sql(sql)
    print(f"Equities in tech sector:")
    for row in rows:
        print(f"  {row[0]}: {row[1]}")
        if row[2]:
            print(f"    {row[2]}")

def run_end_to_end():
    """Run all steps end to end."""
    print("\n" + "="*60)
    print("JSON DOCUMENTS, JSONB SPECS & QUERIES")
    print("="*60)

    print("\n=== Step 1: Inspect JSONB Specs ===")
    sql = "SELECT instrument_id, name, spec FROM bank.instrument LIMIT 3"
    rows = run_sql(sql)
    print(f"Sample instrument specs (JSONB, varying fields):")
    for row in rows:
        print(f"  {row[0]}: {row[1]}")
        print(f"    spec: {row[2]}")

    run_contains()
    run_extract()
    run_index()
    run_screening()

    print("\n" + "="*60)
    print("Done. See instructions.md for detailed explanations.")
    print("="*60)

def main():
    ap = argparse.ArgumentParser(description="JSONB specs and queries")
    ap.add_argument("--step", choices=["contains", "extract", "index", "screening"],
                    help="Run a specific step (default: all)")
    args = ap.parse_args()

    if args.step == "contains":
        run_contains()
    elif args.step == "extract":
        run_extract()
    elif args.step == "index":
        run_index()
    elif args.step == "screening":
        run_screening()
    else:
        run_end_to_end()

if __name__ == "__main__":
    main()
