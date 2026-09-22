#!/usr/bin/env python3
"""Pg integration — show that Lakebase is standard Postgres.

Demonstrates that standard Postgres clients, ORMs, and BI tools
work unmodified by:
  - querying information_schema to discover tables
  - querying information_schema to discover columns and types
  - building a schema map (what BI tools do internally)
  - sampling rows to verify data correctness
  - confirming schema is visible in Unity Catalog

Usage:
    python pg_integration.py             # run the whole story
    python pg_integration.py --step tables      # list tables
    python pg_integration.py --step columns     # list columns and types
    python pg_integration.py --step schema-map  # build readable schema
    python pg_integration.py --step sample-data # sample rows from key tables

Env: LB_PROFILE, LB_PROJECT, LB_BRANCH, LB_SCHEMA (see 00-setup/).
"""
from __future__ import annotations

import argparse
from collections import defaultdict

import os, sys
# The shared Lakebase helper lives in common/scripts/. Make it importable
# from this journey folder no matter where you run the script from.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "common", "scripts"))
from lakebase import run_sql, _env


def list_tables(schema: str = "factory"):
    """List all tables in the given schema using information_schema."""
    query = f"SELECT table_name FROM information_schema.tables WHERE table_schema='{schema}' ORDER BY table_name"
    rows = run_sql(query)
    tables = [row[0] for row in rows]
    print(f"  {len(tables)} tables discovered:")
    for table in tables:
        print(f"    - {table}")
    return tables


def list_columns(schema: str = "factory"):
    """List all columns and types in the given schema."""
    query = (
        f"SELECT table_name, column_name, data_type "
        f"FROM information_schema.columns "
        f"WHERE table_schema='{schema}' "
        f"ORDER BY table_name, ordinal_position"
    )
    rows = run_sql(query)
    print(f"  {len(rows)} columns across all tables:")
    # Group by table for readability
    by_table = defaultdict(list)
    for table, column, dtype in rows:
        by_table[table].append((column, dtype))
    for table in sorted(by_table.keys()):
        print(f"    {table}:")
        for col, dtype in by_table[table]:
            print(f"      {col}: {dtype}")
    return rows


def build_schema_map(schema: str = "factory"):
    """Build a schema map (table -> columns -> types), like a BI tool does."""
    query = (
        f"SELECT table_name, column_name, data_type, is_nullable "
        f"FROM information_schema.columns "
        f"WHERE table_schema='{schema}' "
        f"ORDER BY table_name, ordinal_position"
    )
    rows = run_sql(query)

    schema_map = defaultdict(list)
    for table, column, dtype, nullable in rows:
        schema_map[table].append({
            "column": column,
            "type": dtype,
            "nullable": nullable == "YES"
        })

    print(f"\n=== Factory Schema Map (discovered via information_schema) ===\n")
    total_cols = 0
    for table in sorted(schema_map.keys()):
        print(f"TABLE: {table}")
        for col_info in schema_map[table]:
            col = col_info["column"]
            dtype = col_info["type"]
            null_marker = "" if col_info["nullable"] else " NOT NULL"
            print(f"  {col}: {dtype}{null_marker}")
            total_cols += 1
        print()

    print(f"=== Statistics ===")
    print(f"Total tables: {len(schema_map)}")
    print(f"Total columns: {total_cols}")


def sample_data(schema: str = "factory"):
    """Sample rows from key tables to verify data correctness."""
    key_tables = ["machine", "work_order", "sensor_reading"]

    for table in key_tables:
        try:
            query = f"SELECT * FROM {schema}.{table} LIMIT 3 ORDER BY 1"
            rows = run_sql(query)
            print(f"\nSample from {table}:")
            print(f"  ({len(rows)} rows shown)")
            for row in rows:
                print(f"  {row}")
        except Exception as e:
            print(f"\nSample from {table}: ERROR ({e})")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--step", choices=["tables", "columns", "schema-map", "sample-data"])
    args = ap.parse_args()

    schema = _env("LB_SCHEMA", "factory")

    if args.step == "tables":
        list_tables(schema)
        return
    if args.step == "columns":
        list_columns(schema)
        return
    if args.step == "schema-map":
        build_schema_map(schema)
        return
    if args.step == "sample-data":
        sample_data(schema)
        return

    # full story
    print("1. List tables in factory schema (via information_schema):")
    tables = list_tables(schema)

    print("\n2. List columns and types (via information_schema):")
    list_columns(schema)

    print("\n3. Build schema map (what a BI tool infers):")
    build_schema_map(schema)

    print("\n4. Sample rows from key tables (verify data is real):")
    sample_data(schema)

    print("\n5. Confirm schema in Unity Catalog (governance):")
    print("  (Open your Databricks workspace Data Catalog and navigate to")
    print(f"   the Lakebase instance's {schema} schema — same tables and columns")
    print("   visible, governed by Unity Catalog.)")

    print("\nDone. Lakebase is Postgres; your tools work unmodified.")


if __name__ == "__main__":
    main()
