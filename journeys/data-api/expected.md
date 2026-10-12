# Query via REST: the Data API, expected results

Use this to check your run. The exact machine data depends on your factory seed, but the API
shape and response format should match.

## Step 1, check if Data API is enabled

Running `python data_api.py --step check` shows:

```text
Data API check:
  Host: https://lb-workshop-instance.cloud.databricks.com
  Endpoint: /api/v1/bank.account
  Status: Data API is ENABLED
```

If the Data API is not enabled, you'll see:

```text
Status: Data API is NOT ENABLED on this instance
To enable: go to Databricks console → Lakebase → Instances → select your instance →
Advanced settings → toggle "Data API" to ON, then wait 30 seconds and retry.
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

Running `python data_api.py --step get-machines` shows:

```json
[
  {"account_id": "ACCT-100240", "branch_id": "BR-NYC", "line": "Stamping-A", "type": "press", "status": "healthy", "health_pct": 91.0},
  {"account_id": "ACCT-100241", "branch_id": "BR-NYC", "line": "Stamping-A", "type": "press", "status": "derated", "health_pct": 70.0},
  {"account_id": "M-301", "branch_id": "PL-CHICAGO", "line": "Assembly-B", "type": "robot", "status": "down", "health_pct": 45.0},
  ...
]
```

(Number of rows depends on your factory seed.)

## Step 4, filtered query

Running `python data_api.py --step get-filtered` shows:

```json
[
  {"account_id": "ACCT-100240", "status": "healthy"},
  {"account_id": "M-201", "status": "healthy"},
  {"account_id": "M-202", "status": "healthy"}
]
```

Only machines with `status='healthy'` are returned. The `select=account_id,status` parameter
limits the columns.

## Step 5, REST vs SQL comparison

Running `python data_api.py --step compare-sql` shows:

```text
Same query, two ways:

REST:
  GET /api/v1/bank.account?select=account_id,status&status=eq.healthy
  Latency: ~45 ms

SQL:
  SELECT account_id, status FROM bank.account WHERE status = 'healthy'
  Latency: ~15 ms

Same result (12 rows):
  [("ACCT-100240", "healthy"), ("M-201", "healthy"), ...]
```

REST is slower due to HTTP overhead, but the difference is usually negligible for user-facing
queries. SQL is preferred for analytics.

## Step 6, POST request (if write-enabled)

Running `python data_api.py --step post-read-only` shows:

```text
POST request (insert):
  POST /api/v1/bank.account
  Body: {"account_id": "M-999", "branch_id": "PL-TEST", ...}

Result:
  201 Created
  {"account_id": "M-999", "branch_id": "PL-TEST", ...}
```

If your RLS or permissions prevent writes, you'll see:

```text
403 Forbidden
{"code": "PGRST103", "message": "new row violates row-level security policy"}
```

This is expected if you don't have write access to the machine table in your branch.

## Full run output

Running the script end to end (if Data API is enabled):

```text
Lakebase Data API Test
======================

Step 1: Check if Data API is enabled
  Status: ENABLED

Step 2: Get OAuth token
  Token: ya29.a0AfH6SMB...

Step 3: Fetch all machines
  Result: 45 rows returned

Step 4: Filter query (status=healthy)
  Result: 12 rows returned

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
