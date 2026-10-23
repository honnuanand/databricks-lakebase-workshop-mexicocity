#!/usr/bin/env python3
"""Shared Lakebase helper for the workshop.

A thin, honest wrapper over the Databricks SDK's Postgres (Autoscaling) surface
plus psycopg, so every journey's script can connect to YOUR branch and run SQL
without re-writing the plumbing. See docs/lakebase-sdk.md for the concepts.

Config comes from environment (or a .env you export), so nothing here is
hard-coded to any workspace:

    LB_PROFILE      Databricks CLI profile to auth as (from 00-setup/auth.md)
    LB_PROJECT      your Lakebase project id, e.g. bank-alex (created by 00-setup/setup_databricks)
    LB_BRANCH       your branch id, e.g. u-alex (from 00-setup/your-branch.md)
    LB_SCHEMA       schema to use (default: bank)
    LB_LANG         language for printed messages: en (default) or es

Usage (from another script):
    from lakebase import connect, run_sql, branch_endpoint
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT count(*) FROM account")
            print(cur.fetchone())

Or as a CLI smoke test:
    python lakebase.py --check          # SELECT 1 on your branch
    python lakebase.py --sql "SELECT account_id, status FROM bank.account"
"""
from __future__ import annotations

import argparse
import os
import re
import time
from typing import Optional

import psycopg
from databricks.sdk import WorkspaceClient

PG_PORT = 5432
DEFAULT_DB = "databricks_postgres"
PRIMARY_ENDPOINT = "primary"


def _t(en: str, es: str) -> str:
    """Pick a printed message by LB_LANG (set by notebook_env(..., lang="es")). English by default."""
    return es if os.getenv("LB_LANG") == "es" else en


def _env(name: str, default: Optional[str] = None, required: bool = False) -> str:
    val = os.getenv(name, default)
    if required and not val:
        raise SystemExit(_t(
            f"Missing required env var {name}. Set it (see 00-setup/) e.g.:\n"
            f"  export {name}=...",
            f"Falta la variable de entorno requerida {name}. Defínela (ver 00-setup/), por ejemplo:\n"
            f"  export {name}=..."))
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


def wait_active(w: WorkspaceClient, project: str, branch: str, timeout_s: int = 30,
                idle_ok: bool = False) -> float:
    """Poll until the branch endpoint is ACTIVE with a host. Returns seconds waited.

    idle_ok=True also accepts IDLE: a suspended endpoint wakes on the next connection, so it's
    ready to use, and polling alone never wakes it."""
    t0 = time.time()
    while time.time() - t0 < timeout_s:
        host, _, state = branch_endpoint(w, project, branch)
        if host and (state == "ACTIVE" or (idle_ok and state == "IDLE")):
            return time.time() - t0
        time.sleep(0.4)
    raise TimeoutError(_t(f"branch {branch} not ACTIVE within {timeout_s}s",
                          f"la rama {branch} no llegó a ACTIVE en {timeout_s}s"))


def connect(project: Optional[str] = None, branch: Optional[str] = None,
            dbname: str = DEFAULT_DB, profile: Optional[str] = None) -> psycopg.Connection:
    """Open a psycopg connection to YOUR branch, using a fresh OAuth credential
    as the password. autocommit=True so single statements just run."""
    w = client(profile)
    project = project or _env("LB_PROJECT", required=True)
    branch = branch or _env("LB_BRANCH", required=True)
    host, endpoint_id, state = branch_endpoint(w, project, branch)
    if not host:
        raise RuntimeError(_t(f"branch '{branch}' has no endpoint host yet (state={state}). "
                              f"Is the branch provisioned? See 00-setup/your-branch.md.",
                              f"la rama '{branch}' todavía no tiene host de endpoint (state={state}). "
                              f"¿Ya se creó la rama? Ver 00-setup/your-branch.md."))
    cred = w.postgres.generate_database_credential(
        endpoint=f"{branch_name(project, branch)}/endpoints/{endpoint_id}")
    user = w.current_user.me().user_name
    conn = psycopg.connect(
        host=host, port=PG_PORT, dbname=dbname,
        user=user, password=cred.token,
        sslmode="require", autocommit=True, connect_timeout=20)
    schema = _env("LB_SCHEMA", "bank")
    with conn.cursor() as cur:
        cur.execute(f"SET search_path TO {schema}, public")
    return conn


def run_sql(sql: str, project: Optional[str] = None, branch: Optional[str] = None) -> list[tuple]:
    """Run SQL on your branch; return rows if the last statement is a SELECT."""
    with connect(project, branch) as conn:
        with conn.cursor() as cur:
            cur.execute(sql)
            return cur.fetchall() if cur.description else []


def _email_name(user_name: str) -> str:
    """The part of an email before the @, as lowercase letters, digits, and hyphens."""
    return re.sub(r"[^a-z0-9]+", "-", user_name.split("@")[0].lower()).strip("-")


def default_branch(user_name: str) -> str:
    """The workshop's branch name for a user: u-<email name>, e.g.
    alex.kim@example.com -> u-alex-kim. Lowercase letters, digits, and hyphens only."""
    return f"u-{_email_name(user_name)}"[:63]


def default_project(user_name: str) -> str:
    """The workshop's project name for a user: bank-<email name>, e.g.
    alex.kim@example.com -> bank-alex-kim. Each attendee creates their own."""
    return f"bank-{_email_name(user_name)}"[:63]


def notebook_env(dbutils, project: Optional[str] = None, schema: str = "bank", lang: str = "en") -> dict:
    """For Databricks notebooks: set LB_PROJECT, LB_BRANCH, LB_SCHEMA from widgets.

    A workspace has no workshop.env, so each notebook calls this once. It adds
    three widgets at the top of the notebook; LB_PROJECT defaults to your
    default_project() and LB_BRANCH to your default_branch(), the project and branch
    00-setup/setup_databricks creates. LB_PROFILE stays unset, so the SDK signs in as you
    automatically. lang="es" sets LB_LANG so the shared scripts print their messages in Spanish."""
    os.environ["LB_LANG"] = lang
    w = client()
    if not hasattr(w, "postgres"):
        import databricks.sdk
        v = databricks.sdk.version.__version__
        raise SystemExit(_t(
            f"databricks-sdk {v} predates the Lakebase API. Run the "
            f'%pip install "databricks-sdk>=0.120.0" cell and the restart cell above, then rerun this one.',
            f"databricks-sdk {v} es anterior a la API de Lakebase. Ejecuta la celda "
            f'%pip install "databricks-sdk>=0.120.0" y la celda de reinicio de arriba, y luego vuelve a ejecutar esta.'))
    me = w.current_user.me().user_name
    dbutils.widgets.text("LB_PROJECT", project or default_project(me))
    dbutils.widgets.text("LB_BRANCH", default_branch(me))
    dbutils.widgets.text("LB_SCHEMA", schema)
    env = {k: dbutils.widgets.get(k).strip() for k in ("LB_PROJECT", "LB_BRANCH", "LB_SCHEMA")}
    missing = [k for k, v in env.items() if not v]
    if missing:
        raise SystemExit(_t(f"Fill in {', '.join(missing)} in the widgets at the top of the notebook.",
                            f"Llena {', '.join(missing)} en los widgets de la parte superior del notebook."))
    os.environ.update(env)
    print(_t(f"signed in as {me}", f"sesión iniciada como {me}"))
    for k, v in env.items():
        print(f"  {k} = {v}")
    return env


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
