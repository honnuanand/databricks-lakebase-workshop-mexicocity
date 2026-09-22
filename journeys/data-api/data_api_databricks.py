# Databricks notebook source
# MAGIC %md
# MAGIC # Query via REST: the Data API, step by step
# MAGIC
# MAGIC A hands-on lab. Run one cell at a time, read what happened, then move on. You will make HTTP requests to the Lakebase Data API using Databricks OAuth tokens. If the Data API is enabled on your instance, you will fetch and filter data as JSON. If it is not enabled, the notebook shows you how to enable it.
# MAGIC
# MAGIC **Before you start:** finish `00-setup/` so `LB_PROFILE`, `LB_PROJECT`, `LB_BRANCH` are set.

# COMMAND ----------

# MAGIC %md
# MAGIC ## Setup — install httpx and get your connection info

# COMMAND ----------

import os, sys
sys.path.insert(0, os.path.join(os.getcwd(), "..", "..", "common", "scripts"))

try:
    import httpx
except ImportError:
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "httpx"])
    import httpx

from lakebase import client, branch_endpoint, _env

print("httpx ready.")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 1 — Get connection info and OAuth token

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
# MAGIC ## Step 2 — Get an OAuth token from Databricks

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
# MAGIC ## Step 3 — Check if the Data API is enabled on your instance

# COMMAND ----------

url = f"https://{host}/api/v1/factory.machine"
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
# MAGIC ## Step 4 — Fetch all machines via REST (if enabled)

# COMMAND ----------

if not data_api_enabled:
    print("Skipping: Data API is not enabled. Enable it first (see Step 3).")
else:
    url = f"https://{host}/api/v1/factory.machine"
    headers = {"Authorization": f"Bearer {token}"}

    print(f"Fetching all machines:")
    print(f"  URL: {url}")
    print()

    try:
        with httpx.Client(timeout=10) as client_http:
            response = client_http.get(url, headers=headers)
            response.raise_for_status()
            machines = response.json()
            print(f"Result: {len(machines)} machines")
            if machines:
                print(f"\nFirst machine:")
                print(f"  {machines[0]}")
    except Exception as e:
        print(f"Error: {e}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 5 — Filter with query parameters

# COMMAND ----------

if not data_api_enabled:
    print("Skipping: Data API is not enabled.")
else:
    url = f"https://{host}/api/v1/factory.machine"
    headers = {"Authorization": f"Bearer {token}"}
    params = {"select": "machine_id,status", "status": "eq.healthy"}

    print(f"Fetching only healthy machines:")
    print(f"  URL: {url}")
    print(f"  Params: {params}")
    print()

    try:
        with httpx.Client(timeout=10) as client_http:
            response = client_http.get(url, headers=headers, params=params)
            response.raise_for_status()
            machines = response.json()
            print(f"Result: {len(machines)} healthy machines")
            print(f"\nSample machines:")
            for machine in machines[:3]:
                print(f"  {machine}")
    except Exception as e:
        print(f"Error: {e}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 6 — Compare REST to SQL
# MAGIC
# MAGIC The same query in SQL:
# MAGIC
# MAGIC ```sql
# MAGIC SELECT machine_id, status FROM factory.machine WHERE status = 'healthy'
# MAGIC ```

# COMMAND ----------

from lakebase import connect

if not data_api_enabled:
    print("Skipping: Data API is not enabled.")
else:
    print("SQL equivalent:")
    print("  SELECT machine_id, status FROM factory.machine WHERE status = 'healthy'")
    print()

    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT machine_id, status FROM factory.machine WHERE status = 'healthy'")
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
