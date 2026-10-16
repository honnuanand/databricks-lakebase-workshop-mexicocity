#!/usr/bin/env python3
"""Create YOUR Lakebase project and set up its Data API access.

Each attendee owns a project, bank-<email name> (LB_PROJECT). It comes with a
`production` branch; 00-setup/setup_databricks loads the bank there and forks
your branch (LB_BRANCH) from it.

The Data API refuses the project owner's identity, so the Data API journey calls
it as a workshop service principal instead. The instructor creates that service
principal once and stores its client id and secret in the `lakebase-workshop`
secret scope; grant_data_api() gives it read access to the bank on a branch, and
enable_data_api() turns the Data API on for a branch.

Usage (from a notebook, after notebook_env):
    import project
    project.create()                      # idempotent, waits until production is ACTIVE
    project.grant_data_api(sp_app_id)     # on production, so forks inherit the role
    project.enable_data_api()             # on your branch (LB_BRANCH)

Env: LB_PROFILE, LB_PROJECT, LB_BRANCH, LB_SCHEMA (see 00-setup/).
"""
from __future__ import annotations

import time

from google.protobuf.duration_pb2 import Duration
from databricks.sdk.errors import NotFound
from databricks.sdk.service.postgres import (DataApi, DataApiDataApiSpec, Project, ProjectSpec,
                                             ProjectDefaultEndpointSettings)

from lakebase import client, connect, branch_endpoint, wait_active, _env, _t

PRODUCTION = "production"
PG_VERSION = 17
SUSPEND_TIMEOUT_S = 300   # 5 minutes, so Scale to Zero shows a real suspend and cold wake
DATABASE_ID = "databricks-postgres"


def create() -> None:
    """Create your project if it doesn't exist, then wait until production is ACTIVE."""
    w = client()
    project = _env("LB_PROJECT", required=True)
    try:
        existing = w.postgres.get_project(name=f"projects/{project}")
    except NotFound:
        existing = None
    if existing and existing.delete_time:
        # A deleted project keeps its name for 7 days, so it can't be created again; restore it.
        w.postgres.undelete_project(name=f"projects/{project}").wait()
        print(_t(f"project {project} was deleted, so it was restored",
                 f"el proyecto {project} estaba eliminado, así que se restauró"))
    elif existing:
        print(_t(f"project {project} already exists", f"el proyecto {project} ya existe"))
    else:
        t0 = time.time()
        w.postgres.create_project(
            project=Project(spec=ProjectSpec(
                display_name=project, pg_version=PG_VERSION,
                default_endpoint_settings=ProjectDefaultEndpointSettings(
                    suspend_timeout_duration=Duration(seconds=SUSPEND_TIMEOUT_S)))),
            project_id=project)
        ms = (time.time() - t0) * 1000
        print(_t(f"create_project API returned in {ms:.0f} ms", f"la API create_project respondió en {ms:.0f} ms"))
    waited = wait_active(w, project, PRODUCTION, timeout_s=180, idle_ok=True)
    _, _, state = branch_endpoint(w, project, PRODUCTION)
    print(_t(f"project {project}: branch {PRODUCTION} is {state} in ~{waited:.1f}s",
             f"proyecto {project}: la rama {PRODUCTION} está {state} en ~{waited:.1f}s"))


def grant_data_api(sp_app_id: str, branch: str = PRODUCTION) -> None:
    """Give the workshop service principal a Postgres role on a branch that the Data API can
    use, with read access to the bank. Idempotent. Run it on production, before forking, so
    your branch (and any reset of it) inherits the role."""
    schema = _env("LB_SCHEMA", "bank")
    role = f'"{sp_app_id}"'
    with connect(branch=branch) as conn:
        with conn.cursor() as cur:
            cur.execute("CREATE EXTENSION IF NOT EXISTS databricks_auth")
            cur.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", [sp_app_id])
            if cur.fetchone() is None:
                cur.execute("SELECT databricks_create_role(%s, 'SERVICE_PRINCIPAL')", [sp_app_id])
            cur.execute(f"GRANT {role} TO authenticator")
            cur.execute(f"GRANT USAGE ON SCHEMA {schema} TO {role}")
            cur.execute(f"GRANT SELECT ON ALL TABLES IN SCHEMA {schema} TO {role}")
            # tables the journeys create later are readable too
            cur.execute(f"ALTER DEFAULT PRIVILEGES IN SCHEMA {schema} GRANT SELECT ON TABLES TO {role}")
    print(_t(f"Data API role ready on {branch}: the workshop service principal can read {schema}",
             f"rol de la Data API listo en {branch}: el service principal del taller puede leer {schema}"))


def enable_data_api(branch: str | None = None) -> str:
    """Turn the Data API on for a branch, exposing the bank schema. Idempotent. Returns its URL."""
    w = client()
    project = _env("LB_PROJECT", required=True)
    branch = branch or _env("LB_BRANCH", required=True)
    schema = _env("LB_SCHEMA", "bank")
    parent = f"projects/{project}/branches/{branch}/databases/{DATABASE_ID}"
    try:
        url = w.postgres.get_data_api(name=f"{parent}/data-api").status.url
    except Exception:
        w.postgres.create_data_api(parent=parent, data_api=DataApi(spec=DataApiDataApiSpec(db_schemas=[schema])))
        url = ""
        t0 = time.time()
        while not url and time.time() - t0 < 60:
            time.sleep(2)
            try:
                url = w.postgres.get_data_api(name=f"{parent}/data-api").status.url or ""
            except Exception:
                pass
    if not url:
        raise TimeoutError(_t(f"the Data API on {branch} has no URL after 60s",
                              f"la Data API de {branch} no tiene URL después de 60s"))
    print(_t(f"Data API on {branch}: {url}", f"Data API en {branch}: {url}"))
    return url
