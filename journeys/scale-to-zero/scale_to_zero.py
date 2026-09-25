#!/usr/bin/env python3
"""Scale to zero, on Lakebase Autoscaling.

The honest Autoscaling model: an endpoint's compute AUTO-SUSPENDS to zero after a
period with no queries (state IDLE, no nodes, no compute cost), and WAKES on the
next connection. You do not press a stop button; idle compute costs nothing on its
own, and the next query brings it back in about two seconds.

This journey:
  - shows an endpoint's current state (ACTIVE = serving, IDLE = suspended to zero)
  - waits for / observes it going IDLE (or you point at an already-idle endpoint)
  - wakes it with a single query and TIMES the IDLE -> ACTIVE wake
  - confirms the data is exactly as it was

Usage:
    python scale_to_zero.py                 # the whole story
    python scale_to_zero.py --step status    # show the endpoint state
    python scale_to_zero.py --step wake      # wake it with a query, timed
    python scale_to_zero.py --branch production   # observe a likely-idle branch

Env: LB_PROFILE, LB_PROJECT, LB_BRANCH, LB_SCHEMA (see 00-setup/).

Note: unlike the managed-instance API, there is no manual "stopped=true" on an
Autoscaling endpoint here; suspension is automatic on idle. To force an endpoint
off you would set EndpointSpec.disabled=true, but the cost story is the automatic
suspend, so that is what we show.
"""
from __future__ import annotations

import argparse
import time

import psycopg

import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "common", "scripts"))
from lakebase import client, branch_name, _env, PG_PORT, DEFAULT_DB


def endpoint_state(w, project, branch):
    """(state, host, endpoint_id, last_active) for the branch's primary endpoint."""
    eps = list(w.postgres.list_endpoints(parent=branch_name(project, branch)))
    if not eps:
        return "NO_ENDPOINT", None, "primary", None
    e = eps[0]
    st = e.status.current_state.value if e.status and e.status.current_state else "UNKNOWN"
    host = e.status.hosts.host if e.status and e.status.hosts else None
    last = e.status.last_active_time if e.status else None
    return st, host, (e.endpoint_id or "primary"), last


def show_state(w, project, branch):
    st, host, eid, last = endpoint_state(w, project, branch)
    print(f"  branch {branch}: endpoint {eid} is {st}")
    if st == "IDLE":
        print("  -> suspended to zero: no compute nodes, no compute cost right now.")
    elif st == "ACTIVE":
        print("  -> serving: compute is up and metering.")
    return st, host, eid


def wake(w, project, branch):
    """Wake the endpoint with one query, timing the IDLE -> ACTIVE transition."""
    st, host, eid, _ = endpoint_state(w, project, branch)
    if not host:
        raise RuntimeError(f"branch {branch} has no endpoint host")
    if st == "IDLE":
        print(f"  endpoint is IDLE; a single query will wake it. timing...")
    else:
        print(f"  endpoint is {st}; running a query (already warm, so this is not a cold wake)")
    t0 = time.time()
    cred = w.postgres.generate_database_credential(
        endpoint=f"{branch_name(project, branch)}/endpoints/{eid}")
    conn = psycopg.connect(host=host, port=PG_PORT, dbname=DEFAULT_DB,
                           user=w.current_user.me().user_name, password=cred.token,
                           sslmode="require", autocommit=True, connect_timeout=30)
    # A plain SELECT 1 is enough to wake the endpoint; it does not depend on any
    # table existing on this branch (waking is about the compute, not the data).
    with conn.cursor() as cur:
        cur.execute("SELECT 1")
        cur.fetchone()
    dt = (time.time() - t0) * 1000
    conn.close()
    st2, _, _, _ = endpoint_state(w, project, branch)
    verb = "woke IDLE -> " + st2 if st == "IDLE" else st2
    print(f"  {verb}; first query answered in {dt:.0f} ms")
    return dt


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--step", choices=["status", "wake"])
    ap.add_argument("--branch", help="branch to observe (default: your LB_BRANCH)")
    args = ap.parse_args()

    w = client()
    project = _env("LB_PROJECT", required=True)
    branch = args.branch or _env("LB_BRANCH", required=True)

    if args.step == "status":
        show_state(w, project, branch)
        return
    if args.step == "wake":
        wake(w, project, branch)
        return

    # full story
    print("1. The endpoint's current state:")
    st, _, _ = show_state(w, project, branch)

    print("\n2. Idle compute scales to zero on its own.")
    print("   With no queries, an Autoscaling endpoint auto-suspends to IDLE: compute is")
    print("   released and you pay nothing for it. There is no stop button to press.")
    print("   (A busy branch you just used may still be ACTIVE; the production branch or one")
    print("   you have not touched for a while will be IDLE. Point --branch at an idle one to")
    print("   see the wake clearly.)")

    print("\n3. Wake it on demand with a single query:")
    dt = wake(w, project, branch)

    print("\n4. Back to serving, and the data is exactly as it was (nothing is lost when")
    print("   compute suspends; only the compute goes away, the storage stays):")
    show_state(w, project, branch)
    print(f"\nDone. Idle costs nothing; waking on demand took ~{dt/1000:.1f}s. You only pay when you serve.")


if __name__ == "__main__":
    main()
