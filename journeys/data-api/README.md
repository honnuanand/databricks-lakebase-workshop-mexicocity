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
> **Time:** about 20 minutes  ·  **Status:** conditional (needs the Data API enabled on your branch; REST calls not yet tested end to end)

## The scenario

Your bank runs a mobile app for supervisors to check account status and case notes. The app is iOS/Android; it can't easily use psycopg or the Lakebase SDK. You need an HTTP endpoint that returns JSON account data.

The Lakebase Data API provides exactly that: HTTP GET/POST endpoints that execute SQL and return
JSON, authenticated with Databricks [OAuth](../../docs/glossary.md). Your app sends a bearer token, requests
`GET <url>/bank/account?select=account_id,status`, and gets back JSON.

## What the Data API is

The Data API is a [REST](../../docs/glossary.md) layer on top of PostgreSQL. It follows the [PostgREST](../../docs/glossary.md) convention: HTTP
verbs (GET, POST, PATCH, DELETE) map to SQL operations (SELECT, INSERT, UPDATE, DELETE), and
responses are JSON. Authentication is Databricks [OAuth](../../docs/glossary.md) bearer tokens, and [Row-Level Security](../../docs/glossary.md)
applies.

### API shape

The base URL is shown in your branch's Data API settings (and returned by
`w.postgres.get_data_api(...).status.url`). It looks like
`https://<endpoint-host>/api/2.0/workspace/<workspace-id>/rest/databricks_postgres`. Endpoints add the
schema and table:

```
GET    <url>/{schema}/{table}
POST   <url>/{schema}/{table}
PATCH  <url>/{schema}/{table}
DELETE <url>/{schema}/{table}
```

Query parameters control filtering, ordering, and pagination:

```
GET <url>/bank/account?select=account_id,status&status=eq.good_standing
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
  {"account_id": "CTA-100234", "status": "good_standing", "health_pct": 98.5},
  {"account_id": "CTA-100241", "status": "derated", "health_pct": 70.0}
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

1. Check that the Data API is enabled on your branch, with the `bank` schema exposed.
2. Get a Databricks OAuth token.
3. Make a simple GET request to fetch accounts and parse the JSON.
4. Try a filtered query with parameters.
5. Compare REST to SQL to understand the trade-offs.

Full copy-paste steps are in [`instructions.md`](instructions.md); expected output is in
[`expected.md`](expected.md).

## Prerequisites

Finish [`../../00-setup/`](../../00-setup/) so you have a branch and can connect. In a Databricks
notebook nothing else is needed; the script on a laptop also needs `LB_PROFILE`.

The Data API must be enabled on your branch, with `bank` exposed, and your Postgres role set up for
it. If it isn't, the notebook says which part is missing:

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

## Status: conditional

The Data API is enabled per branch and isn't on by default. If it isn't ready on your branch, the
journey skips the REST calls and says why. The REST calls follow the Databricks documentation but
haven't been run successfully in the workshop's workspace yet: the account that built the workshop
owns the project, and the project owner can't call the Data API. The journey script checks for availability
and either runs full tests or shows a "not enabled" explainer.

## Wrapping up

The Data API is the REST layer on Lakebase: same data, same security, different transport. For
web and mobile clients, REST is often the right choice. For servers and analytics, SQL and the
SDK are faster and more flexible. In the next journey, [Capstone app](../capstone-app/), you'll
build a full React+FastAPI app on Databricks Apps that uses both the Data API and direct SQL to
serve manufacturing dashboards.
