#!/usr/bin/env python3
"""Query Lakebase via REST: the Data API.

Makes HTTP requests to the Lakebase Data API (if enabled on your branch, with the
`bank` schema exposed), using Databricks OAuth tokens for auth. Demonstrates REST vs
SQL queries. The REST URL comes from the branch's Data API settings
(`w.postgres.get_data_api(...).status.url`); requests go to `<url>/<schema>/<table>`.

Usage:
    python data_api.py              # full test
    python data_api.py --step check # check if Data API is enabled
    python data_api.py --step token # get an OAuth token
    python data_api.py --step get-accounts  # fetch via REST
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


def data_api_url(w, project: str, branch: str) -> str:
    """The branch's Data API base URL, or "" if the Data API isn't enabled on the branch."""
    try:
        return w.postgres.get_data_api(
            name=f"projects/{project}/branches/{branch}/databases/databricks-postgres/data-api").status.url
    except Exception:
        return ""


def check_data_api(base: str, token: str) -> tuple[bool, str]:
    """Check that the Data API answers for bank.account."""
    url = f"{base}/bank/account"
    headers = {"Authorization": f"Bearer {token}"}

    try:
        with httpx.Client(timeout=10) as http:
            response = http.get(url, headers=headers, params={"limit": 1})
            if response.status_code == 200:
                return True, "Data API is ENABLED"
            elif response.status_code == 403:
                return False, ("403: your Postgres role isn't granted to the Data API's `authenticator` role "
                               "(instructor setup; the project owner can't be used)")
            elif response.status_code == 406:
                return False, "406: the `bank` schema isn't exposed (Data API settings -> Exposed schemas)"
            else:
                return False, f"Data API returned {response.status_code}"
    except Exception as e:
        return False, f"Could not reach Data API: {e}"


def get_accounts(base: str, token: str) -> list[dict]:
    """Fetch all accounts via REST."""
    url = f"{base}/bank/account"
    headers = {"Authorization": f"Bearer {token}"}

    with httpx.Client(timeout=10) as http:
        response = http.get(url, headers=headers)
        response.raise_for_status()
        return response.json()


def get_filtered_accounts(base: str, token: str) -> list[dict]:
    """Fetch only good-standing accounts via REST."""
    url = f"{base}/bank/account"
    headers = {"Authorization": f"Bearer {token}"}
    params = {"select": "account_id,status", "status": "eq.good_standing"}

    with httpx.Client(timeout=10) as http:
        response = http.get(url, headers=headers, params=params)
        response.raise_for_status()
        return response.json()


def main() -> None:
    ap = argparse.ArgumentParser(description="Query Lakebase via REST Data API")
    ap.add_argument("--step", choices=["check", "token", "get-accounts", "get-filtered",
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
    base = data_api_url(w, project, branch)

    if args.step == "check" or not args.step:
        print(f"Data API check:")
        print(f"  Data API URL: {base or '(not enabled on this branch)'}")
        print(f"  Endpoint: <url>/bank/account")

        try:
            token = get_oauth_token(profile)
            enabled, msg = check_data_api(base, token) if base else (False, "Data API not enabled on this branch")
            print(f"  Status: {msg}")
            if not enabled:
                print("\nTo enable: Lakebase Postgres app -> your project -> your branch -> Data API -> "
                      "Enable Data API, then add `bank` under Exposed schemas")
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
        enabled, msg = check_data_api(base, token) if base else (False, "not enabled on this branch")
        if not enabled:
            print(f"\nThe Data API isn't ready on this branch ({msg}).")
            print("This journey makes real HTTPS calls when it is ready; it does not mock them.")
            print("To enable it: Lakebase Postgres app -> your project -> your branch -> Data API ->")
            print("Enable Data API, and add `bank` under Exposed schemas. The calls below are what you would run:")
            print("  GET  <url>/bank/account")
            print("  GET  <url>/bank/account?select=account_id,status&status=eq.good_standing")
            print("\nEverything up to here is real: the OAuth token above is live.")
            return

    if args.step == "get-accounts" or not args.step:
        print(f"\nFetching accounts via REST...")
        try:
            accounts = get_accounts(base, token)
            print(f"  Result: {len(accounts)} rows returned")
            if accounts:
                print(f"  Sample: {accounts[0]}")
        except Exception as e:
            print(f"  Error: {e}")
        if args.step:
            return

    if args.step == "get-filtered" or not args.step:
        print(f"\nFetching filtered (good_standing) accounts via REST...")
        try:
            accounts = get_filtered_accounts(base, token)
            print(f"  Result: {len(accounts)} rows returned")
            if accounts:
                print(f"  Sample: {accounts[0]}")
        except Exception as e:
            print(f"  Error: {e}")
        if args.step:
            return

    if args.step == "compare-sql":
        print(f"\nComparing REST vs SQL...")
        try:
            accounts = get_filtered_accounts(base, token)
            print(f"  REST result: {len(accounts)} accounts")

            with connect() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT account_id, status FROM bank.account WHERE status = 'good_standing'")
                    sql_rows = cur.fetchall()
                    print(f"  SQL result: {len(sql_rows)} accounts")
                    print(f"  Results match: {'✓' if len(accounts) == len(sql_rows) else '✗'}")
        except Exception as e:
            print(f"  Error: {e}")

    if args.step == "post-read-only":
        print(f"\nTesting POST (insert) via REST (may be read-only)...")
        url = f"{base}/bank/account"
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        data = {
            "account_id": "CTA-TEST-999",
            "branch_id": "BR-TEST",
            "line": "Test",
            "type": "test",
            "status": "good_standing",
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
