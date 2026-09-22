# Pg integration, FAQ

## It connected fine, but information_schema is empty

Make sure you're searching in the correct schema. The factory tables are in the `factory` schema, not `public`. If you didn't set `LB_SCHEMA=factory` or run the query with `WHERE table_schema='factory'`, you won't see the factory tables.

Also check that the factory schema was loaded during setup. Run:

```bash
python lakebase.py --sql "SELECT * FROM factory.machine LIMIT 1"
```

If that fails with "relation not found," run the factory schema and seed load from [`../../00-setup/`](../../00-setup/).

## My BI tool connected but shows no tables

Your BI tool is likely querying the default `public` schema, not `factory`. Most BI tools let you select or filter by schema. Point it at `factory` and it should discover the tables. If the BI tool has a "schema search path" setting, make sure `factory` is listed first.

## Why doesn't Lakebase have extension X (PostGIS, pgvector)?

Lakebase is a managed Postgres system, so some extensions require additional setup or may not be available yet. Standard SQL and many common extensions are available. If you need a specific extension, ask your Databricks account team, some are prioritized based on customer demand.

## Can I use psql directly?

Yes. psql is a Postgres client and Lakebase speaks Postgres wire protocol. You can connect with:

```bash
psql -h <your-endpoint-host> -U <your-user> -d databricks_postgres
```

Then run queries normally. You'll be prompted for a password (use your Databricks OAuth token). The same information_schema queries work in psql.

## I see different column names or types than expected

Check that you're querying the right table. Run:

```bash
python lakebase.py --sql \
  "SELECT table_name, column_name, data_type FROM information_schema.columns WHERE table_name='machine'"
```

If the columns don't match the factory_schema.sql, the seed data may not have loaded correctly. Re-run the load (see setup).

## Can I use an ORM like SQLAlchemy?

Yes. SQLAlchemy has a Postgres dialect that works with Lakebase. Create a connection string like:

```python
from sqlalchemy import create_engine
engine = create_engine("postgresql+psycopg://user:password@host:5432/databricks_postgres")
```

SQLAlchemy will query information_schema to discover your schema and generate ORM models automatically. This is exactly the "it just works" moment the journey is about.

## Does Lakebase support logical decoding ([change data capture](../../docs/glossary.md) (CDC))?

Logical decoding (which powers change-data-capture) is on the Lakebase roadmap. For now, the MANAGED_ONLINE_CATALOG foreign-table approach (see [Write to analytics](../write-to-analytics/)) is the supported live-integration method. You can also use Databricks [change data capture](../../docs/glossary.md) (CDC) to capture Lakebase table changes in Unity Catalog.

## Is there a governance model for information_schema?

Yes. [Unity Catalog](../../docs/glossary.md) governs all tables, including whether you can read information_schema. If you can SELECT from a table in the factory schema, you can see it in information_schema. [Unity Catalog](../../docs/glossary.md) (UC) permissions cascade: if you're denied access to a table, it won't appear in information_schema queries either (depending on your Catalog permissions).

## Why is the wire protocol "Postgres 16" and not "Postgres 17"?

Lakebase currently advertises Postgres 16 compatibility (wire protocol version). This means clients and tools built for Postgres 16 will work. Future Lakebase releases may bump the advertised version as the system evolves. It's a version number; the capabilities matter more.

## Can I run EXPLAIN or ANALYZE?

Yes. These are standard Postgres query-planning tools and work on Lakebase. You can use them to tune queries and understand the query planner. The journey [Tune the planner](../pg-perf/) showcases this.

## I want to connect from Tableau / Looker / Power BI. Does it work?

If the tool has a Postgres connector, it should work with Lakebase (assuming you have the tool's license and your workspace has network access to Lakebase). The tool will query information_schema just like the script does, discover your schema, and let you build reports. Unity Catalog governs row/column-level access.

## My connection is slow

Lakebase compute responds in milliseconds to queries. If connections are slow:
- Check your network latency to the endpoint host (should be <50 ms in the same region).
- If compute is stopped (see [Scale to zero](../scale-to-zero/)), restart it.
- If queries are slow, that's a separate issue (see [Tune the planner](../pg-perf/)); connection speed is usually network, not the database.
