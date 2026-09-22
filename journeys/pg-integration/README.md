# Pg integration

> ## What you'll learn
>
> **Key takeaways**
>
> - Lakebase speaks standard Postgres wire protocol v16, so any driver, ORM, or BI tool connects unmodified.
> - The information_schema is identical to Postgres, a BI tool or ORM introspects your whole schema automatically.
> - Unity Catalog governs the whole database, with no proprietary adapters or connectors needed.
>
> **You'll be able to:** point any Postgres client or tool at Lakebase and confirm it discovers the full schema with no special integration code.
>
> **Time:** about 10 minutes  ·  **Status:** live

## The scenario

You're the architect picking a database for the factory's operational system. The MES, the shop floor, the supply-chain apps, they all have existing integrations: SQLAlchemy, JDBC, Tableau, dbt, Metabase. If you pick a proprietary database, those integrations break. You need adapters, shims, consultants.

You pitch Lakebase to the team. The answer you need is simple: will the tools we already use just work?

The answer is yes. Lakebase *is* standard Postgres wire protocol. psql, JDBC, Go's pq driver, Python's psycopg, everything that speaks Postgres connects with zero adapter, discovers the schema automatically, and governs the data with Unity Catalog on top.

## What this means

Lakebase advertises itself as Postgres 16 on the wire. When a client connects, it sees a standard Postgres server. The information_schema (the system tables that describe the database schema) is Postgres-compatible. An ORM like SQLAlchemy can query information_schema to learn every table and column. A BI tool like Tableau can do the same. You're not locked into Databricks' ecosystem; you're locked into Postgres', which is everywhere.

> **Note**
> This is the "it fits your landscape" moment. The journey doesn't showcase advanced Postgres features (those come later in other journeys). It showcases the architectural fit: if you already use Postgres tools, Lakebase works as a drop-in replacement. The magic is boring, which is the point.

## The wow moment

The beat worth watching: you run a single SQL query against the information_schema, the same query a BI tool runs, and it maps your entire factory schema: 26 tables, 133 columns, all relationships. No Databricks SDK, no Lakebase-specific plumbing. Just Postgres.

> **From the field**
> The honest scope: Lakebase is wire-compatible Postgres, so standard introspection works. Some advanced Postgres features (logical decoding for [change data capture](../../docs/glossary.md) (CDC)) are on the Lakebase roadmap. You won't find every exotic extension ([PostGIS](../../docs/glossary.md), [pgvector](../../docs/glossary.md), etc.) immediately, but the governance (Unity Catalog) wraps the whole database without needing a separate auth layer. ORMs and BI tools that target Postgres 16 work unmodified. This is about eliminating lock-in, not about getting everything Postgres ever had.

## What you'll do

1. Query the information_schema to discover all tables in the factory schema.
2. Query information_schema to discover all columns and their types.
3. Build a simple schema map (tables → columns → types), exactly what a BI tool does.
4. Confirm the data is accurate by sampling a row from one table.
5. Show that the same schema is visible in Databricks Catalog (Unity Catalog governs it).

Full copy-paste steps are in [`instructions.md`](instructions.md); the exact output and timings to check against are in [`expected.md`](expected.md).

## Prerequisites

Finish [`../../00-setup/`](../../00-setup/) so you have a branch and can connect. You also need:
- Any Postgres client (psql, Python, Java, Go, anything that speaks Postgres wire protocol).
- For the Unity Catalog visibility check, access to your Databricks workspace.

Nothing Lakebase-specific; this journey is about confirming you can use the tools you already have.

## Wrapping up

Once you confirm that standard tools work unmodified, the question shifts from "does this fit my stack?" to "what does this let me do that I couldn't before?" The Lakebase-specific journeys answer that: branching, [point-in-time restore](../../docs/glossary.md) (PITR), live data flow, [row-level security](../../docs/glossary.md) (RLS), vector search, knowledge graphs. But the foundation is always "it's just Postgres."
