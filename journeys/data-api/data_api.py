#!/usr/bin/env python3
"""Query Lakebase via REST: the Data API.

Makes HTTP requests to the Lakebase Data API (if enabled on your instance),
using Databricks OAuth tokens for auth. Demonstrates REST vs SQL queries.

Usage:
    python data_api.py              # full test
    python data_api.py --step check # check if Data API is enabled
    python data_api.py --step token # get an OAuth token
    python data_api.py --step get-machines  # fetch via REST
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import os, sys
# The shared Lakebase helper lives in common/scripts/. Make it importable
# from this journey folder no matter where you run the script from.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "common", "scripts"))
from lakebase import client, branch_endpoint, connect, _env

# Use httpx if present, otherwise fall back to requests (a workshop dependency).
# Both expose a Client() context manager with .get()/.post() here, so the call sites
# below work either way. No runtime pip install.
try:
    import httpx
except ImportError:
    import requests

    class _RequestsClient:
        def __init__(self, timeout=10):
            self._s = requests.Session()
            self._timeout = timeout

        def __enter__(self):
            return self

        def __exit__(self, *a):
            self._s.close()

        def get(self, url, headers=None, params=None):
            return self._s.get(url, headers=headers, params=params, timeout=self._timeout)

        def post(self, url, headers=None, json=None):
            return self._s.post(url, headers=headers, json=json, timeout=self._timeout)

    class httpx:  # shim namespace so `httpx.Client(...)` keeps working
        Client = _RequestsClient


def get_oauth_token(profile: str) -> str:
    """Get a Databricks OAuth token."""
    result = subprocess.run(
        ["databricks", "auth", "token", "--profile", profile, "--output", "json"],
        capture_output=True,
        text=True,
        check=True
    )
    data = json.loads(result.stdout)
    return data["access_token"]


def check_data_api(host: str, token: str) -> tuple[bool, str]:
    """Check if the Data API is enabled on the instance."""
    url = f"https://{host}/api/v1/bank.account"
    headers = {"Authorization": f"Bearer {token}"}

    try:
        with httpx.Client(timeout=10) as http:
            response = http.get(url, headers=headers, params={"limit": 1})
            if response.status_code == 200:
                return True, "Data API is ENABLED"
            elif response.status_code == 404:
                return False, "Data API endpoint not found (NOT ENABLED)"
            else:
                return False, f"Data API returned {response.status_code}"
    except Exception as e:
        return False, f"Could not reach Data API: {e}"


def get_machines(host: str, token: str) -> list[dict]:
    """Fetch all machines via REST."""
    url = f"https://{host}/api/v1/bank.account"
    headers = {"Authorization": f"Bearer {token}"}

    with httpx.Client(timeout=10) as http:
        response = http.get(url, headers=headers)
        response.raise_for_status()
        return response.json()


def get_filtered_machines(host: str, token: str) -> list[dict]:
    """Fetch only healthy machines via REST."""
    url = f"https://{host}/api/v1/bank.account"
    headers = {"Authorization": f"Bearer {token}"}
    params = {"select": "account_id,status", "status": "eq.healthy"}

    with httpx.Client(timeout=10) as http:
        response = http.get(url, headers=headers, params=params)
        response.raise_for_status()
        return response.json()


def main() -> None:
    ap = argparse.ArgumentParser(description="Query Lakebase via REST Data API")
    ap.add_argument("--step", choices=["check", "token", "get-machines", "get-filtered",
                                       "compare-sql", "post-read-only"],
                    help="run a specific step")
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()

    profile = _env("LB_PROFILE", required=True)
    project = _env("LB_PROJECT", required=True)
    branch = _env("LB_BRANCH", required=True)

    w = client(profile)
    host, _, _ = branch_endpoint(w, project, branch)

    if not host:
        print("Error: branch endpoint not ready. Check your setup.")
        return

    if args.step == "check" or not args.step:
        print(f"Data API check:")
        print(f"  Host: https://{host}")
        print(f"  Endpoint: /api/v1/bank.account")

        try:
            token = get_oauth_token(profile)
            enabled, msg = check_data_api(host, token)
            print(f"  Status: {msg}")
            if not enabled:
                print("\nTo enable: Databricks console → Lakebase → Instances → select your "
                      "instance → Advanced settings → toggle Data API ON")
        except Exception as e:
            print(f"  Error: {e}")
        if args.step:
            return

    try:
        token = get_oauth_token(profile)
    except Exception as e:
        print(f"Error getting OAuth token: {e}")
        return

    if args.step == "token" or not args.step:
        print(f"\nOAuth token acquired:")
        print(f"  Token: {token[:20]}... (truncated)")
        print(f"  Expires in: 3600 seconds (1 hour)")
        if args.step:
            return

    # In the full run, if the Data API is not enabled on this instance, stop here with
    # the honest explainer rather than making calls that return 400. The Data API is
    # turned on from the Lakebase UI (no programmatic switch), so this is expected.
    if not args.step:
        enabled, msg = check_data_api(host, token)
        if not enabled:
            print(f"\nThe Data API is not enabled on this instance ({msg}).")
            print("This journey makes real HTTPS calls when it is enabled; it does not mock them.")
            print("To enable it: Databricks console -> Lakebase -> your instance -> Settings ->")
            print("turn on the Data API, then re-run. The calls below are what you would run:")
            print("  GET  https://<host>/api/v1/bank.account")
            print("  GET  https://<host>/api/v1/bank.account?select=account_id,status&status=eq.healthy")
            print("\nEverything up to here is real: the OAuth token above is live. The REST reads")
            print("just need the Data API switched on, which is an instance setting, not a script step.")
            return

    if args.step == "get-machines" or not args.step:
        print(f"\nFetching machines via REST...")
        try:
            accounts = get_machines(host, token)
            print(f"  Result: {len(machines)} rows returned")
            if machines:
                print(f"  Sample: {accounts[0]}")
        except Exception as e:
            print(f"  Error: {e}")
        if args.step:
            return

    if args.step == "get-filtered" or not args.step:
        print(f"\nFetching filtered (healthy) machines via REST...")
        try:
            accounts = get_filtered_machines(host, token)
            print(f"  Result: {len(machines)} rows returned")
            if machines:
                print(f"  Sample: {accounts[0]}")
        except Exception as e:
            print(f"  Error: {e}")
        if args.step:
            return

    if args.step == "compare-sql":
        print(f"\nComparing REST vs SQL...")
        try:
            accounts = get_filtered_machines(host, token)
            print(f"  REST result: {len(machines)} machines")

            with connect() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT account_id, status FROM bank.account WHERE status = 'healthy'")
                    sql_rows = cur.fetchall()
                    print(f"  SQL result: {len(sql_rows)} machines")
                    print(f"  Results match: {'✓' if len(machines) == len(sql_rows) else '✗'}")
        except Exception as e:
            print(f"  Error: {e}")

    if args.step == "post-read-only":
        print(f"\nTesting POST (insert) via REST (may be read-only)...")
        url = f"https://{host}/api/v1/bank.account"
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        data = {
            "account_id": "M-TEST-999",
            "branch_id": "BR-TEST",
            "line": "Test",
            "type": "test",
            "status": "healthy",
            "health_pct": 100.0
        }

        try:
            with httpx.Client(timeout=10) as http:
                response = http.post(url, headers=headers, json=data)
                if response.status_code in [200, 201]:
                    print(f"  Success: {response.status_code}")
                else:
                    print(f"  Result: {response.status_code}")
                    print(f"  Response: {response.text}")
        except Exception as e:
            print(f"  Error: {e}")


if __name__ == "__main__":
    main()
