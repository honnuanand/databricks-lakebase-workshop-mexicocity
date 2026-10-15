# Build a knowledge graph, instructions

## How to run this journey

There are a few ways to work through the steps. Pick one:

- **Notebook, step by step (recommended for learning):** open [`kg_build.ipynb`](kg_build.ipynb) and run one cell at a time. Reading each result before the next step is where the learning happens.
- **In a Databricks workspace:** import [`kg_build_databricks.py`](kg_build_databricks.py) and run it cell by cell there.
- **By hand:** follow the numbered steps below, copying each command yourself.
- **Just see it work:** run `python kg_build.py` from this folder to execute the whole thing at once. Fast, but you learn the most from the notebook.

Run these on your own branch. If you haven't done [`../../00-setup/`](../../00-setup/), do that
first; you need `LB_PROFILE`, `LB_PROJECT`, `LB_BRANCH`, and `LB_SCHEMA` set, and the bank
loaded.

Everything here is a single script you can read: [`./kg_build.py`](./kg_build.py).
You can run it end to end, or follow the steps by hand to see each piece.

## Run it end to end

First, install rdflib if you haven't already:

```bash
pip install rdflib
```

Then run the full script:

```bash
cd journeys/kg-build
python kg_build.py
```

This loads the bank data into a knowledge graph and prints the triples and query results. Read on for what each step does; the exact output to expect is in [`expected.md`](expected.md).

## Or step through it by hand

### Step 1, load the holdings tree as triples

The script queries the bank's `fund`, `instrument`, `holding`, `counterparty`, `trade_counterparty`,
`branch`, and `trade` tables, then builds [RDF](../../docs/glossary.md) triples for each relationship:

```python
from lakebase import connect
from rdflib import Graph, Namespace, URIRef, Literal

g = Graph()
BANK = Namespace("http://bank.local/")

# Load funds
with connect() as conn:
    with conn.cursor() as cur:
        cur.execute("SELECT fund_id, name FROM bank.fund")
        for fund_id, name in cur.fetchall():
            g.add((
                URIRef(BANK[fund_id]),
                BANK.name,
                Literal(name)
            ))
```

Run the script with the `--step load` flag to see the triples being built:

```bash
python kg_build.py --step load
```

You'll see triples like:

```text
(FUND-GROWTH-A, holds, INS-SLEEVE-EQ)
(INS-QTZL, traded_by, CP-ALTAMAR)
(FUND-GROWTH-A, booked_at, BR-CDMX)
```

### Step 2, query the graph for a fund's direct holdings

Ask the graph: "which instruments does FUND-GROWTH-A hold directly?"

```bash
python kg_build.py --step query
```

The script traverses the `holds` relationship from that fund:

```sparql
SELECT ?instrument WHERE {
  ?fund <http://bank.local/holds> ?instrument .
  FILTER (?fund = <http://bank.local/FUND-GROWTH-A>)
}
```

You'll see a list of instrument IDs that are direct children of FUND-GROWTH-A in the holdings tree.

### Step 3, show the equivalent SQL

```bash
python kg_build.py --step sql
```

The script prints the equivalent SQL:

```sql
SELECT instrument_id FROM bank.holding WHERE parent_id = 'FUND-GROWTH-A'
```

This is a single-level SELECT. But when you ask "which funds hold an instrument traded by
CP-ALTAMAR?", the SQL becomes a multi-join query that also has to walk the sleeve nesting. The
graph makes it a short traversal.

## What you just did

You converted a bank data model (holdings tree, funds, branches, counterparties) into a knowledge
graph representation, loaded it into an in-memory RDF store, and ran queries. The graph is small
enough to fit in memory for this workshop; in production, you'd use a dedicated triple store like
Apache Jena or a graph database.

Compare the output against [`expected.md`](expected.md), and if anything went wrong, check
[`faq.md`](faq.md).
