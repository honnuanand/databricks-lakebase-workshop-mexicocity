# Query Lakebase via REST: the Data API

> ## What you'll learn
>
> **Key takeaways**
>
> - The Lakebase Data API exposes your PostgreSQL database via [PostgREST](../../docs/glossary.md)-compatible [REST](../../docs/glossary.md) endpoints, so you can query it without a Postgres client or SDK.
> - Authentication is Databricks [OAuth](../../docs/glossary.md): pass a bearer token, and the API returns JSON. [Row-level security](../../docs/glossary.md) (RLS) applies to REST queries just like SQL queries; users only see data they have access to.
> - [REST](../../docs/glossary.md) queries are useful for mobile apps, JavaScript frontends, third-party integrations, and scenarios where you can't install a Postgres driver.
>
> **You'll be able to:** query your Lakebase data via HTTPS GET/POST using [OAuth](../../docs/glossary.md) tokens, parse the JSON results, and understand when [REST](../../docs/glossary.md) is the right approach.
>
> **Time:** about 20 minutes  ·  **Status:** live (conditional: requires Data API enabled on the instance)

## The scenario

Your bank runs a mobile app for supervisors to check account status and case notes. The app is iOS/Android; it can't easily use psycopg or the Lakebase SDK. You need an HTTP endpoint that returns JSON account data.

The Lakebase Data API provides exactly that: HTTP GET/POST endpoints that execute SQL and return
JSON, authenticated with Databricks [OAuth](../../docs/glossary.md). Your app sends a bearer token, requests
`GET /api/v1/bank.account?select=account_id,status`, and gets back JSON.

## What the Data API is

The Data API is a [REST](../../docs/glossary.md) layer on top of PostgreSQL. It follows the [PostgREST](../../docs/glossary.md) convention: HTTP
verbs (GET, POST, PATCH, DELETE) map to SQL operations (SELECT, INSERT, UPDATE, DELETE), and
responses are JSON. Authentication is Databricks [OAuth](../../docs/glossary.md) bearer tokens, and [Row-Level Security](../../docs/glossary.md)
applies.

### API shape

The base URL is the Lakebase instance host with `/api/v1/` prefix. Endpoints follow this pattern:

```
GET /api/v1/{schema}.{table}
POST /api/v1/{schema}.{table}
PATCH /api/v1/{schema}.{table}
DELETE /api/v1/{schema}.{table}
```

Query parameters control filtering, ordering, and pagination:

```
GET /api/v1/bank.account?select=account_id,status&status=eq.good_standing
```

### Authentication

Pass a Databricks [OAuth](../../docs/glossary.md) token as a bearer token:

```
Authorization: Bearer <oauth_token>
```

The token is valid for 1 hour (3600 seconds). The API enforces the same user permissions and
[Row-Level Security](../../docs/glossary.md) policies as SQL queries.

### Response format

Responses are JSON arrays or objects. A GET query returns an array of rows:

```json
[
  {"account_id": "ACCT-100234", "status": "good_standing", "health_pct": 98.5},
  {"account_id": "ACCT-100241", "status": "derated", "health_pct": 70.0}
]
```

Errors return HTTP 4xx or 5xx with an error message:

```json
{"code": "PGRST103", "message": "The endpoint does not support GET"}
```

## The wow moment

You write a mobile app HTTP client in five lines of Swift or JavaScript, point it at the Data
API, and your app can query live manufacturing data. No Postgres driver, no SDK setup, just
HTTPS and JSON. The data is current and respects row-level security.

## What you'll do

1. Enable the Data API on your Lakebase instance (if not already enabled).
2. Get a Databricks OAuth token.
3. Make a simple GET request to fetch accounts and parse the JSON.
4. Try a filtered query with parameters.
5. Compare REST to SQL to understand the trade-offs.

Full copy-paste steps are in [`instructions.md`](instructions.md); expected output is in
[`expected.md`](expected.md).

## Prerequisites

Finish [`../../00-setup/`](../../00-setup/) so you have a branch and can connect. You'll need
`LB_PROFILE` and `LB_PROJECT` set to get OAuth tokens.

The Data API must be enabled on your Lakebase instance. If it's not, you'll see a clear error
and instructions to enable it. Enabling is a one-click checkbox in the Lakebase console (requires
instance owner/admin access).

## Status: conditional

The Data API is **live** (GA) when enabled on an instance. However, not all instances have it
enabled by default. If your instance doesn't have it, you can enable it in the console; the
journey will gracefully skip if it's not available. The journey script checks for availability
and either runs full tests or shows a "not enabled" explainer.

## Wrapping up

The Data API is the REST layer on Lakebase: same data, same security, different transport. For
web and mobile clients, REST is often the right choice. For servers and analytics, SQL and the
SDK are faster and more flexible. In the next journey, [Capstone app](../capstone-app/), you'll
build a full React+FastAPI app on Databricks Apps that uses both the Data API and direct SQL to
serve manufacturing dashboards.
