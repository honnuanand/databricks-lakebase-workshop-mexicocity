# Build a knowledge graph, instructions

## How to run this journey

There are a few ways to work through the steps. Pick one:

- **Notebook, step by step (recommended for learning):** open [`kg_build.ipynb`](kg_build.ipynb) and run one cell at a time. Reading each result before the next step is where the learning happens.
- **In a Databricks workspace:** import [`kg_build_databricks.py`](kg_build_databricks.py) and run it cell by cell there.
- **By hand:** follow the numbered steps below, copying each command yourself.
- **Just see it work:** run `python kg_build.py` from this folder to execute the whole thing at once. Fast, but you learn the most from the notebook.

Run these on your own branch. If you haven't done [`../../00-setup/`](../../00-setup/), do that
first; you need `LB_PROFILE`, `LB_PROJECT`, `LB_BRANCH`, and `LB_SCHEMA` set, and the factory
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

This loads the factory data into a knowledge graph and prints the triples and query results. Read on for what each step does; the exact output to expect is in [`expected.md`](expected.md).

## Or step through it by hand

### Step 1, load the BOM as triples

The script queries the factory's bom_edge, product, and part tables, then builds [RDF](../../docs/glossary.md) triples
for each relationship:

```python
from lakebase import connect
from rdflib import Graph, Namespace, URIRef, Literal

g = Graph()
FACTORY = Namespace("http://factory.local/")

# Load products
with connect() as conn:
    with conn.cursor() as cur:
        cur.execute("SELECT product_id, name FROM factory.product")
        for product_id, name in cur.fetchall():
            g.add((
                URIRef(FACTORY[product_id]),
                FACTORY.name,
                Literal(name)
            ))
```

Run the script with the `--step load` flag to see the triples being built:

```bash
python kg_build.py --step load
```

You'll see triples like:

```text
(PRD-GEARBOX-X1, contains, PT-BEARING-6204)
(PT-BEARING-6204, supplied_by, S-ACME)
(M-204, operates_in, PL-DETROIT)
```

### Step 2, query the graph for a single BOM path

Ask the graph: "what parts does product PRD-GEARBOX-X1 contain?"

```bash
python kg_build.py --step query
```

The script uses a simple [SPARQL](../../docs/glossary.md) query:

```sparql
SELECT ?part WHERE {
  ?prod <http://factory.local/contains> ?part .
  FILTER (?prod = <http://factory.local/PRD-GEARBOX-X1>)
}
```

You'll see a list of part IDs that are direct children of PRD-GEARBOX-X1 in the BOM.

### Step 3, show the equivalent SQL

```bash
python kg_build.py --step sql
```

The script prints the equivalent SQL:

```sql
SELECT child_part FROM factory.bom_edge WHERE parent_id = 'PRD-GEARBOX-X1'
```

This is a single-row SELECT. But when you ask "which products contain a part from supplier S-ACME?",
the SQL becomes a 3-join query. The graph makes it a 2-hop traversal.

## What you just did

You converted a manufacturing data model (BOM tree, machines, suppliers) into a knowledge graph
representation, loaded it into an in-memory RDF store, and ran queries. The graph is small enough
to fit in memory for this workshop; in production, you'd use a dedicated triple store like
Apache Jena or a graph database.

Compare the output against [`expected.md`](expected.md), and if anything went wrong, check
[`faq.md`](faq.md).
