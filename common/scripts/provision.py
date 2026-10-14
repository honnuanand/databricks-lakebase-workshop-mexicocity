#!/usr/bin/env python3
"""Provision a workshop-owned Lakebase project (so learners never touch a demo's).

Creates an Autoscaling project, which comes with a `production` branch and a
primary endpoint, then waits until it's ACTIVE and queryable. Idempotent: an
existing project of the same id is reported as already-live.

Usage:
    python provision.py --project bank --profile workshop
    python provision.py --project bank --profile workshop --status   # just check

After it prints ACTIVE, set:  export LB_PROJECT=<project>
"""
from __future__ import annotations

import argparse
import time

from databricks.sdk import WorkspaceClient
from databricks.sdk.service.postgres import Project, ProjectSpec

PRODUCTION = "production"


def _endpoint_state(w, project) -> tuple[str, str]:
    parent = f"projects/{project}/branches/{PRODUCTION}"
    try:
        eps = list(w.postgres.list_endpoints(parent=parent))
    except Exception:
        return "", "PROVISIONING"
    if not eps:
        return "", "NO_ENDPOINT"
    ep = eps[0]
    host = ep.status.hosts.host if ep.status and ep.status.hosts else ""
    state = ep.status.current_state.value if ep.status and ep.status.current_state else "UNKNOWN"
    return host, state


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", required=True, help="project id, e.g. bank")
    ap.add_argument("--profile", required=True)
    ap.add_argument("--pg-version", type=int, default=17)
    ap.add_argument("--status", action="store_true", help="report state, don't create")
    ap.add_argument("--timeout", type=int, default=120)
    args = ap.parse_args()

    w = WorkspaceClient(profile=args.profile)

    if not args.status:
        t0 = time.time()
        try:
            w.postgres.create_project(
                project=Project(spec=ProjectSpec(display_name=args.project, pg_version=args.pg_version)),
                project_id=args.project)
            print(f"create_project API returned in {(time.time()-t0)*1000:.0f} ms")
        except Exception as e:
            if "already exists" in str(e).lower():
                print(f"project {args.project} already exists (live)")
            else:
                raise

    # poll to ACTIVE
    t0 = time.time()
    while time.time() - t0 < args.timeout:
        host, state = _endpoint_state(w, args.project)
        if state == "ACTIVE" and host:
            print(f"project {args.project} production endpoint ACTIVE in ~{time.time()-t0:.1f}s")
            print(f"  host: {host}")
            print(f"\nNow run:  export LB_PROJECT={args.project}")
            return
        time.sleep(1)
    host, state = _endpoint_state(w, args.project)
    raise SystemExit(f"project not ACTIVE within {args.timeout}s (state={state})")


if __name__ == "__main__":
    main()
