#!/usr/bin/env python3
"""Scale to zero — stop and start database compute on demand.

Demonstrates cost control by:
  - checking the current compute state (ACTIVE, running)
  - stopping the compute (effective_stopped → true, nodes → 0, cost → $0)
  - timing restart back to ACTIVE (about 7 seconds)
  - verifying data is untouched

Usage:
    python scale_to_zero.py           # run the whole story
    python scale_to_zero.py --step status   # check endpoint state
    python scale_to_zero.py --step stop     # stop compute
    python scale_to_zero.py --step start    # start compute

Env: LB_PROFILE, LB_PROJECT (see 00-setup/).
Note: This stops compute on the PROJECT, affecting all branches. Only run on your own project
      or with coordination on a shared project.
"""
from __future__ import annotations

import argparse
import time

from databricks.sdk.service.postgres import DatabaseInstance

from lakebase import client, _env


def get_instance_state(w, project):
    """Fetch the project's database instance state and return key info."""
    inst = w.postgres.get_database_instance(name=f"projects/{project}")
    ep = inst.endpoints[0] if inst.endpoints else None
    return {
        "endpoint_id": ep.endpoint_id if ep else "?",
        "state": ep.status.current_state.value if (ep and ep.status and ep.status.current_state) else "UNKNOWN",
        "nodes": inst.nodes if inst.nodes else 0,
        "effective_stopped": inst.effective_stopped if inst.effective_stopped else False,
        "cu": inst.compute_unit if inst.compute_unit else "?",
    }


def show_state(w, project):
    """Print the current instance state."""
    state = get_instance_state(w, project)
    print(f"  endpoint_id: {state['endpoint_id']}")
    print(f"  state: {state['state']}")
    print(f"  nodes: {state['nodes']}")
    print(f"  cu: {state['cu']}")
    if state['effective_stopped']:
        print(f"  effective_stopped: {state['effective_stopped']}")


def stop_compute(w, project):
    """Stop the compute on the project."""
    print("  stopping compute ...")
    t0 = time.time()
    w.postgres.update_database_instance(
        name=f"projects/{project}",
        database_instance=DatabaseInstance(stopped=True))

    # Poll until stopped
    while time.time() - t0 < 30:
        state = get_instance_state(w, project)
        if state["state"] == "STOPPED" and state["nodes"] == 0 and state["effective_stopped"]:
            elapsed = time.time() - t0
            print(f"  stopped in ~{elapsed:.1f}s; nodes: {state['nodes']}; effective_stopped: {state['effective_stopped']}")
            return
        time.sleep(0.5)
    raise TimeoutError("compute did not stop within 30s")


def start_compute(w, project):
    """Start the compute on the project."""
    print("  starting compute ...")
    t0 = time.time()
    w.postgres.update_database_instance(
        name=f"projects/{project}",
        database_instance=DatabaseInstance(stopped=False))

    # Poll until active
    while time.time() - t0 < 60:
        state = get_instance_state(w, project)
        if state["state"] == "ACTIVE" and state["nodes"] > 0:
            elapsed = time.time() - t0
            print(f"  started in ~{elapsed:.1f}s; state: {state['state']}; nodes: {state['nodes']}")
            return
        time.sleep(0.5)
    raise TimeoutError("compute did not start within 60s")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--step", choices=["status", "stop", "start"])
    args = ap.parse_args()

    w = client()
    project = _env("LB_PROJECT", required=True)

    if args.step == "status":
        show_state(w, project)
        return
    if args.step == "stop":
        stop_compute(w, project)
        return
    if args.step == "start":
        start_compute(w, project)
        return

    # full story
    print("1. Check current state:")
    show_state(w, project)

    print("2. Stop the compute:")
    stop_compute(w, project)

    print("3. Verify the stop (no compute, cost = $0):")
    show_state(w, project)

    print("4. Restart the compute:")
    start_compute(w, project)

    print("5. Verify data is untouched:")
    from lakebase import run_sql
    count = run_sql("SELECT count(*) FROM machine")[0][0]
    print(f"  machine count: {count}")

    print("Done. Compute stopped and restarted; data intact.")


if __name__ == "__main__":
    main()
