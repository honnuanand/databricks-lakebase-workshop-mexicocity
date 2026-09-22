# Query via REST: the Data API, instructions

If you haven't done [`../../00-setup/`](../../00-setup/), do that first; you need `LB_PROFILE` and
`LB_PROJECT` set to get OAuth tokens.

Everything here is in a single script: [`./data_api.py`](./data_api.py).
This script checks if the Data API is enabled on your instance and either runs full tests or
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

Fetch all machines:

```bash
python data_api.py --step get-machines
```

The script makes an HTTP GET request:

```
GET https://<lakebase-host>/api/v1/factory.machine
Authorization: Bearer <token>
```

And prints the JSON response:

```json
[
  {"machine_id": "M-204", "status": "healthy", "health_pct": 91.0},
  {"machine_id": "M-205", "status": "derated", "health_pct": 70.0},
  ...
]
```

### Step 4, filter with query parameters

Fetch only healthy machines:

```bash
python data_api.py --step get-filtered
```

The script makes a GET request with filters:

```
GET https://<lakebase-host>/api/v1/factory.machine?select=machine_id,status&status=eq.healthy
Authorization: Bearer <token>
```

This returns only rows where `status='healthy'`.

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

1. Log into your Databricks workspace.
2. Go to **Data Engineering** → **Lakebase** → **Instances**.
3. Click on your instance.
4. In the **Advanced** settings, toggle **Data API** to **Enabled**.
5. Wait a few seconds for the API to become available.
6. Re-run the script.

Enabling takes about 30 seconds.
