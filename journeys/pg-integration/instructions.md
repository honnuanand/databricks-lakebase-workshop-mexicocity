# Pg integration, instructions

## How to run this journey

There are a few ways to work through the steps. Pick one:

- **Notebook, step by step (recommended for learning):** open [`pg_integration.ipynb`](pg_integration.ipynb) and run one cell at a time. Reading each result before the next step is where the learning happens.
- **In a Databricks workspace:** import [`pg_integration_databricks.py`](pg_integration_databricks.py) and run it cell by cell there.
- **By hand:** follow the numbered steps below, copying each command yourself.
- **Just see it work:** run `python pg_integration.py` from this folder to execute the whole thing at once. Fast, but you learn the most from the notebook.

Run these on your own branch. If you haven't done [`../../00-setup/`](../../00-setup/), do that first; you need `LB_PROFILE`, `LB_PROJECT`, `LB_BRANCH`, and `LB_SCHEMA` set.

This journey is all about showing that Postgres clients work unmodified. You'll run standard information_schema queries that any BI tool, ORM, or driver would run. Everything here is a single script you can read: [`./pg_integration.py`](./pg_integration.py).

You can run it end to end, or follow the steps by hand to see each piece.

## Run it end to end

```bash
cd journeys/pg-integration
python pg_integration.py
```

The script discovers your bank schema using information_schema, builds a schema map, and prints it. Read on for what each step does; the exact output to expect is in [`expected.md`](expected.md).

## Or step through it by hand

### Step 1, query information_schema for tables

This is the query every BI tool and ORM runs to discover what's in your database:

```bash
python ../../common/scripts/lakebase.py --sql \
  "SELECT table_name FROM information_schema.tables WHERE table_schema='bank' ORDER BY table_name"
```

You'll see the 14 core bank tables: account, agent_memory, branch, case_note, counterparty, custodian, fund, holding, instrument, position, settlement, trade, trade_counterparty, txn, plus any tables that extensions (PostGIS) or earlier journeys (CDC, feature store) added to your branch. That is the real BI-tool experience: a client sees whatever is live in the database.

### Step 2, query information_schema for columns

For each table, discover the columns and types:

```bash
python ../../common/scripts/lakebase.py --sql \
  "SELECT table_name, column_name, data_type FROM information_schema.columns WHERE table_schema='bank' ORDER BY table_name, ordinal_position"
```

This is what SQLAlchemy, dbt, or Tableau runs to build a typed schema. The output is a long list of (table, column, type) tuples.

### Step 3, build a schema map

The script collects this into a map:

```bash
python pg_integration.py --step schema-map
```

The output is organized by table, showing columns and types. This is what an ORM or BI tool builds internally.

### Step 4, sample a row from each table

For a few key tables, sample a row to confirm the data is real and matches the schema:

```bash
python pg_integration.py --step sample-data
```

You'll see rows from account, trade, and txn, all real data, all matching the schema inferred from information_schema.

### Step 5, check Unity Catalog governance

In a Databricks workspace, open the Data Catalog and navigate to the Lakebase instance's schema. The same tables are listed and governed by [Unity Catalog](../../docs/glossary.md) (UC), no separate catalog sync, no proprietary metadata layer. The single source of truth is Postgres, and UC layers governance on top.

## What you just did

You discovered the entire bank schema using standard Postgres information_schema queries, the exact queries BI tools and ORMs run. You confirmed the data is real and matches the schema. You showed that Lakebase is just Postgres from the client's perspective: no adapters, no special integration code, no lock-in. Compare the results you saw against [`expected.md`](expected.md), and if anything went sideways, [`faq.md`](faq.md) has the common causes.
