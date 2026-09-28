#!/usr/bin/env python3
"""Load the bank schema + seed data onto YOUR branch (finance edition).

Runs finance_schema.sql then finance_seed.sql against the branch resolved from
your environment (LB_PROJECT / LB_BRANCH). Idempotent: DDL is CREATE ... IF NOT
EXISTS and the seed uses ON CONFLICT DO NOTHING, so re-running is safe.

Usage:
    python load_bank.py           # load schema + seed
    python load_bank.py --check   # just report row counts (no load)
"""
from __future__ import annotations

import argparse
import os
import pathlib

from lakebase import connect

HERE = pathlib.Path(__file__).parent
SCHEMA_SQL = HERE / "finance_schema.sql"
SEED_SQL = HERE / "finance_seed.sql"

TABLES = ["branch", "account", "txn", "fund", "instrument", "holding",
          "trade", "settlement", "counterparty", "custodian", "position",
          "trade_counterparty", "case_note", "agent_memory"]


def _counts(conn) -> None:
    schema = os.getenv("LB_SCHEMA", "bank")
    with conn.cursor() as cur:
        for t in TABLES:
            try:
                cur.execute(f"SELECT count(*) FROM {schema}.{t}")
                print(f"  {t:20} {cur.fetchone()[0]:>6} rows")
            except Exception as e:
                print(f"  {t:20} (missing: {str(e)[:40]})")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="report row counts only")
    args = ap.parse_args()

    with connect() as conn:
        if args.check:
            print("Bank tables on your branch:")
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
