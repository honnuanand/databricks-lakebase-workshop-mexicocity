# Query a knowledge graph with SPARQL, instructions

## How to run this journey

There are a few ways to work through the steps. Pick one:

- **Notebook, step by step (recommended for learning):** open [`kg_sparql.ipynb`](kg_sparql.ipynb) and run one cell at a time. Reading each result before the next step is where the learning happens.
- **In a Databricks workspace:** import [`kg_sparql_databricks.py`](kg_sparql_databricks.py) and run it cell by cell there.
- **By hand:** follow the numbered steps below, copying each command yourself.
- **Just see it work:** run `python kg_sparql.py` from this folder to execute the whole thing at once. Fast, but you learn the most from the notebook.

Build on the graph from the previous journey, or run this script to rebuild it. If you haven't
done [`../../00-setup/`](../../00-setup/), do that first; you need `LB_PROFILE`, `LB_PROJECT`,
`LB_BRANCH`, and `LB_SCHEMA` set.

Everything here is in a single script: [`./kg_sparql.py`](./kg_sparql.py).
You can run it end to end, or follow the steps by hand.

## Run it end to end

```bash
cd journeys/kg-sparql
python kg_sparql.py
```

This builds the graph and runs SPARQL queries, comparing them to equivalent SQL. Read on for
what each step does; expected output is in [`expected.md`](expected.md).

## Or step through it by hand

### Step 1, load the graph

If you already ran the kg-build journey, the graph is in memory. Otherwise, the script rebuilds it:

```bash
python kg_sparql.py --step load
```

This loads the same holdings tree and counterparty relationships from Lakebase.

### Step 2, simple SPARQL query

Ask the graph: "which instruments are held directly by FUND-GROWTH-A?"

```bash
python kg_sparql.py --step simple-query
```

The [SPARQL](../../docs/glossary.md) query is:

```sparql
SELECT ?instrument WHERE {
  ?fund <http://bank.local/holds> ?instrument .
  FILTER (?fund = <http://bank.local/FUND-GROWTH-A>)
}
```

You'll see a list of instrument IDs.

### Step 3, multi-hop SPARQL query

Now ask a harder question: "which funds hold an instrument traded by CP-ALTAMAR?"

```bash
python kg_sparql.py --step multi-hop
```

The [SPARQL](../../docs/glossary.md) query walks the holdings tree with the `holds+` property path, then
matches the counterparty edge:

```sparql
SELECT DISTINCT ?fund WHERE {
  ?fund <http://bank.local/holds>+ ?instrument .
  ?instrument <http://bank.local/traded_by> <http://bank.local/CP-ALTAMAR> .
}
```

This reads like a chain: find funds that hold instruments that are traded by CP-ALTAMAR. The
`+` makes `holds` transitive, so it reaches instruments nested under sub-sleeves. The query runs
in milliseconds because the graph is in memory and indexed.

### Step 4, equivalent SQL

```bash
python kg_sparql.py --step sql
```

The script shows the SQL equivalent, a recursive CTE that walks the holdings tree joined to the
counterparty edge:

```sql
WITH RECURSIVE tree(root_fund, node) AS (
    SELECT f.fund_id, f.fund_id FROM bank.fund f
  UNION ALL
    SELECT t.root_fund, h.instrument_id
    FROM tree t JOIN bank.holding h ON h.parent_id = t.node
)
SELECT DISTINCT t.root_fund
  FROM tree t
  JOIN bank.trade_counterparty tc ON tc.instrument_id = t.node
 WHERE tc.counterparty_id = 'CP-ALTAMAR'
   AND t.root_fund LIKE 'FUND-%'
```

And runs it against Lakebase, returning the same fund IDs.

### Step 5, aggregation query

[SPARQL](../../docs/glossary.md) supports GROUP BY and aggregates like SQL. Ask: "for each counterparty, how many distinct
instruments do they trade?"

```bash
python kg_sparql.py --step aggregate
```

The SPARQL query uses GROUP BY:

```sparql
SELECT ?counterparty (COUNT(?instrument) as ?instrument_count) WHERE {
  ?instrument <http://bank.local/traded_by> ?counterparty .
}
GROUP BY ?counterparty
```

## What you just did

You asked the same business question (funds exposed to a flagged counterparty) in three ways:
simple SPARQL, multi-hop SPARQL with a property path, and SQL with a recursive CTE. The graph
queries are more readable and closer to how you actually think about the relationships. Compare
your output to [`expected.md`](expected.md), and if anything went wrong, check [`faq.md`](faq.md).
