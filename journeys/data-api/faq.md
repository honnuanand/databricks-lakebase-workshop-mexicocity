# Query via REST: the Data API, FAQ

## Common errors and fixes

### `Data API is NOT ENABLED on this instance`

The Data API must be enabled on your Lakebase instance. It's a checkbox in the console:

1. Log into Databricks.
2. Go to **Data Engineering** → **Lakebase** → **Instances**.
3. Click your instance.
4. Scroll to **Advanced** settings.
5. Toggle **Data API** to **ON**.
6. Wait 30 seconds.
7. Re-run the script.

Enabling is free and takes about 30 seconds.

### `401 Unauthorized`

Your OAuth token is invalid or expired. Tokens expire in 1 hour (3600 seconds). Get a fresh
token:

```bash
python data_api.py --step token
```

Then re-run the query.

### `403 Forbidden: row-level security policy violation`

You're trying to insert or modify a row that violates Row-Level Security policies. This is
expected if the table has RLS and you don't have write access to that row. Check what data you
have access to:

```bash
python data_api.py --step check-rls
```

### `404 Not Found`

The table or schema doesn't exist, or the Data API endpoint path is wrong. Check:

- Is the table name correct? (e.g., `factory.machine`, not `factory_machine`)
- Does the table exist in your branch? Run:
  ```bash
  python lakebase.py --sql "SELECT 1 FROM factory.machine LIMIT 1"
  ```
- Is the schema `factory`? If you use a different schema, update the script.

### `Request timeout` or `connection refused`

The Data API endpoint is not responding. Possible causes:

- Data API is not enabled (see first error above).
- The Lakebase instance is scaled to zero or shut down. Check the console.
- Network connectivity issue. Try pinging the Lakebase host.

### `Missing env var LB_PROFILE`

Set your environment variables (see [`../../00-setup/auth.md`](../../00-setup/auth.md)):

```bash
export LB_PROFILE=<your-profile>
export LB_PROJECT=<project-id>
export LB_SCHEMA=factory
```

## Concept clarifications

### Is the Data API the same as PostgREST?

The Lakebase Data API follows [PostgREST](../../docs/glossary.md) conventions (HTTP verbs map to SQL operations, JSON
responses), but it's not the PostgREST library itself. It's a Lakebase-native [REST](../../docs/glossary.md) layer. The
API is compatible with PostgREST clients and tools.

### Can I do complex queries with the Data API?

The Data API is designed for simple table queries (GET, INSERT, UPDATE, DELETE) and basic
filtering. Complex queries with joins, aggregations, or stored procedures are better done with
SQL via the SDK.

If you need complex queries, use SQL:

```python
from lakebase import connect
with connect() as conn:
    with conn.cursor() as cur:
        cur.execute("""
            SELECT product_id, COUNT(*) as part_count
            FROM factory.bom_edge
            GROUP BY product_id
        """)
```

The Data API is designed for user-facing apps that need simple, fast queries.

### Does the Data API support RLS?

Yes. [Row-Level Security](../../docs/glossary.md) policies are automatically enforced on Data API requests. The same user
permissions that apply to SQL queries apply to REST queries. If a user can't SELECT a row in
SQL, they can't GET it via [REST](../../docs/glossary.md).

### What's the latency overhead of REST vs SQL?

[REST](../../docs/glossary.md) adds HTTP transport overhead: usually 20-50 ms. For interactive apps, this is fine. For
analytics or bulk operations, SQL is faster. If you're serving a thousand queries per second, use
SQL; if you're serving a mobile app, REST is appropriate.

### Can I use the Data API from a browser (CORS)?

The Data API supports CORS (Cross-Origin Resource Sharing), so you can call it from JavaScript
in a browser. Example:

```javascript
const token = "ya29.a0AfH6SMB...";
const response = await fetch(
  "https://lb-instance.cloud.databricks.com/api/v1/factory.machine",
  {
    headers: { "Authorization": `Bearer ${token}` }
  }
);
const rows = await response.json();
```

Note: your token must be valid and have access to the table.

### Is OAuth the only auth method?

Currently, yes. The Data API uses Databricks [OAuth](../../docs/glossary.md) tokens (same as the Databricks CLI and
SDKs). There's no API key or PAT token support for the Data API.

### Can I cache results?

Yes. The Data API is read-optimized. If you're serving the same query to many users, cache the
results in your application or a CDN. Just remember to refresh the cache when the underlying
data changes.

## Tracing and debugging

### See the HTTP requests and responses

Run with verbose mode:

```bash
python data_api.py --verbose
```

This prints the full HTTP request (method, URL, headers) and response (status, body).

### Check RLS for a specific table

```bash
python data_api.py --check-rls factory.machine
```

This shows what rows you have access to in the table.

### Compare REST and SQL latency for your data

```bash
python data_api.py --step compare-sql --show-timing
```

This runs the same query via REST and SQL multiple times and shows average latency.

## Performance tips

### Use select to limit columns

Instead of:

```
GET /api/v1/factory.machine
```

Use:

```
GET /api/v1/factory.machine?select=machine_id,status
```

This reduces JSON payload and network overhead.

### Use filters to limit rows

Instead of fetching all rows and filtering in your app, filter at the API:

```
GET /api/v1/factory.machine?status=eq.healthy
```

This reduces the amount of data transferred.

### Paginate large result sets

If a query returns thousands of rows, paginate:

```
GET /api/v1/factory.machine?limit=100&offset=0
GET /api/v1/factory.machine?limit=100&offset=100
...
```

This keeps response sizes manageable and allows your app to show results incrementally.

### Batch writes

If you're inserting many rows, use bulk operations or batch inserts instead of individual POSTs.

## Related documentation

- PostgREST API documentation: https://postgrest.org/en/stable/
- Databricks Data API docs: (link to official Lakebase docs)
- OAuth token refresh: see [`../../00-setup/auth.md`](../../00-setup/auth.md)
