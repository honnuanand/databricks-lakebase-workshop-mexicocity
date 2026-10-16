# Query via REST: the Data API, instructions

## How to run this journey

There are a few ways to work through the steps. Pick one:

- **Notebook, step by step (recommended for learning):** open [`data_api.ipynb`](data_api.ipynb) and run one cell at a time. Reading each result before the next step is where the learning happens.
- **In a Databricks workspace:** import [`data_api_databricks.py`](data_api_databricks.py) and run it cell by cell there.
- **By hand:** follow the numbered steps below, copying each command yourself.
- **Just see it work:** run `python data_api.py` from this folder to execute the whole thing at once. Fast, but you learn the most from the notebook.

If you haven't done [`../../00-setup/`](../../00-setup/), do that first; you need `LB_PROFILE` and
`LB_PROJECT` set to get OAuth tokens.

Everything here is in a single script: [`./data_api.py`](./data_api.py).
This script checks if the Data API is enabled on your branch and either runs full tests or
shows you how to enable it.

## Run it end to end

```bash
cd journeys/data-api
python data_api.py
```

The script checks if the Data API is enabled. If it is, it makes HTTP requests and shows you
results. If it's not enabled, it provides instructions. Read on for what each step does; expected
output is in [`expected.md`](expected.md).

## Or step through it by hand

### Step 1, check if the Data API is enabled

```bash
python data_api.py --step check
```

The script tries to reach the Data API endpoint. If it's enabled, you'll see a success message. If
not, you'll see instructions to enable it (a one-click checkbox in the Lakebase console, requires
admin access).

### Step 2, get an OAuth token

You can't make Data API requests without a Databricks [OAuth](../../docs/glossary.md) token. The script gets one for you:

```bash
python data_api.py --step token
```

This runs:

```bash
databricks auth token --profile <LB_PROFILE> --output json
```

And extracts the `access_token` field. Tokens expire in 1 hour (3600 seconds).

### Step 3, make a simple GET request

Fetch all accounts:

```bash
python data_api.py --step get-accounts
```

The script makes an HTTP GET request:

```
GET <url>/bank/account
Authorization: Bearer <token>
```

And prints the JSON response:

```json
[
  {"account_id": "CTA-100234", "status": "good_standing", "health_pct": 98.5},
  {"account_id": "CTA-100241", "status": "derated", "health_pct": 70.0},
  ...
]
```

### Step 4, filter with query parameters

Fetch only good_standing accounts:

```bash
python data_api.py --step get-filtered
```

The script makes a GET request with filters:

```
GET <url>/bank/account?select=account_id,status&status=eq.good_standing
Authorization: Bearer <token>
```

This returns only rows where `status='good_standing'`.

### Step 5, compare REST to SQL

```bash
python data_api.py --step compare-sql
```

The script shows the same query in SQL and compares performance. The REST query and the SQL
query return the same data, but with different latency and transport overhead.

### Step 6, create data via REST (POST)

Try inserting a new row (if you have write permissions):

```bash
python data_api.py --step post-read-only
```

The script attempts to insert a row and shows the result (or an RLS/permission error if the
Data API has restrictions).

## What you just did

You connected to your Lakebase data via REST, using OAuth authentication, and queried it as JSON.
This is the bridge between your PostgreSQL database and web/mobile clients that speak HTTP and
JSON. Compare your output to [`expected.md`](expected.md); if anything went wrong, check
[`faq.md`](faq.md).

## Enabling the Data API (if not already enabled)

If the script says the Data API is not enabled:

1. Open the **Lakebase Postgres** app, then your project and your branch.
2. Open **Data API** and choose **Enable Data API**.
3. Under **Exposed schemas**, add `bank` (only `public` is exposed by default).
4. Re-run the notebook or script.

Each caller also needs a Postgres role that the Data API can switch to. Your instructor sets this up
once, on `production`, so attendee branches inherit it:

```sql
CREATE EXTENSION IF NOT EXISTS databricks_auth;
SELECT databricks_create_role('attendee@example.com', 'USER');
GRANT "attendee@example.com" TO authenticator;
GRANT USAGE ON SCHEMA bank TO "attendee@example.com";
GRANT SELECT ON ALL TABLES IN SCHEMA bank TO "attendee@example.com";
```

The project owner's own account can't be used with the Data API: its role can't be granted to
`authenticator`, and calls fail with `permission denied to set role`.
