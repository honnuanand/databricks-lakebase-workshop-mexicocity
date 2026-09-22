# Build a knowledge graph, expected results

Use this to check your run. Your exact triple counts may vary slightly depending on the factory
data you loaded, but the structure and query shapes should match.

## Step 1, load the BOM as triples

Running the full script prints a summary of triples loaded:

```text
Loaded 250 triples:
  - 45 product nodes
  - 120 part nodes
  - 85 BOM edges (contains relationships)
  - 8 supplier nodes
  - 12 part_supplied_by edges
  - 15 machines and operates_in relationships
  - (plus name and property triples)
```

The exact counts depend on your factory seed data, but you should see hundreds of triples.

## Step 2, query the BOM

Running `python kg_build.py --step query` (or the full script) shows:

```text
Parts contained in PRD-GEARBOX-X1:
  PT-BEARING-6204
  PT-GEAR-420
  PT-SHAFT-110
  PT-HOUSING-08
```

This is a direct query into the graph's contains relationships. The SPARQL query is:

```sparql
SELECT ?part WHERE {
  ?prod <http://factory.local/contains> ?part .
  FILTER (?prod = <http://factory.local/PRD-GEARBOX-X1>)
}
```

## Step 3, equivalent SQL

The script shows the same query in SQL:

```text
SQL equivalent:
SELECT child_part FROM factory.bom_edge WHERE parent_id = 'PRD-GEARBOX-X1'
```

Both return the same part IDs. In this simple case they're equally readable. But when you ask
a multi-hop question like "which products contain a part from supplier S-ACME?", the SQL joins
grow and the graph query stays shallow.

## Full run output

Running the whole script end to end produces output like:

```text
Loading factory into RDF graph...
  Loaded 250 triples
  Loaded 45 products
  Loaded 120 parts
  Loaded 85 BOM edges
  Loaded 8 suppliers
  Loaded 12 supplier relationships

Querying: which parts does PRD-GEARBOX-X1 contain?
  PT-BEARING-6204
  PT-GEAR-420
  PT-SHAFT-110
  PT-HOUSING-08

Equivalent SQL:
SELECT child_part FROM factory.bom_edge WHERE parent_id = 'PRD-GEARBOX-X1'
  Result: [('PT-BEARING-6204',), ('PT-GEAR-420',), ('PT-SHAFT-110',), ('PT-HOUSING-08',)]

Done. Graph ready for SPARQL queries.
```

## The numbers that matter

| What | Expected | Why it matters |
| ---- | -------- | -------------- |
| triples loaded | 200-300 | reflects your factory's BOM depth and supplier relationships |
| parts per product | typically 3-6 | BOM complexity; deeper trees mean more complex recall analysis |
| suppliers in graph | 8-15 | supply-chain density |
| time to load | under 1 second | rdflib is fast for small to medium graphs |

> **Note**
> For production graphs with millions of triples, you'd use a purpose-built triple store
> (Apache Jena, RDF4J, or a managed service). For this workshop, in-memory rdflib is sufficient
> and teaches the mechanics directly.
