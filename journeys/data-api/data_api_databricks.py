# Databricks notebook source
# MAGIC %md-sandbox
# MAGIC <div style="display:flex; align-items:center; gap:10px; padding:8px 16px; background:#F9F7F4; border-bottom:2px solid #E0E0E0; font-family:sans-serif; line-height:1;">
# MAGIC   <span style="display:inline-block; width:12px; height:12px; border-radius:2px; background:#FF3621;"></span>
# MAGIC   <span style="font-weight:bold; color:#0b2026;">Lakebase workshop</span>
# MAGIC   <span style="color:#999;">|</span>
# MAGIC   <span style="color:#5A6F77;">Part 2 · App developers · Journey 5 of 6 · Lakebase Data API</span>
# MAGIC </div>

# COMMAND ----------

# MAGIC %md
# MAGIC # Lakebase Data API
# MAGIC #### Duration: 20 minutes
# MAGIC
# MAGIC *Journey 5 of 6 in the App developers track. So far every query went through a Postgres connection; this journey reads the same tables over HTTPS.*
# MAGIC
# MAGIC ## Overview
# MAGIC
# MAGIC A mobile banking team wants account data in its app, but a phone shouldn't hold a database connection
# MAGIC or a Postgres driver. It speaks HTTPS and JSON.
# MAGIC
# MAGIC The **Lakebase Data API** exposes your tables as a REST API: `GET <url>/bank/account` returns rows as
# MAGIC JSON, with filters and column selection as URL parameters, authenticated with a Databricks OAuth
# MAGIC token. In this lab you find your branch's Data API, get a token, and call it. **Not yet tested end to
# MAGIC end:** the REST calls follow the Databricks documentation, but the account that built the workshop owns
# MAGIC the project, and the project owner can't call the Data API; the setup checks were run.
# MAGIC
# MAGIC ## Learning objectives
# MAGIC
# MAGIC By the end of this lab, you will be able to:
# MAGIC
# MAGIC 1. **Find your branch's Data API URL** and what has to be set up for it.
# MAGIC 2. **Authenticate with an OAuth token** in the `Authorization` header.
# MAGIC 3. **Read and filter rows over HTTPS** with REST query parameters.
# MAGIC 4. **Compare the REST call with the SQL** it replaces, and know when each fits.

# COMMAND ----------

# MAGIC %md
# MAGIC ## Key concepts
# MAGIC
# MAGIC - **REST API:** an HTTPS interface: you `GET` a URL and receive JSON. Any language or device that speaks HTTPS can use it, with no database driver.
# MAGIC - **Data API:** Lakebase's REST interface to your tables (PostgREST-compatible). It's enabled per branch, and only exposes the schemas you choose.
# MAGIC - **OAuth token (JWT):** a short-lived signed token that proves who you are. The Data API needs one in the `Authorization: Bearer` header.
# MAGIC - **`authenticator` role:** the Postgres role the Data API connects as. It switches to your role for each request, so your role must be set up for it (an instructor step).
# MAGIC
# MAGIC More terms are defined in `docs/glossary.md` in the workshop folder.

# COMMAND ----------

# MAGIC %md-sandbox
# MAGIC ## A. Setup
# MAGIC
# MAGIC <div style="border-left:4px solid #1B5162; background:#EEF4F6; padding:12px 16px; border-radius:4px; margin:12px 0; font-family:sans-serif;">
# MAGIC   <strong style="display:block; color:#1B5162; margin-bottom:6px;">Before you start</strong>
# MAGIC   <div style="color:#333;">
# MAGIC     Run <code>00-setup/setup_databricks</code> once to create your branch and load the bank.
# MAGIC     Attach this notebook to <strong>serverless</strong> compute.
# MAGIC     Needs: the <strong>Data API enabled on your branch</strong> with the <code>bank</code> schema exposed, and your Postgres role set up for it by your instructor (C1 explains). Without it, the REST steps skip themselves.
# MAGIC   </div>
# MAGIC </div>

# COMMAND ----------

# MAGIC %md
# MAGIC ### A1. Install the driver and pick your branch
# MAGIC
# MAGIC Run the next three cells before anything else. They install the Postgres driver, upgrade the
# MAGIC Databricks SDK if your environment's version predates the Lakebase API, and set `LB_PROJECT`,
# MAGIC `LB_BRANCH`, and `LB_SCHEMA` from the widgets at the top of this notebook. `LB_BRANCH` defaults to
# MAGIC the branch `00-setup/setup_databricks` created for you. Change a widget only if you used a
# MAGIC different project or branch name.

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

# MAGIC %md-sandbox
# MAGIC **Expected result:** `signed in as` your email, followed by your project, branch, and schema:
# MAGIC
# MAGIC ```
# MAGIC signed in as alex.kim@example.com
# MAGIC   LB_PROJECT = bank
# MAGIC   LB_BRANCH = u-alex-kim
# MAGIC   LB_SCHEMA = bank
# MAGIC ```
# MAGIC
# MAGIC <div style="border-left:4px solid #FF9800; background:#FFF3E0; padding:12px 16px; border-radius:4px; margin:12px 0; font-family:sans-serif;">
# MAGIC   <strong style="display:block; color:#E65100; margin-bottom:6px;">Troubleshooting</strong>
# MAGIC   <div style="color:#333;">
# MAGIC     <ul style="margin:0; padding-left:20px;">
# MAGIC       <li><code>databricks-sdk ... predates the Lakebase API</code>: rerun the install cell and the restart cell, then this one.</li>
# MAGIC       <li><code>Fill in LB_BRANCH in the widgets at the top of the notebook</code>: type your branch name in the <code>LB_BRANCH</code> box, then rerun this cell.</li>
# MAGIC       <li>The widgets show an old branch name: run <code>dbutils.widgets.removeAll()</code> in a new cell, then rerun this one.</li>
# MAGIC     </ul>
# MAGIC   </div>
# MAGIC </div>

# COMMAND ----------

# MAGIC %md
# MAGIC ### A2. Load the HTTP client
# MAGIC
# MAGIC This cell loads `httpx` if it's installed, or a small stand-in built on `requests`, plus the workshop
# MAGIC helpers.

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
# MAGIC **Expected result:** `HTTP client ready (httpx or requests shim).`

# COMMAND ----------

# MAGIC %md
# MAGIC ## B. Connect

# COMMAND ----------

# MAGIC %md
# MAGIC ### B1. Find your branch's Data API URL
# MAGIC
# MAGIC The Data API is enabled per branch. Its base URL comes from the branch's Data API settings, and
# MAGIC requests go to `<url>/<schema>/<table>`, for example `<url>/bank/account`.

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

# MAGIC %md-sandbox
# MAGIC **Expected result:** your project and branch, the endpoint host, and the Data API URL, or `(the Data API is not
# MAGIC enabled on this branch)`:
# MAGIC
# MAGIC ```
# MAGIC Connection info:
# MAGIC   Project: bank
# MAGIC   Branch: u-alex-kim
# MAGIC   Host: ep-....database.us-east-2.cloud.databricks.com
# MAGIC   Data API URL: https://ep-....database.us-east-2.cloud.databricks.com/api/2.0/workspace/<workspace id>/rest/databricks_postgres
# MAGIC ```
# MAGIC
# MAGIC **What this proves:** the REST endpoint belongs to your branch: it sits on the same host you've been connecting to with SQL.
# MAGIC
# MAGIC <div style="border-left:4px solid #FF9800; background:#FFF3E0; padding:12px 16px; border-radius:4px; margin:12px 0; font-family:sans-serif;">
# MAGIC   <strong style="display:block; color:#E65100; margin-bottom:6px;">Troubleshooting</strong>
# MAGIC   <div style="color:#333;">
# MAGIC     <ul style="margin:0; padding-left:20px;">
# MAGIC       <li><code>Missing required env var LB_PROJECT</code> or <code>KeyError: 'LB_PROJECT'</code>: the A1 cells didn't run in this session. Run the three A1 cells, then this one.</li>
# MAGIC     </ul>
# MAGIC   </div>
# MAGIC </div>

# COMMAND ----------

# MAGIC %md
# MAGIC ### B2. Get an OAuth token
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
# MAGIC **Expected result:** `OAuth token acquired.` and the first characters of the token.

# COMMAND ----------

# MAGIC %md
# MAGIC ## C. Call the API

# COMMAND ----------

# MAGIC %md
# MAGIC ### C1. Check that the Data API answers
# MAGIC
# MAGIC A `GET` for one account. The answer tells you what, if anything, is missing:
# MAGIC
# MAGIC - **200:** ready.
# MAGIC - **Not enabled:** enable it on your branch (the cell prints how) and add `bank` under **Exposed schemas**.
# MAGIC - **406:** the `bank` schema isn't exposed.
# MAGIC - **403 `permission denied to set role`:** your Postgres role isn't set up for the Data API; your
# MAGIC   instructor creates it with `databricks_create_role()` and grants it to `authenticator`.

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
    print("  4. Re-run this notebook from B1")
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

# MAGIC %md-sandbox
# MAGIC **Expected result:** `SUCCESS: the Data API answers for bank.account` once everything is set up. In the workshop's
# MAGIC own test run, as the project owner, it stopped here, as expected:
# MAGIC
# MAGIC ```
# MAGIC 403: your Postgres role isn't set up for the Data API yet.
# MAGIC   Your role must be created with databricks_create_role() and granted to the
# MAGIC   Data API's 'authenticator' role. Ask your instructor. (The project owner's
# MAGIC   account can't be used with the Data API.)
# MAGIC ```
# MAGIC
# MAGIC <div style="border-left:4px solid #1B5162; background:#EEF4F6; padding:12px 16px; border-radius:4px; margin:12px 0; font-family:sans-serif;">
# MAGIC   <strong style="display:block; color:#1B5162; margin-bottom:6px;">See it in the UI (optional)</strong>
# MAGIC   <div style="color:#333;">
# MAGIC     Open the <strong>Lakebase Postgres</strong> app, then your project and your branch, and choose <strong>Data API</strong>: it shows whether the API is enabled, its URL, and the exposed schemas.
# MAGIC   </div>
# MAGIC </div>

# COMMAND ----------

# MAGIC %md
# MAGIC ### C2. Read all accounts over HTTPS
# MAGIC
# MAGIC ```
# MAGIC GET <url>/bank/account
# MAGIC ```

# COMMAND ----------

if not data_api_enabled:
    print("Skipping: the Data API isn't ready on your branch (see C1).")
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
# MAGIC **Expected result:** `Result: 8 accounts`, then the first one as JSON. (Not yet run successfully in the workshop's
# MAGIC workspace; see the note at the top.) If C1 didn't succeed, the cell prints `Skipping`.

# COMMAND ----------

# MAGIC %md
# MAGIC ### C3. Filter and pick columns
# MAGIC
# MAGIC REST query parameters do the work of `WHERE` and `SELECT`: `status=eq.good_standing` filters, and
# MAGIC `select=account_id,status` picks the columns.
# MAGIC
# MAGIC ```
# MAGIC GET <url>/bank/account?select=account_id,status&status=eq.good_standing
# MAGIC ```

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
# MAGIC **Expected result:** `Result: 5 good_standing accounts` and three of them, such as `{'account_id': 'CTA-100234', 'status': 'good_standing'}`
# MAGIC (not yet run successfully; see the note at the top). If C1 didn't succeed, the cell prints `Skipping`.

# COMMAND ----------

# MAGIC %md
# MAGIC ## D. REST and SQL

# COMMAND ----------

# MAGIC %md
# MAGIC ### D1. The same question in SQL
# MAGIC
# MAGIC ```sql
# MAGIC SELECT account_id, status FROM bank.account WHERE status = 'good_standing';
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
# MAGIC **Expected result:** when the Data API is ready, `SQL result: 5 rows` and the same accounts as C3. Otherwise
# MAGIC `Skipping: Data API is not enabled.`
# MAGIC
# MAGIC **What this proves:** the REST call and the SQL read the same rows; the Data API is another door into the same tables.

# COMMAND ----------

# MAGIC %md-sandbox
# MAGIC ##### EXPAND FOR ADDITIONAL NOTES
# MAGIC
# MAGIC <details>
# MAGIC <summary><strong>REST or SQL?</strong></summary>
# MAGIC
# MAGIC Use the Data API for clients that can't, or shouldn't, hold a database connection: browsers, mobile apps,
# MAGIC partner integrations. It respects the same Postgres roles and row-level security as SQL. Use SQL for
# MAGIC joins, bulk work, and anything performance-critical, where one query beats many HTTP calls.
# MAGIC
# MAGIC </details>

# COMMAND ----------

# MAGIC %md-sandbox
# MAGIC ##### Check your understanding
# MAGIC
# MAGIC <details>
# MAGIC <summary><strong>1. What URL returns the `bank.account` table?</strong></summary>
# MAGIC
# MAGIC `<your branch's Data API URL>/bank/account`.
# MAGIC
# MAGIC </details>
# MAGIC
# MAGIC <details>
# MAGIC <summary><strong>2. Why can't the project owner's account call the Data API?</strong></summary>
# MAGIC
# MAGIC The Data API connects as `authenticator` and switches to the caller's role; the owner's role can't be granted to `authenticator`.
# MAGIC
# MAGIC </details>
# MAGIC
# MAGIC <details>
# MAGIC <summary><strong>3. What do `status=eq.good_standing` and `select=account_id,status` correspond to in SQL?</strong></summary>
# MAGIC
# MAGIC `WHERE status = 'good_standing'` and `SELECT account_id, status`.
# MAGIC
# MAGIC </details>

# COMMAND ----------

# MAGIC %md
# MAGIC ## E. Conclusion
# MAGIC
# MAGIC In this lab you found your branch's Data API, got a token, and called it. Key takeaways:
# MAGIC
# MAGIC 1. **The Data API turns tables into REST endpoints,** `<url>/<schema>/<table>`, returning JSON.
# MAGIC 2. **It's enabled per branch** and exposes only the schemas you choose.
# MAGIC 3. **Every call carries an OAuth token,** and the API acts as the caller's Postgres role, so the usual
# MAGIC    permissions and row-level security apply.
# MAGIC 4. **REST suits clients without a database driver;** SQL stays best for heavy queries.
# MAGIC
# MAGIC The last journey in this track puts a full web app on the same bank.

# COMMAND ----------

# MAGIC %md
# MAGIC ---
# MAGIC **Next in the App developers track:** <a href="$../capstone-app/capstone_app_databricks">Building a Databricks App on Lakebase →</a>
# MAGIC
# MAGIC <a href="$../../START_HERE">← Back to the table of contents</a>
