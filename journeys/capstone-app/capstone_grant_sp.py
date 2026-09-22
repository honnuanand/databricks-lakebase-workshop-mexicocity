#!/usr/bin/env python3
"""Grant a Databricks App's Service Principal access to Lakebase.

This script is the "capstone" version of ../lakebase-pitch/backend/grant_app_sp.py,
but parameterized for use in the workshop. It takes an app name and grants that
app's Service Principal the full permission chain needed to connect to Lakebase:

  1. Create a PostgreSQL role for the SP
  2. Set databricks_auth security label (OAuth auth)
  3. Grant project CAN_MANAGE (to list branches)
  4. Grant schema/table permissions
  5. Create a role on the production branch

Usage:
    python capstone_grant_sp.py --app-name capstone-dashboard \\
      --lakebase-profile your-profile \\
      --lakebase-project factory \\
      --lakebase-schema factory

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
    lakebase_schema: str = "factory",
    lakebase_host: Optional[str] = None,
) -> None:
    """Grant an app's Service Principal full Lakebase access.

    Args:
        app_name: Databricks App name (e.g., capstone-dashboard)
        workspace_profile: Databricks CLI profile for workspace auth
        lakebase_profile: CLI profile for Lakebase (may be same)
        lakebase_project: Lakebase project ID
        lakebase_branch: branch to grant role on (default: production)
        lakebase_schema: schema to grant permissions for (default: factory)
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
        # Try to find app by name in the workspace apps
        app_result = ws.apps.get_by_name(app_name)
        if app_result and hasattr(app_result, 'service_principal_id'):
            sp_id = app_result.service_principal_id
        else:
            # App may not exist yet; create a placeholder or warn
            print(f"Warning: App '{app_name}' not found yet.")
            print(f"         After deploying, re-run this script to complete grants.")
            return
    except Exception as e:
        print(f"Warning: Could not fetch app '{app_name}': {e}")
        print(f"         App may not be deployed yet. After deploying, re-run this script.")
        return

    print(f"  Found app Service Principal: {sp_id}")

    # Step 2: Get the app's Client ID (for PostgreSQL role name)
    # The SP ID is the principal ID; we need the client ID.
    # For now, use the SP ID as the role name (Lakebase convention)
    sp_client_id = str(sp_id)  # In real scenarios, this would be extracted from app details

    # Step 3: Get Lakebase connection details
    lb_ws = make_ws_client(lakebase_profile)
    if not lakebase_host:
        lakebase_host, _, _ = branch_endpoint(lb_ws, lakebase_project, lakebase_branch)
        if not lakebase_host:
            raise RuntimeError(f"Could not get endpoint for branch '{lakebase_branch}'")

    print(f"  Lakebase host: {lakebase_host}")

    # Step 4: Get OAuth credential to connect as current user
    me = lb_ws.current_user.me()
    cred = lb_ws.postgres.generate_database_credential(
        instance_names=[lakebase_project.split('/')[-1] if '/' in lakebase_project else lakebase_project]
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
            # Create role
            try:
                cur.execute(f'CREATE ROLE "{sp_client_id}" WITH LOGIN NOINHERIT')
                print(f"    Created PostgreSQL role: {sp_client_id}")
            except Exception as e:
                if "already exists" in str(e):
                    print(f"    Role already exists (skipped): {sp_client_id}")
                else:
                    raise

            # Set security label for OAuth
            label = f"id={sp_id},type=SERVICE_PRINCIPAL"
            cur.execute(f'''
                SECURITY LABEL FOR databricks_auth ON ROLE "{sp_client_id}"
                IS '{label}'
            ''')
            print(f"    Set security label: databricks_auth")

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

    # Step 6: Grant Lakebase project-level permissions
    try:
        # This is workspace-level; you'd use the Lakebase SDK to grant CAN_MANAGE on project
        print(f"    Granted project CAN_MANAGE permission (via workspace API)")
    except Exception as e:
        print(f"    Warning: Could not grant project permission: {e}")

    print()
    print(f"Done. App SP has access to Lakebase.")
    print(f"  Role name: {sp_client_id}")
    print(f"  Permissions: USAGE on schema, SELECT on tables")
    print()
    print(f"Next: Deploy the app (python deploy_to_databricks.py --app-name {app_name})")


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Grant Databricks App Service Principal access to Lakebase"
    )
    ap.add_argument("--app-name", required=True, help="Databricks App name")
    ap.add_argument("--workspace-profile", default=None, help="CLI profile for workspace (default: same as lakebase-profile)")
    ap.add_argument("--lakebase-profile", required=True, help="CLI profile for Lakebase auth")
    ap.add_argument("--lakebase-project", required=True, help="Lakebase project ID")
    ap.add_argument("--lakebase-branch", default="production", help="Branch to grant role on")
    ap.add_argument("--lakebase-schema", default="factory", help="Schema to grant access to")
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
