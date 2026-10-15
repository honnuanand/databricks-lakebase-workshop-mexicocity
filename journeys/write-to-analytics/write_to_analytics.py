#!/usr/bin/env python3
"""One copy, both directions: operational writes and analytics on the same data.

The Lakebase idea (live data flow, no pipeline): your operational rows are the same
rows analytics reads. There is no change-data-capture job copying from an OLTP store
to an analytics store; there is one copy, reachable from both sides.

Banking scenario: a SPEI transfer lands, you score its fraud risk, and write the
score back onto the row, so the operational side (the authorization path) serves an
analytics-derived value at OLTP latency.

WHAT RUNS LIVE (real, on your branch):
  - write a new transaction through Lakebase (a millisecond OLTP write)
  - compute a fraud-risk score from it
  - write that score back onto the row (a fraud_risk column)
  - read it back

WHAT IS AN EXPLAINER (clearly labeled, NOT run here):
  - reading the same rows from the lakehouse through a Unity Catalog foreign table
    on a SQL warehouse. That needs the Lakebase database registered as a UC catalog,
    a metastore-admin action. We show the query you would run; we do not fake output.

Usage:
    python write_to_analytics.py                # the live half + the explainer
    python write_to_analytics.py --step write   # just the OLTP write
    python write_to_analytics.py --step score    # compute + write back the fraud score

Env: LB_PROFILE, LB_PROJECT, LB_BRANCH, LB_SCHEMA (see 00-setup/).
"""
from __future__ import annotations

import argparse

import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "common", "scripts"))
from lakebase import run_sql


def ensure_column():
    """Add a fraud_risk column to txn if it is not there yet (idempotent)."""
    run_sql("ALTER TABLE bank.txn ADD COLUMN IF NOT EXISTS fraud_risk NUMERIC(5,1)")


def write_txn():
    """Write a new transaction through Lakebase (OLTP). Returns its txn_id."""
    r = run_sql(
        "INSERT INTO bank.txn (account_id, ts, amount, channel, anomaly_score, mcc, util_pct) "
        "VALUES ('CTA-100240', now(), 38500.00, 'SPEI', 8.7, NULL, 92.0) "
        "RETURNING txn_id, amount, anomaly_score")
    tid, amt, anom = r[0]
    print(f"  inserted txn_id={tid}: amount={amt}, anomaly_score={anom}")
    return tid


def score_and_write_back(tid):
    """Compute a fraud-risk score and write it back onto the row."""
    run_sql(
        "UPDATE bank.txn "
        "SET fraud_risk = ROUND(100 * (anomaly_score / 10.0 + util_pct / 100.0), 1) "
        f"WHERE txn_id = {tid}")
    row = run_sql(
        "SELECT txn_id, account_id, amount, anomaly_score, util_pct, fraud_risk "
        f"FROM bank.txn WHERE txn_id = {tid}")[0]
    print(f"  scored + wrote back: {row}")
    return row


def lakehouse_explainer():
    """Show, honestly labeled, the lakehouse side that needs a UC catalog registration."""
    print("  EXPLAINER (not run here): reading the SAME rows from the lakehouse.")
    print("  Once an admin registers this Lakebase database as a Unity Catalog online catalog,")
    print("  the operational rows are visible to a SQL warehouse with no pipeline and no copy:")
    print()
    print("    -- on a SQL warehouse, against the UC foreign catalog for this database:")
    print("    SELECT account_id, ts, amount, anomaly_score, fraud_risk")
    print("    FROM <catalog>.bank.txn")
    print("    WHERE account_id = 'CTA-100240' ORDER BY ts DESC LIMIT 1;")
    print()
    print("  The transaction you just wrote through Lakebase appears there immediately: same copy,")
    print("  not a synced one. Registering the catalog needs CREATE CATALOG on the metastore (a")
    print("  workspace/metastore-admin action), so this workshop shows the query rather than running")
    print("  it for you. Nothing here is simulated: the write and the fraud score above are real.")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--step", choices=["write", "score"])
    args = ap.parse_args()

    ensure_column()

    if args.step == "write":
        write_txn()
        return
    if args.step == "score":
        tid = write_txn()
        score_and_write_back(tid)
        return

    # full story
    print("1. Write a new transaction through Lakebase (OLTP), a millisecond write:")
    tid = write_txn()

    print("\n2. Compute a fraud-risk score and write it back onto the row (reverse step):")
    score_and_write_back(tid)

    print("\n3. The operational side now serves an analytics-derived value at OLTP latency.")
    print("   Read it straight back from Lakebase:")
    row = run_sql(
        "SELECT account_id, amount, anomaly_score, fraud_risk "
        f"FROM bank.txn WHERE txn_id = {tid}")[0]
    print(f"  {row}")

    print("\n4. The lakehouse side (same copy, no pipeline):")
    lakehouse_explainer()

    print("\nDone. The write, the score, and the write-back are real on your branch. The lakehouse")
    print("read is one query away once the database is registered in Unity Catalog.")


if __name__ == "__main__":
    main()
