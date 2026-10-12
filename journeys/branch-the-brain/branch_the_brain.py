#!/usr/bin/env python3
"""Branch the brain, fork your branch, diverge on the fork, discard it.

Demonstrates zero-copy Lakebase branching with real timings:
  - fork YOUR branch into an experiment branch (w.postgres.create_branch)
  - change ACCT-100240 on the fork only (set it to frozen)
  - show your branch is untouched
  - discard the fork (zero storage left behind)

Usage:
    python branch_the_brain.py                 # run the whole story with timings
    python branch_the_brain.py --step fork      # just fork + time to ACTIVE
    python branch_the_brain.py --step diverge   # change ACCT-100240 on the fork
    python branch_the_brain.py --step discard   # delete the fork
    python branch_the_brain.py --step list      # list branches

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

ACCOUNT = "ACCT-100240"


def _exp_branch() -> str:
    return _env("LB_BRANCH", required=True) + "-exp"


def _connect_branch(w, project, branch):
    host, eid, state = branch_endpoint(w, project, branch)
    if not host:
        raise RuntimeError(f"branch {branch} has no host (state={state})")
    cred = w.postgres.generate_database_credential(
        endpoint=f"{branch_name(project, branch)}/endpoints/{eid}")
    schema = os.getenv("LB_SCHEMA", "bank")
    conn = psycopg.connect(host=host, port=PG_PORT, dbname=DEFAULT_DB,
                           user=w.current_user.me().user_name, password=cred.token,
                           sslmode="require", autocommit=True, connect_timeout=20)
    with conn.cursor() as cur:
        cur.execute(f"SET search_path TO {schema}, public")
    return conn


def _show(conn, label):
    with conn.cursor() as cur:
        cur.execute(f"SELECT account_id, status, health_pct FROM account WHERE account_id=%s", [ACCOUNT])
        row = cur.fetchone()
    print(f"  [{label}] {ACCOUNT}: status={row[1]} health={row[2]}")


def fork(w, project, mine, exp):
    try:
        w.postgres.get_branch(name=branch_name(project, exp))
        print(f"experiment branch {exp} already exists; deleting first for a clean run")
        discard(w, project, exp)
        time.sleep(2)
    except Exception:
        pass
    t0 = time.time()
    w.postgres.create_branch(
        parent=f"projects/{project}",
        branch=Branch(spec=BranchSpec(source_branch=branch_name(project, mine), no_expiry=True)),
        branch_id=exp, replace_existing=False)
    api_ms = (time.time() - t0) * 1000
    waited = wait_active(w, project, exp)
    print(f"  fork API returned in {api_ms:.0f} ms; endpoint ACTIVE in ~{waited:.1f}s")


def diverge(w, project, exp):
    with _connect_branch(w, project, exp) as conn:
        with conn.cursor() as cur:
            cur.execute(f"UPDATE account SET status='frozen', health_pct=70.0 WHERE account_id=%s", [ACCOUNT])
        _show(conn, "fork after change")


def discard(w, project, exp):
    try:
        w.postgres.update_branch(name=branch_name(project, exp),
                                 branch=Branch(spec=BranchSpec(is_protected=False)),
                                 update_mask="spec.is_protected")
    except Exception:
        pass
    w.postgres.delete_branch(name=branch_name(project, exp))
    print(f"  discarded {exp}")


def list_branches(w, project):
    print("  branches:")
    for b in w.postgres.list_branches(parent=f"projects/{project}"):
        print(f"    - {b.branch_id}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--step", choices=["fork", "diverge", "discard", "list"])
    args = ap.parse_args()

    w = client()
    project = _env("LB_PROJECT", required=True)
    mine = _env("LB_BRANCH", required=True)
    exp = _exp_branch()

    if args.step == "fork":
        fork(w, project, mine, exp); return
    if args.step == "diverge":
        diverge(w, project, exp); return
    if args.step == "discard":
        discard(w, project, exp); return
    if args.step == "list":
        list_branches(w, project); return

    # full story
    print("1. Production (your branch) before:")
    with _connect_branch(w, project, mine) as conn:
        _show(conn, "your branch")
    print(f"2. Forking {mine} -> {exp} (zero-copy):")
    fork(w, project, mine, exp)
    print("3. Diverge on the fork:")
    diverge(w, project, exp)
    print("4. Your branch is untouched:")
    with _connect_branch(w, project, mine) as conn:
        _show(conn, "your branch")
    print("5. Discard the fork:")
    discard(w, project, exp)
    print("Done. Production untouched, fork gone, zero storage left behind.")


if __name__ == "__main__":
    main()
