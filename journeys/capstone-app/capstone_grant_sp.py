#!/usr/bin/env python3
"""Grant a Databricks App's Service Principal access to Lakebase.

This script is the "capstone" version of ../lakebase-pitch/backend/grant_app_sp.py,
but parameterized for use in the workshop. It takes an app name and grants that
app's Service Principal the full permission chain needed to connect to Lakebase:

  1. Grant CAN_USE on the Lakebase project (so the app can find the branch and get credentials)
  2. Create a Postgres role for the SP with databricks_create_role() (OAuth login)
  3. Grant schema/table permissions on the branch

The workshop notebook capstone_app_databricks does the same steps from a workspace.

Usage:
    python capstone_grant_sp.py --app-name capstone-dashboard \\
      --lakebase-profile your-profile \\
      --lakebase-project bank \\
      --lakebase-schema bank

Prerequisites:
  - LB_HOST or derive from branch endpoint (set via --lakebase-profile)
  - App must already exist or will exist after deploy
  - You must have workspace admin + SP management permissions
"""
from __future__ import annotations

import argparse
import uuid
from typing import Optional

import psycopg
from databricks.sdk import WorkspaceClient

import os, sys
# The shared Lakebase helper lives in common/scripts/. Make it importable
# from this journey folder no matter where you run the script from.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "common", "scripts"))
from lakebase import client as make_ws_client, _env, branch_endpoint


def grant_app_sp(
    app_name: str,
    workspace_profile: str,
    lakebase_profile: str,
    lakebase_project: str,
    lakebase_branch: str = "production",
    lakebase_schema: str = "bank",
    lakebase_host: Optional[str] = None,
) -> None:
    """Grant an app's Service Principal full Lakebase access.

    Args:
        app_name: Databricks App name (e.g., capstone-dashboard)
        workspace_profile: Databricks CLI profile for workspace auth
        lakebase_profile: CLI profile for Lakebase (may be same)
        lakebase_project: Lakebase project ID
        lakebase_branch: branch to grant role on (default: production)
        lakebase_schema: schema to grant permissions for (default: bank)
        lakebase_host: Lakebase host (if None, derive from branch endpoint)
    """
    print(f"Granting Lakebase access to app Service Principal...")
    print(f"  App: {app_name}")
    print(f"  Project: {lakebase_project}")
    print(f"  Schema: {lakebase_schema}")
    print()

    # Step 1: get the app's Service Principal
    ws = make_ws_client(workspace_profile)
    try:
        # Look the app up by name (it must have been created first, which also
        # provisions its Service Principal).
        app_result = ws.apps.get(name=app_name)
        sp_id = getattr(app_result, "service_principal_id", None)
        sp_client_id = getattr(app_result, "service_principal_client_id", None)
        if not sp_id or not sp_client_id:
            print(f"Warning: App '{app_name}' has no Service Principal yet.")
            print(f"         Create the app first (databricks apps create {app_name}), then re-run.")
            return
    except Exception as e:
        print(f"Warning: Could not fetch app '{app_name}': {e}")
        print(f"         Create the app first (databricks apps create {app_name}), then re-run.")
        return
    print(f"  Found app Service Principal: client_id={sp_client_id}  id={sp_id}")

    # Step 3: Get Lakebase connection details for the branch the app will serve
    lb_ws = make_ws_client(lakebase_profile)
    host, endpoint_id, _ = branch_endpoint(lb_ws, lakebase_project, lakebase_branch)
    lakebase_host = lakebase_host or host
    if not lakebase_host:
        raise RuntimeError(f"Could not get endpoint for branch '{lakebase_branch}'")

    print(f"  Lakebase host: {lakebase_host}")

    # Step 4: Get an OAuth credential to connect as the current user (admin) to run the grants
    me = lb_ws.current_user.me()
    cred = lb_ws.postgres.generate_database_credential(
        endpoint=f"projects/{lakebase_project}/branches/{lakebase_branch}/endpoints/{endpoint_id}"
    )

    # Step 5: Connect to Lakebase and grant permissions
    print()
    print(f"  Creating PostgreSQL role and grants...")

    try:
        conn = psycopg.connect(
            host=lakebase_host,
            port=5432,
            dbname="databricks_postgres",
            user=me.user_name,
            password=cred.token,
            sslmode="require",
            autocommit=True,
            connect_timeout=20,
        )

        with conn.cursor() as cur:
            # Create a Postgres role linked to the service principal (OAuth login)
            cur.execute("CREATE EXTENSION IF NOT EXISTS databricks_auth")
            cur.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", [sp_client_id])
            if cur.fetchone():
                print(f"    Role already exists (skipped): {sp_client_id}")
            else:
                cur.execute("SELECT databricks_create_role(%s, 'SERVICE_PRINCIPAL')", [sp_client_id])
                print(f"    Created PostgreSQL role: {sp_client_id}")

            # Grant schema usage
            cur.execute(f'GRANT USAGE ON SCHEMA {lakebase_schema} TO "{sp_client_id}"')
            print(f"    Granted USAGE on schema {lakebase_schema}")

            # Grant table permissions
            cur.execute(f'''
                GRANT SELECT ON ALL TABLES IN SCHEMA {lakebase_schema}
                TO "{sp_client_id}"
            ''')
            print(f"    Granted SELECT on all tables in {lakebase_schema}")

            # Set default privileges for future tables
            cur.execute(f'''
                ALTER DEFAULT PRIVILEGES IN SCHEMA {lakebase_schema}
                GRANT SELECT ON TABLES TO "{sp_client_id}"
            ''')
            print(f"    Set default SELECT privilege for future tables")

        conn.close()

    except Exception as e:
        print(f"    Error granting PostgreSQL permissions: {e}")
        raise

    # Step 6: Grant CAN_USE on the Lakebase project (workspace permission), so the app can list
    # the branch's endpoint and generate a database credential.
    from databricks.sdk.service.iam import AccessControlRequest, PermissionLevel
    ws.permissions.update("database-projects", lakebase_project, access_control_list=[
        AccessControlRequest(service_principal_name=sp_client_id, permission_level=PermissionLevel.CAN_USE)])
    print(f"    Granted CAN_USE on project {lakebase_project}")

    print()
    print(f"Done. App SP has access to Lakebase.")
    print(f"  Role name: {sp_client_id}")
    print(f"  Permissions: USAGE on schema, SELECT on tables")
    print()
    print(f"Next: deploy the app (bash app/deploy.sh {app_name})")


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Grant Databricks App Service Principal access to Lakebase"
    )
    ap.add_argument("--app-name", required=True, help="Databricks App name")
    ap.add_argument("--workspace-profile", default=None, help="CLI profile for workspace (default: same as lakebase-profile)")
    ap.add_argument("--lakebase-profile", required=True, help="CLI profile for Lakebase auth")
    ap.add_argument("--lakebase-project", required=True, help="Lakebase project ID")
    ap.add_argument("--lakebase-branch", default="production", help="Branch to grant role on")
    ap.add_argument("--lakebase-schema", default="bank", help="Schema to grant access to")
    ap.add_argument("--lakebase-host", default=None, help="Lakebase host (optional; derive from branch if not given)")
    args = ap.parse_args()

    workspace_profile = args.workspace_profile or args.lakebase_profile

    grant_app_sp(
        app_name=args.app_name,
        workspace_profile=workspace_profile,
        lakebase_profile=args.lakebase_profile,
        lakebase_project=args.lakebase_project,
        lakebase_branch=args.lakebase_branch,
        lakebase_schema=args.lakebase_schema,
        lakebase_host=args.lakebase_host,
    )


if __name__ == "__main__":
    main()
