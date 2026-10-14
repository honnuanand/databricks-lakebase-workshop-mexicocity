# Databricks notebook source
# MAGIC %md
# MAGIC # Query via REST: the Data API, step by step
# MAGIC
# MAGIC A hands-on lab. Run one cell at a time, read what happened, then move on. You will make HTTP requests to the Lakebase Data API using Databricks OAuth tokens. If the Data API is enabled on your instance, you will fetch and filter data as JSON. If it is not enabled, the notebook shows you how to enable it.
# MAGIC
# MAGIC **Before you start:** run `00-setup/setup_databricks` once to create your branch, then run the setup cells below.

# COMMAND ----------

# MAGIC %md
# MAGIC ## Run first: install the driver and pick your branch
# MAGIC Run the next three cells before anything else. They install the Postgres driver, upgrade the
# MAGIC Databricks SDK if your environment's version predates the Lakebase API, and set `LB_PROJECT`,
# MAGIC `LB_BRANCH`, and `LB_SCHEMA` from the widgets at the top of this notebook.
# MAGIC `LB_BRANCH` defaults to the branch `00-setup/setup_databricks` created for you. Change a widget
# MAGIC only if you used a different project or branch name.

# COMMAND ----------

# MAGIC %pip install "databricks-sdk>=0.120.0" "psycopg[binary]==3.3.4"

# COMMAND ----------

dbutils.library.restartPython()

# COMMAND ----------

import os, sys
sys.path.insert(0, os.path.join(os.getcwd(), "..", "..", "common", "scripts"))
from lakebase import notebook_env
notebook_env(dbutils);

# COMMAND ----------

# MAGIC %md
# MAGIC ## Setup, install httpx and get your connection info

# COMMAND ----------

import os, sys
sys.path.insert(0, os.path.join(os.getcwd(), "..", "..", "common", "scripts"))

# Use httpx if available, otherwise fall back to requests
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
    
    class httpx:
        Client = _RequestsClient

from lakebase import client, branch_endpoint, _env

print("HTTP client ready (httpx or requests shim).")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 1, Get connection info and OAuth token

# COMMAND ----------

import json
import subprocess

profile = _env("LB_PROFILE", required=True)
project = _env("LB_PROJECT", required=True)
branch = _env("LB_BRANCH", required=True)

w = client(profile)
host, _, _ = branch_endpoint(w, project, branch)

print(f"Connection info:")
print(f"  Profile: {profile}")
print(f"  Project: {project}")
print(f"  Branch: {branch}")
print(f"  Host: {host}")
print(f"  Data API URL: https://{host}/api/v1/")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 2, Get an OAuth token from Databricks

# COMMAND ----------

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

token = get_oauth_token(profile)
print(f"OAuth token acquired.")
print(f"  Token: {token[:20]}... (truncated)")
print(f"  Expires in: 3600 seconds (1 hour)")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 3, Check if the Data API is enabled on your instance

# COMMAND ----------

url = f"https://{host}/api/v1/bank.account"
headers = {"Authorization": f"Bearer {token}"}

print(f"Checking Data API:")
print(f"  URL: {url}")
print(f"  Method: GET")
print()

try:
    with httpx.Client(timeout=10) as client_http:
        response = client_http.get(url, headers=headers, params={"limit": 1})
        if response.status_code == 200:
            print("SUCCESS: Data API is ENABLED")
            data_api_enabled = True
        elif response.status_code == 404:
            print("NOT FOUND: Data API endpoint not available (NOT ENABLED)")
            print()
            print("To enable the Data API:")
            print("  1. Go to Databricks console: Data Engineering -> Lakebase -> Instances")
            print("  2. Select your instance")
            print("  3. In Advanced settings, toggle Data API to ON")
            print("  4. Wait 30 seconds for it to become available")
            print("  5. Re-run this notebook")
            data_api_enabled = False
        else:
            print(f"Unexpected response: {response.status_code}")
            print(f"Response: {response.text}")
            data_api_enabled = False
except Exception as e:
    print(f"Error: {e}")
    data_api_enabled = False

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 4, Fetch all accounts via REST (if enabled)

# COMMAND ----------

if not data_api_enabled:
    print("Skipping: Data API is not enabled. Enable it first (see Step 3).")
else:
    url = f"https://{host}/api/v1/bank.account"
    headers = {"Authorization": f"Bearer {token}"}

    print(f"Fetching all accounts:")
    print(f"  URL: {url}")
    print()

    try:
        with httpx.Client(timeout=10) as client_http:
            response = client_http.get(url, headers=headers)
            response.raise_for_status()
            accounts = response.json()
            print(f"Result: {len(accounts)} accounts")
            if accounts:
                print(f"\nFirst account:")
                print(f"  {accounts[0]}")
    except Exception as e:
        print(f"Error: {e}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 5, Filter with query parameters

# COMMAND ----------

if not data_api_enabled:
    print("Skipping: Data API is not enabled.")
else:
    url = f"https://{host}/api/v1/bank.account"
    headers = {"Authorization": f"Bearer {token}"}
    params = {"select": "account_id,status", "status": "eq.good_standing"}

    print(f"Fetching only good_standing accounts:")
    print(f"  URL: {url}")
    print(f"  Params: {params}")
    print()

    try:
        with httpx.Client(timeout=10) as client_http:
            response = client_http.get(url, headers=headers, params=params)
            response.raise_for_status()
            accounts = response.json()
            print(f"Result: {len(accounts)} good_standing accounts")
            print(f"\nSample accounts:")
            for account in accounts[:3]:
                print(f"  {account}")
    except Exception as e:
        print(f"Error: {e}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 6, Compare REST to SQL
# MAGIC
# MAGIC The same query in SQL:
# MAGIC
# MAGIC ```sql
# MAGIC SELECT account_id, status FROM bank.account WHERE status = 'good_standing'
# MAGIC ```

# COMMAND ----------

from lakebase import connect

if not data_api_enabled:
    print("Skipping: Data API is not enabled.")
else:
    print("SQL equivalent:")
    print("  SELECT account_id, status FROM bank.account WHERE status = 'good_standing'")
    print()

    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT account_id, status FROM bank.account WHERE status = 'good_standing'")
            sql_rows = cur.fetchall()
            print(f"SQL result: {len(sql_rows)} rows")
            print(f"\nSample rows:")
            for row in sql_rows[:3]:
                print(f"  {row}")

    print(f"\nBoth REST and SQL return the same data. REST is useful for web/mobile clients.")

# COMMAND ----------

# MAGIC %md
# MAGIC ## What you learned
# MAGIC
# MAGIC The Data API lets you query Lakebase via HTTP using Databricks OAuth tokens, perfect for web applications, mobile apps, or any client that speaks JSON and REST. The API supports filtering (like SQL WHERE), column selection (like SQL SELECT), and aggregates. Once enabled, the Data API bridges PostgreSQL and HTTP-based clients without needing a direct database connection.
# MAGIC
# MAGIC Key takeaways:
# MAGIC
# MAGIC - OAuth tokens expire in 1 hour; refresh before making long-running scripts.
# MAGIC - The Data API respects row-level security (RLS) and role-based access control (RBAC) from your Lakebase config.
# MAGIC - For bulk operations or complex joins, direct SQL is faster than multiple REST calls.

# COMMAND ----------

# MAGIC %md
# MAGIC ---
# MAGIC **Next in the App developers track:** <a href="$../capstone-app/capstone_app_databricks">Building a Databricks App on Lakebase →</a>
# MAGIC
# MAGIC <a href="$../../START_HERE">← Back to the table of contents</a>
