#!/usr/bin/env python3
"""Break it, then rewind — delete work orders, then recover via point-in-time restore.

Demonstrates PITR (point-in-time restore) by:
  - capturing the LSN before a destructive DELETE
  - deleting all work orders on YOUR branch
  - creating a zero-copy PITR branch at the captured LSN
  - reading the deleted work orders back from the PITR branch
  - discarding the PITR branch (zero storage left behind)

Usage:
    python break_and_rewind.py                  # run the whole story with timings
    python break_and_rewind.py --step capture-lsn  # capture the LSN before delete
    python break_and_rewind.py --step delete       # delete all work orders
    python break_and_rewind.py --step recover      # create PITR branch and recover
    python break_and_rewind.py --step discard      # delete the PITR branch

Env: LB_PROFILE, LB_PROJECT, LB_BRANCH, LB_SCHEMA (see 00-setup/).
"""
from __future__ import annotations

import argparse
import os
import time

import psycopg
from databricks.sdk.service.postgres import Branch, BranchSpec

import os, sys
# The shared Lakebase helper lives in common/scripts/. Make it importable
# from this journey folder no matter where you run the script from.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "common", "scripts"))
from lakebase import (client, branch_name, branch_endpoint, wait_active,
                      _env, PG_PORT, DEFAULT_DB)


def _recover_branch() -> str:
    return _env("LB_BRANCH", required=True) + "-restore"


def _connect_branch(w, project, branch):
    host, eid, state = branch_endpoint(w, project, branch)
    if not host:
        raise RuntimeError(f"branch {branch} has no host (state={state})")
    cred = w.postgres.generate_database_credential(
        endpoint=f"{branch_name(project, branch)}/endpoints/{eid}")
    schema = os.getenv("LB_SCHEMA", "factory")
    conn = psycopg.connect(host=host, port=PG_PORT, dbname=DEFAULT_DB,
                           user=w.current_user.me().user_name, password=cred.token,
                           sslmode="require", autocommit=True, connect_timeout=20)
    with conn.cursor() as cur:
        cur.execute(f"SET search_path TO {schema}, public")
    return conn


def _show_work_orders(conn, label):
    with conn.cursor() as cur:
        cur.execute("SELECT count(*) FROM operation")
        n_ops = cur.fetchone()[0]
        cur.execute("SELECT wo_id, product_id, qty, status FROM work_order ORDER BY wo_id")
        rows = cur.fetchall()
    if not rows:
        print(f"  [{label}] (no work orders, {n_ops} operations)")
    else:
        for row in rows:
            print(f"  [{label}] {row}")
        print(f"  [{label}] ({len(rows)} work orders, {n_ops} operations)")


def capture_lsn(w, project, mine):
    """Capture the current LSN before the delete. Return the LSN."""
    with _connect_branch(w, project, mine) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT pg_current_wal_lsn()")
            lsn = cur.fetchone()[0]
    print(f"  LSN captured: {lsn}")
    return lsn


def delete_work_orders(w, project, mine):
    """The 'fat-fingered cleanup': wipe the work orders and their operations.

    operation rows reference work_order (a foreign key), so a real cleanup has to
    remove the child rows too. Deleting both is exactly the kind of over-broad
    DELETE this journey is about recovering from."""
    with _connect_branch(w, project, mine) as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM operation")     # children first (FK to work_order)
            cur.execute("DELETE FROM work_order")
        with conn.cursor() as cur:
            cur.execute("SELECT count(*) FROM work_order")
            wo = cur.fetchone()[0]
            cur.execute("SELECT count(*) FROM operation")
            ops = cur.fetchone()[0]
    if wo == 0 and ops == 0:
        print(f"  deleted: {wo} work orders and {ops} operations remain (all gone)")
    else:
        print(f"  ERROR: {wo} work orders / {ops} operations still remain")


def recover_via_pitr(w, project, mine, restore, lsn):
    """Create a PITR branch at the given LSN and read the work orders back."""
    try:
        w.postgres.get_branch(name=branch_name(project, restore))
        print(f"  restore branch {restore} already exists; deleting first for a clean run")
        discard(w, project, restore)
        time.sleep(2)
    except Exception:
        pass

    t0 = time.time()
    w.postgres.create_branch(
        parent=f"projects/{project}",
        branch=Branch(spec=BranchSpec(source_branch=branch_name(project, mine), source_branch_lsn=lsn, no_expiry=True)),
        branch_id=restore, replace_existing=False)
    api_ms = (time.time() - t0) * 1000
    waited = wait_active(w, project, restore)
    print(f"  PITR branch created: {restore}")
    print(f"  recovery API returned in {api_ms:.0f} ms; endpoint ACTIVE in ~{waited:.1f}s")

    # Read the work orders from the PITR branch
    print(f"  Recovered work orders from PITR branch:")
    with _connect_branch(w, project, restore) as conn:
        _show_work_orders(conn, "PITR branch")


def discard(w, project, restore):
    try:
        w.postgres.update_branch(name=branch_name(project, restore),
                                 branch=Branch(spec=BranchSpec(is_protected=False)),
                                 update_mask="spec.is_protected")
    except Exception:
        pass
    w.postgres.delete_branch(name=branch_name(project, restore))
    print(f"  discarded {restore}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--step", choices=["capture-lsn", "delete", "recover", "discard"])
    args = ap.parse_args()

    w = client()
    project = _env("LB_PROJECT", required=True)
    mine = _env("LB_BRANCH", required=True)
    restore = _recover_branch()

    # For step-by-step execution, we may need to capture LSN from a file (not ideal in a demo)
    # For now, each step that needs the LSN will capture it fresh
    lsn = None

    if args.step == "capture-lsn":
        lsn = capture_lsn(w, project, mine)
        return
    if args.step == "delete":
        delete_work_orders(w, project, mine)
        return
    if args.step == "recover":
        # For the recover step alone, we need to have captured the LSN earlier
        # In practice, users will run the full story; for per-step, they'd need to manually capture first
        print("  (for this step, capture-lsn should have been run first)")
        print("  Using the current LSN as a proxy (this won't recover old data if run standalone)")
        lsn = capture_lsn(w, project, mine)
        recover_via_pitr(w, project, mine, restore, lsn)
        return
    if args.step == "discard":
        discard(w, project, restore)
        return

    # full story
    print("1. Establish the data:")
    with _connect_branch(w, project, mine) as conn:
        _show_work_orders(conn, "your branch")

    print("2. Capture LSN (before the mistake):")
    lsn = capture_lsn(w, project, mine)

    print("3. Make the mistake (DELETE all work_orders):")
    delete_work_orders(w, project, mine)

    print("4. Recover via point-in-time restore:")
    recover_via_pitr(w, project, mine, restore, lsn)

    print("5. Discard the PITR branch:")
    discard(w, project, restore)

    print("Done. Work orders recovered, branch deleted, zero storage left behind.")


if __name__ == "__main__":
    main()
