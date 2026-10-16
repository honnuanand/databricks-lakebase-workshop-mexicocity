# Query via REST: the Data API, expected results

Use this to check your run. The exact account data depends on your bank seed, but the API
shape and response format should match.

## Step 1, check if Data API is enabled

Running `python data_api.py --step check` shows:

```text
Data API check:
  Data API URL: https://<endpoint-host>/api/2.0/workspace/<workspace-id>/rest/databricks_postgres
  Endpoint: <url>/bank/account
  Status: Data API is ENABLED
```

If the Data API is not enabled, you'll see:

```text
  Data API URL: (not enabled on this branch)
  Status: Data API not enabled on this branch

To enable: Lakebase Postgres app -> your project -> your branch -> Data API -> Enable Data API, then add `bank` under Exposed schemas
```

As the project owner (as in the workshop's own test runs), the check stops with:

```text
  Status: 403: your Postgres role isn't granted to the Data API's `authenticator` role (instructor setup; the project owner can't be used)
```

## Step 2, get an OAuth token

Running `python data_api.py --step token` shows:

```text
OAuth token acquired:
  Token: ya29.a0AfH6SMBxabc...xyz (first 20 chars)
  Expires in: 3600 seconds (1 hour)
```

The full token is long and sensitive; the script only shows the first 20 characters for safety.

## Step 3, simple GET request

Running `python data_api.py --step get-accounts` shows:

```json
[
  {"account_id": "CTA-100240", "branch_id": "BR-CDMX", "line": "Checking", "type": "retail", "status": "good_standing", "health_pct": 91.0},
  {"account_id": "CTA-100241", "branch_id": "BR-CDMX", "line": "Credit", "type": "retail", "status": "watch", "health_pct": 70.0},
  {"account_id": "CTA-200311", "branch_id": "BR-MTY", "line": "Credit", "type": "retail", "status": "frozen", "health_pct": 45.0},
  ...
]
```

(Number of rows depends on your bank seed.)

## Step 4, filtered query

Running `python data_api.py --step get-filtered` shows:

```json
[
  {"account_id": "CTA-100234", "status": "good_standing"},
  {"account_id": "CTA-100234", "status": "good_standing"},
  {"account_id": "CTA-100235", "status": "good_standing"}
]
```

Only accounts with `status='good_standing'` are returned. The `select=account_id,status` parameter
limits the columns.

## Step 5, REST vs SQL comparison

Running `python data_api.py --step compare-sql` shows:

```text
Same query, two ways:

REST:
  GET <url>/bank/account?select=account_id,status&status=eq.good_standing
  Latency: ~45 ms

SQL:
  SELECT account_id, status FROM bank.account WHERE status = 'good_standing'
  Latency: ~15 ms

Same result:
  [("CTA-100234", "good_standing"), ("CTA-100235", "good_standing"), ...]
```

REST is slower due to HTTP overhead, but the difference is usually negligible for user-facing
queries. SQL is preferred for analytics.

## Step 6, POST request (if write-enabled)

Running `python data_api.py --step post-read-only` shows:

```text
POST request (insert):
  POST <url>/bank/account
  Body: {"account_id": "CTA-999999", "branch_id": "BR-TEST", ...}

Result:
  201 Created
  {"account_id": "CTA-999999", "branch_id": "BR-TEST", ...}
```

If your RLS or permissions prevent writes, you'll see:

```text
403 Forbidden
{"code": "PGRST103", "message": "new row violates row-level security policy"}
```

This is expected if you don't have write access to the account table in your branch.

## Full run output

Running the script end to end (if Data API is enabled):

```text
Lakebase Data API Test
======================

Step 1: Check if Data API is enabled
  Status: ENABLED

Step 2: Get OAuth token
  Token: ya29.a0AfH6SMB...

Step 3: Fetch all accounts
  Result: 8 rows returned

Step 4: Filter query (status=good_standing)
  Result: 5 rows returned

Step 5: Compare REST vs SQL
  REST latency: 45 ms
  SQL latency: 15 ms
  Results match: ✓

Step 6: POST test (insert)
  Result: 403 Forbidden (expected if read-only)

All tests passed (or gracefully skipped).
```

## The numbers that matter

| Aspect | Expected | Why it matters |
| ------ | -------- | -------------- |
| GET latency | 30-100 ms | HTTP + network overhead; still fast for most apps |
| Token validity | 3600 seconds (1 hr) | tokens expire; your app needs to refresh |
| Maximum response size | varies | depends on your Lakebase instance size; typically 100K-1M rows per request |
| RLS enforcement | automatic | users only see rows they have access to, same as SQL |
| Pagination | via offset/limit | REST API supports pagination for large result sets |

> **Note**
> Latencies are measured on a local network with a warm Lakebase instance. Your latencies may
> vary based on network distance, instance load, and query complexity.
