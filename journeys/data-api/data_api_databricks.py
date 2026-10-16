# Databricks notebook source
# MAGIC %md
# MAGIC # Query via REST: the Data API, step by step
# MAGIC
# MAGIC A hands-on lab. Run one cell at a time, read what happened, then move on. You will make HTTP requests to the Lakebase Data API using Databricks OAuth tokens. If the Data API is enabled on your instance, you will fetch and filter data as JSON. If it is not enabled, the notebook shows you how to enable it.
# MAGIC
# MAGIC **Before you start:** run `00-setup/setup_databricks` once to create your branch, then run the setup cells below. Needs: the **Data API enabled on your branch** with the `bank` schema exposed, and your Postgres role set up for it by your instructor (Step 3 explains). Without it, the REST steps skip themselves.

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
# MAGIC ## Step 1, Find your branch's Data API URL
# MAGIC
# MAGIC The Data API is enabled per branch. Its base URL comes from the branch's Data API settings; requests
# MAGIC go to `<url>/<schema>/<table>`, for example `<url>/bank/account`.
# MAGIC
# MAGIC **Not yet tested end to end.** The REST calls in Steps 3 to 5 follow the Databricks documentation, but
# MAGIC they haven't been run successfully in the workshop's workspace: the account that built the workshop
# MAGIC owns the project, and the Data API can't be called as the project owner. The setup checks in Steps 1
# MAGIC and 3 were run.

# COMMAND ----------

import json

project = _env("LB_PROJECT", required=True)
branch = _env("LB_BRANCH", required=True)

w = client()   # in a notebook, signs in as you; no CLI profile needed
host, endpoint_id, _ = branch_endpoint(w, project, branch)

try:
    rest_url = w.postgres.get_data_api(
        name=f"projects/{project}/branches/{branch}/databases/databricks-postgres/data-api").status.url
except Exception:
    rest_url = ""

print(f"Connection info:")
print(f"  Project: {project}")
print(f"  Branch: {branch}")
print(f"  Host: {host}")
print(f"  Data API URL: {rest_url or '(the Data API is not enabled on this branch)'}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 2, Get an OAuth token from Databricks
# MAGIC
# MAGIC The Data API accepts a Databricks OAuth token (a JWT) in the `Authorization: Bearer` header. In a
# MAGIC notebook, the simplest way to get one is the short-lived database credential, valid for about an hour.

# COMMAND ----------

def get_oauth_token() -> str:
    """Get a Databricks OAuth token (a JWT) for the signed-in user.

    The Data API needs an OAuth JWT. Inside a notebook, the SDK's own login is a workspace token,
    which the Data API rejects ("not a valid JWT encoding"), so this uses the same short-lived
    database credential that the other journeys use as their Postgres password."""
    return w.postgres.generate_database_credential(
        endpoint=f"projects/{project}/branches/{branch}/endpoints/{endpoint_id}").token

token = get_oauth_token()
print(f"OAuth token acquired.")
print(f"  Token: {token[:20]}... (truncated)")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 3, Check that the Data API answers for your branch

# COMMAND ----------

headers = {"Authorization": f"Bearer {token}"}
data_api_enabled = False

if not rest_url:
    print("The Data API is not enabled on your branch.")
    print()
    print("To enable it:")
    print("  1. Open the Lakebase Postgres app, then your project and your branch")
    print("  2. Open Data API and choose Enable Data API")
    print("  3. Under Exposed schemas, add bank")
    print("  4. Re-run this notebook from Step 1")
else:
    url = f"{rest_url}/bank/account"
    print(f"Checking Data API:")
    print(f"  URL: {url}")
    print(f"  Method: GET")
    print()
    try:
        with httpx.Client(timeout=10) as client_http:
            response = client_http.get(url, headers=headers, params={"limit": 1})
        if response.status_code == 200:
            print("SUCCESS: the Data API answers for bank.account")
            data_api_enabled = True
        elif response.status_code == 403:
            print("403: your Postgres role isn't set up for the Data API yet.")
            print("  Your role must be created with databricks_create_role() and granted to the")
            print("  Data API's 'authenticator' role. Ask your instructor. (The project owner's")
            print("  account can't be used with the Data API.)")
            print(f"  Response: {response.text[:200]}")
        elif response.status_code == 406:
            print("406: the bank schema isn't exposed. In your branch's Data API settings, add bank")
            print("  under Exposed schemas, then re-run this cell.")
        else:
            print(f"Unexpected response: {response.status_code}")
            print(f"Response: {response.text[:200]}")
    except Exception as e:
        print(f"Error: {e}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 4, Fetch all accounts via REST (if enabled)

# COMMAND ----------

if not data_api_enabled:
    print("Skipping: the Data API isn't ready on your branch (see Step 3).")
else:
    url = f"{rest_url}/bank/account"

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
    print("Skipping: the Data API isn't ready on your branch.")
else:
    url = f"{rest_url}/bank/account"
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
