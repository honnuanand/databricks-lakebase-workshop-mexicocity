#!/usr/bin/env python3
"""One copy, both directions: operational writes and analytics on the same data.

The Lakebase LTAP idea (live data flow, no pipeline): your operational rows are the
same rows analytics reads. There is no change-data-capture job copying data from an
OLTP store to an analytics store; there is one copy, reachable from both sides.

WHAT THIS SCRIPT RUNS LIVE (real, on your branch):
  - write a new sensor reading through Postgres (a millisecond OLTP write)
  - compute a failure-risk score from it
  - write that score back onto the row (a failure_risk column)
  - read it back, so the operational side now serves an analytics-derived value

WHAT IS AN EXPLAINER (clearly labeled, NOT run here):
  - reading the same rows from the lakehouse through a Unity Catalog foreign table
    on a SQL warehouse. That requires registering the Lakebase database as a UC
    catalog, which is a metastore-admin action (CREATE CATALOG on the metastore).
    We show the exact query you would run once that catalog exists; we do not fake
    its output.

Usage:
    python write_to_analytics.py                # the live half + the explainer
    python write_to_analytics.py --step write   # just the OLTP write
    python write_to_analytics.py --step score    # compute + write back the risk

Env: LB_PROFILE, LB_PROJECT, LB_BRANCH, LB_SCHEMA (see 00-setup/).
"""
from __future__ import annotations

import argparse

import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "common", "scripts"))
from lakebase import run_sql


def ensure_column():
    """Add a failure_risk column to sensor_reading if it is not there yet (idempotent)."""
    run_sql("ALTER TABLE bank.txn ADD COLUMN IF NOT EXISTS failure_risk NUMERIC(5,1)")


def write_reading():
    """Write a new sensor reading through Postgres (OLTP). Returns its txn_id."""
    r = run_sql(
        "INSERT INTO bank.txn (account_id, ts, temp_c, anomaly_score, rpm, util_pct) "
        "VALUES ('ACCT-100240', now(), 67.3, 4.2, 1165, 81.0) "
        "RETURNING txn_id, temp_c, anomaly_score")
    rid, temp, vib = r[0]
    print(f"  inserted txn_id={rid}: temp_c={temp}, anomaly_score={vib}")
    return rid


def score_and_write_back(rid):
    """Compute a failure-risk score and write it back onto the row."""
    run_sql(
        "UPDATE bank.txn "
        "SET failure_risk = ROUND(100 * (anomaly_score / 10.0 + temp_c / 100.0), 1) "
        f"WHERE txn_id = {rid}")
    row = run_sql(
        "SELECT txn_id, account_id, temp_c, anomaly_score, failure_risk "
        f"FROM bank.txn WHERE txn_id = {rid}")[0]
    print(f"  scored + wrote back: {row}")
    return row


def lakehouse_explainer():
    """Show, honestly labeled, the lakehouse side that needs a UC catalog registration."""
    print("  EXPLAINER (not run here): reading the SAME rows from the lakehouse.")
    print("  Once an admin registers this Lakebase database as a Unity Catalog online catalog,")
    print("  the operational rows are visible to a SQL warehouse with no pipeline and no copy:")
    print()
    print("    -- on a SQL warehouse, against the UC foreign catalog for this database:")
    print("    SELECT account_id, ts, temp_c, anomaly_score, failure_risk")
    print("    FROM <catalog>.bank.txn")
    print("    WHERE account_id = 'ACCT-100240' ORDER BY ts DESC LIMIT 1;")
    print()
    print("  The row you just wrote through Postgres appears there immediately: it is the same")
    print("  copy, not a synced one. Registering the catalog needs CREATE CATALOG on the")
    print("  metastore (a workspace/metastore-admin action), so this workshop shows the query")
    print("  rather than running it for you. Nothing here is simulated: the write and score above")
    print("  are real on your branch; this step is the one that needs admin setup.")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--step", choices=["write", "score"])
    args = ap.parse_args()

    ensure_column()

    if args.step == "write":
        write_reading()
        return
    if args.step == "score":
        rid = write_reading()
        score_and_write_back(rid)
        return

    # full story
    print("1. Write a new sensor reading through Postgres (OLTP), a millisecond write:")
    rid = write_reading()

    print("\n2. Compute a failure-risk score and write it back onto the row (reverse step):")
    score_and_write_back(rid)

    print("\n3. The operational side now serves an analytics-derived value at OLTP latency.")
    print("   Read it straight back from Postgres:")
    row = run_sql(
        "SELECT account_id, temp_c, anomaly_score, failure_risk "
        f"FROM bank.txn WHERE txn_id = {rid}")[0]
    print(f"  {row}")

    print("\n4. The lakehouse side (same copy, no pipeline):")
    lakehouse_explainer()

    print("\nDone. The write, the score, and the write-back are real on your branch. The lakehouse")
    print("read is one query away once the database is registered in Unity Catalog.")


if __name__ == "__main__":
    main()
