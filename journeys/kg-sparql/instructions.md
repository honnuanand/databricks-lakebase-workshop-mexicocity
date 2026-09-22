# Query a knowledge graph with SPARQL, instructions

Build on the graph from the previous journey, or run this script to rebuild it. If you haven't
done [`../../00-setup/`](../../00-setup/), do that first; you need `LB_PROFILE`, `LB_PROJECT`,
`LB_BRANCH`, and `LB_SCHEMA` set.

Everything here is in a single script: [`../../common/scripts/kg_sparql.py`](../../common/scripts/kg_sparql.py).
You can run it end to end, or follow the steps by hand.

## Run it end to end

```bash
cd common/scripts
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

This loads the same BOM, supplier, and machine relationships from Lakebase.

### Step 2, simple SPARQL query

Ask the graph: "which parts are contained in product PRD-GEARBOX-X1?"

```bash
python kg_sparql.py --step simple-query
```

The SPARQL query is:

```sparql
SELECT ?part WHERE {
  ?product <http://factory.local/contains> ?part .
  FILTER (?product = <http://factory.local/PRD-GEARBOX-X1>)
}
```

You'll see a list of part IDs.

### Step 3, multi-hop SPARQL query

Now ask a harder question: "which finished products contain a part supplied by S-ACME?"

```bash
python kg_sparql.py --step multi-hop
```

The SPARQL query traverses three relationships:

```sparql
SELECT DISTINCT ?product WHERE {
  ?product <http://factory.local/contains> ?part .
  ?part <http://factory.local/supplied_by> ?supplier .
  FILTER (?supplier = <http://factory.local/S-ACME>)
}
```

This reads like a chain: find products that contain parts that are supplied by S-ACME. The
query runs in milliseconds because the graph is in memory and indexed.

### Step 4, equivalent SQL

```bash
python kg_sparql.py --step sql
```

The script shows the SQL equivalent:

```sql
SELECT DISTINCT p.product_id
  FROM product p
  JOIN bom_edge b ON p.product_id = b.parent_id
  JOIN part pt ON b.child_part = pt.part_id
  JOIN part_supplier ps ON pt.part_id = ps.part_id
  JOIN supplier s ON ps.supplier_id = s.supplier_id
 WHERE s.supplier_id = 'S-ACME'
```

And runs it against Lakebase, returning the same product IDs.

### Step 5, aggregation query

SPARQL supports GROUP BY and aggregates like SQL. Ask: "for each supplier, how many distinct
parts do they supply?"

```bash
python kg_sparql.py --step aggregate
```

The SPARQL query uses GROUP BY:

```sparql
SELECT ?supplier (COUNT(?part) as ?part_count) WHERE {
  ?part <http://factory.local/supplied_by> ?supplier .
}
GROUP BY ?supplier
```

## What you just did

You asked the same business question (products affected by a supplier disruption) in three ways:
simple SPARQL, multi-hop SPARQL with patterns, and SQL with joins. The graph queries are more
readable and closer to how you actually think about the relationships. Compare your output to
[`expected.md`](expected.md), and if anything went wrong, check [`faq.md`](faq.md).
