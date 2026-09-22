#!/usr/bin/env python3
"""Load the factory schema + seed data onto YOUR branch.

Runs factory_schema.sql then factory_seed.sql against the branch resolved from
your environment (LB_PROJECT / LB_BRANCH). Idempotent: the DDL is CREATE ... IF
NOT EXISTS and the seed uses ON CONFLICT DO NOTHING, so re-running is safe.

Usage:
    python load_factory.py           # load schema + seed
    python load_factory.py --check   # just report row counts (no load)
"""
from __future__ import annotations

import argparse
import os
import pathlib

from lakebase import connect

HERE = pathlib.Path(__file__).parent
SCHEMA_SQL = HERE / "factory_schema.sql"
SEED_SQL = HERE / "factory_seed.sql"

TABLES = ["plant", "machine", "sensor_reading", "product", "part", "bom_edge",
          "work_order", "operation", "supplier", "warehouse", "inventory",
          "part_supplier", "maintenance_log", "agent_memory"]


def _counts(conn) -> None:
    schema = os.getenv("LB_SCHEMA", "factory")
    with conn.cursor() as cur:
        for t in TABLES:
            try:
                cur.execute(f"SELECT count(*) FROM {schema}.{t}")
                print(f"  {t:16} {cur.fetchone()[0]:>6} rows")
            except Exception as e:  # table may not exist yet
                print(f"  {t:16} (missing: {str(e)[:40]})")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="report row counts only")
    args = ap.parse_args()

    with connect() as conn:
        if args.check:
            print("Factory tables on your branch:")
            _counts(conn)
            return
        with conn.cursor() as cur:
            print("Loading schema ...")
            cur.execute(SCHEMA_SQL.read_text())
            print("Seeding data ...")
            cur.execute(SEED_SQL.read_text())
        print("Done. Row counts:")
        _counts(conn)


if __name__ == "__main__":
    main()
