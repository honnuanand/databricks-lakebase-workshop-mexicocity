# Postgres in your browser

> ## What you'll learn
>
> **Key takeaways**
>
> - PGlite: full PostgreSQL (18.3) compiled to WebAssembly, running entirely client-side in your browser.
> - Same SQL as Lakebase: CREATE, INSERT, JSON, window functions, ON CONFLICT, all execute in the browser in single-digit milliseconds.
> - Local-first primitive: work offline, then sync back to Lakebase when connectivity returns.
>
> **You'll be able to:** write real SQL in the browser, run queries locally with zero network, and understand why edge Postgres matters.
>
> **Time:** about 10 minutes  ·  **Status:** live

## The scenario

You're a relationship manager visiting a client, or a field agent in a branch where network is spotty. You need to look up an account's recent transactions, check its spec, and update its status, all on a tablet, offline if needed.

Traditional setup: "I need to connect to the Lakebase instance in the cloud." But the network is slow or intermittent. The latency adds up; every query waits. The work grinds.

Modern setup: **Postgres runs on the edge**, on the device itself, in the browser via WebAssembly. The agent works offline. Queries run in milliseconds (no network). When connectivity returns, changes sync back to the central Lakebase instance.

This is PGlite: the same Postgres engine you run on Lakebase, now at the edge. Same SQL semantics, same data types (JSON, vectors, geography), zero network overhead while working locally.

## The wow moment

Open the interactive SQL editor below. Type or copy-paste real Postgres SQL. Hit Run. The query executes in the browser in a few milliseconds. No server, no round-trip. You can CREATE TABLE, INSERT, SELECT, JOIN, use JSON, all the Postgres you know, running client-side.

## What you'll do

1. Open the interactive editor (below).
2. Run SQL examples: CREATE TABLE, INSERT, SELECT with JSON and window functions.
3. See the results print instantly (single-digit milliseconds).
4. Understand how this powers offline-first local-first applications.

## The interactive editor

Open [`pglite-demo.html`](pglite-demo.html) (in this journey folder) in your browser.

Type SQL or use the "Quick Examples" buttons to load common patterns. Hit "Run SQL" and watch the results appear.

Everything runs client-side; there's no server call. The entire Postgres engine (a few MB of WASM) loads on first open.

## Prerequisites

A modern browser with JavaScript enabled. That's it. No backend required.

## Wrapping up

PGlite bridges operational Postgres (Lakebase in the cloud) and edge Postgres (local, on-device, offline). The next step
is syncing: when connectivity returns, electric-sql or similar sync engines keep the two copies in step. This is the future of
full-stack applications: strong consistency at the edge, consistent data across your users.

You've now completed all 8 Postgres-power journeys (part B):
- [`../pg-perf/`](../pg-perf/), tune the planner.
- [`../pg-index/`](../pg-index/), six index types.
- [`../pg-iso/`](../pg-iso/), isolation & locking.
- [`../pg-partition/`](../pg-partition/), scale-out partitioning.
- [`../pg-features/`](../pg-features/), online feature store.
- [`../pg-one-database/`](../pg-one-database/), one query, every type.
- [`../pg-cdc/`](../pg-cdc/), change-feeds (preview).
- Here, Postgres at the edge.
