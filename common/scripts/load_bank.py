#!/usr/bin/env python3
"""Load the bank schema + seed data onto YOUR branch (finance edition).

Runs finance_schema.sql then finance_seed.sql against the branch resolved from
your environment (LB_PROJECT / LB_BRANCH). DDL is CREATE ... IF NOT EXISTS and
the seed uses ON CONFLICT DO NOTHING, but txn and case_note have BIGSERIAL ids, so
re-loading adds duplicate rows to those two. Check is_loaded() first.

Usage:
    python load_bank.py           # load schema + seed
    python load_bank.py --check   # just report row counts (no load)

From a notebook, pass an empty argv so argparse ignores the kernel's arguments:
    load_bank.main([])
"""
from __future__ import annotations

import argparse
import os
import pathlib

from lakebase import connect, _t

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
                print(f"  {t:20} {cur.fetchone()[0]:>6} {_t('rows', 'filas')}")
            except Exception as e:
                print(f"  {t:20} ({_t('missing', 'no existe')}: {str(e)[:40]})")


def is_loaded(conn) -> bool:
    """True if the bank schema already has accounts on this branch."""
    schema = os.getenv("LB_SCHEMA", "bank")
    with conn.cursor() as cur:
        cur.execute("SELECT to_regclass(%s)", [f"{schema}.account"])
        if cur.fetchone()[0] is None:
            return False
        cur.execute(f"SELECT count(*) FROM {schema}.account")
        return cur.fetchone()[0] > 0


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="report row counts only")
    args = ap.parse_args(argv)

    with connect() as conn:
        if args.check:
            branch = os.getenv("LB_BRANCH", "")
            print(_t(f"Bank tables on branch {branch}:", f"Tablas del banco en la rama {branch}:"))
            _counts(conn)
            return
        with conn.cursor() as cur:
            print(_t("Loading schema ...", "Cargando el esquema ..."))
            cur.execute(SCHEMA_SQL.read_text())
            print(_t("Seeding data ...", "Cargando los datos de ejemplo ..."))
            cur.execute(SEED_SQL.read_text())
        print(_t("Done. Row counts:", "Listo. Filas por tabla:"))
        _counts(conn)


if __name__ == "__main__":
    main()
