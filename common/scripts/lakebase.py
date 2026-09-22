#!/usr/bin/env python3
"""Shared Lakebase helper for the workshop.

A thin, honest wrapper over the Databricks SDK's Postgres (Autoscaling) surface
plus psycopg, so every journey's script can connect to YOUR branch and run SQL
without re-writing the plumbing. See docs/lakebase-sdk.md for the concepts.

Config comes from environment (or a .env you export), so nothing here is
hard-coded to any workspace:

    LB_PROFILE      Databricks CLI profile to auth as (from 00-setup/auth.md)
    LB_PROJECT      the Lakebase project id (from 00-setup/provision.md)
    LB_BRANCH       your branch id, e.g. u-alex (from 00-setup/your-branch.md)
    LB_SCHEMA       schema to use (default: factory)

Usage (from another script):
    from lakebase import connect, run_sql, branch_endpoint
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT count(*) FROM machine")
            print(cur.fetchone())

Or as a CLI smoke test:
    python lakebase.py --check          # SELECT 1 on your branch
    python lakebase.py --sql "SELECT machine_id, status FROM factory.machine"
"""
from __future__ import annotations

import argparse
import os
import time
from typing import Optional

import psycopg
from databricks.sdk import WorkspaceClient

PG_PORT = 5432
DEFAULT_DB = "databricks_postgres"
PRIMARY_ENDPOINT = "primary"


def _env(name: str, default: Optional[str] = None, required: bool = False) -> str:
    val = os.getenv(name, default)
    if required and not val:
        raise SystemExit(
            f"Missing required env var {name}. Set it (see 00-setup/) e.g.:\n"
            f"  export {name}=...")
    return val or ""


def client(profile: Optional[str] = None) -> WorkspaceClient:
    profile = profile or _env("LB_PROFILE")
    return WorkspaceClient(profile=profile) if profile else WorkspaceClient()


def branch_name(project: str, branch: str) -> str:
    return f"projects/{project}/branches/{branch}"


def branch_endpoint(w: WorkspaceClient, project: str, branch: str) -> tuple[str, str, str]:
    """Return (host, endpoint_id, state) for a branch's primary endpoint.

    Readiness is endpoint.status.current_state == 'ACTIVE' (NOT .state — that
    attribute does not exist and silently breaks polling). See docs/lakebase-sdk.md.
    """
    eps = list(w.postgres.list_endpoints(parent=branch_name(project, branch)))
    if not eps:
        return "", PRIMARY_ENDPOINT, "NO_ENDPOINT"
    ep = eps[0]
    host = ep.status.hosts.host if ep.status and ep.status.hosts else ""
    state = ep.status.current_state.value if ep.status and ep.status.current_state else "UNKNOWN"
    eid = ep.endpoint_id or PRIMARY_ENDPOINT
    return host, eid, state


def wait_active(w: WorkspaceClient, project: str, branch: str, timeout_s: int = 30) -> float:
    """Poll until the branch endpoint is ACTIVE with a host. Returns seconds waited."""
    t0 = time.time()
    while time.time() - t0 < timeout_s:
        host, _, state = branch_endpoint(w, project, branch)
        if state == "ACTIVE" and host:
            return time.time() - t0
        time.sleep(0.4)
    raise TimeoutError(f"branch {branch} not ACTIVE within {timeout_s}s")


def connect(project: Optional[str] = None, branch: Optional[str] = None,
            dbname: str = DEFAULT_DB, profile: Optional[str] = None) -> psycopg.Connection:
    """Open a psycopg connection to YOUR branch, using a fresh OAuth credential
    as the password. autocommit=True so single statements just run."""
    w = client(profile)
    project = project or _env("LB_PROJECT", required=True)
    branch = branch or _env("LB_BRANCH", required=True)
    host, endpoint_id, state = branch_endpoint(w, project, branch)
    if not host:
        raise RuntimeError(f"branch '{branch}' has no endpoint host yet (state={state}). "
                           f"Is the branch provisioned? See 00-setup/your-branch.md.")
    cred = w.postgres.generate_database_credential(
        endpoint=f"{branch_name(project, branch)}/endpoints/{endpoint_id}")
    user = w.current_user.me().user_name
    conn = psycopg.connect(
        host=host, port=PG_PORT, dbname=dbname,
        user=user, password=cred.token,
        sslmode="require", autocommit=True, connect_timeout=20)
    schema = _env("LB_SCHEMA", "factory")
    with conn.cursor() as cur:
        cur.execute(f"SET search_path TO {schema}, public")
    return conn


def run_sql(sql: str, project: Optional[str] = None, branch: Optional[str] = None) -> list[tuple]:
    """Run SQL on your branch; return rows if the last statement is a SELECT."""
    with connect(project, branch) as conn:
        with conn.cursor() as cur:
            cur.execute(sql)
            return cur.fetchall() if cur.description else []


def _main() -> None:
    ap = argparse.ArgumentParser(description="Lakebase branch smoke test / SQL runner")
    ap.add_argument("--check", action="store_true", help="SELECT 1 on your branch")
    ap.add_argument("--sql", help="run a SQL statement and print rows")
    args = ap.parse_args()

    if args.check or not args.sql:
        rows = run_sql("SELECT 1")
        print("branch OK, SELECT 1 ->", rows[0][0] if rows else "?")
    if args.sql:
        for r in run_sql(args.sql):
            print(r)


if __name__ == "__main__":
    _main()
