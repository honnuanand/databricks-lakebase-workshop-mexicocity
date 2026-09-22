# Query a knowledge graph with SPARQL, expected results

Use this to check your run. Your product and supplier lists depend on the factory seed data you
loaded, but the structure of the queries and results should match.

## Step 2, simple SPARQL query

Running `python kg_sparql.py --step simple-query` shows:

```text
SPARQL query: which parts are contained in PRD-GEARBOX-X1?
  PT-BEARING-6204
  PT-GEAR-420
  PT-SHAFT-110
  PT-HOUSING-08
```

These are the direct child parts of PRD-GEARBOX-X1 in the BOM.

## Step 3, multi-hop SPARQL query

Running `python kg_sparql.py --step multi-hop` shows:

```text
SPARQL multi-hop query: which products contain a part from S-ACME?
  PRD-GEARBOX-X1
  PRD-MOTOR-2HP
  PRD-PUMP-SERIES-A
```

These are all finished products that, directly or indirectly, contain parts supplied by S-ACME.
The SPARQL pattern traverses:
  product contains part
  part supplied_by supplier
  filter supplier = S-ACME

## Step 4, equivalent SQL

Running `python kg_sparql.py --step sql` shows:

```text
Equivalent SQL query:
SELECT DISTINCT p.product_id
  FROM product p
  JOIN bom_edge b ON p.product_id = b.parent_id
  JOIN part pt ON b.child_part = pt.part_id
  JOIN part_supplier ps ON pt.part_id = ps.part_id
  JOIN supplier s ON ps.supplier_id = s.supplier_id
 WHERE s.supplier_id = 'S-ACME'

Results:
  PRD-GEARBOX-X1
  PRD-MOTOR-2HP
  PRD-PUMP-SERIES-A
```

Both queries return the same product IDs. The SPARQL version reads as a description of the
relationship chain; the SQL version is explicit about join order and table names.

## Step 5, aggregation query

Running `python kg_sparql.py --step aggregate` shows:

```text
SPARQL aggregation query: parts per supplier
  S-ACME: 8
  S-BEARINGS-LTD: 5
  S-STEELCO: 12
  S-PREMIUM-PARTS: 3
```

The SPARQL GROUP BY aggregates across all triples, counting distinct parts per supplier.

## Full run output

Running the script end to end:

```text
Loading graph...
  Loaded 250 triples

Simple query: parts in PRD-GEARBOX-X1?
  PT-BEARING-6204
  PT-GEAR-420
  PT-SHAFT-110
  PT-HOUSING-08

Multi-hop query: products with S-ACME parts?
  PRD-GEARBOX-X1
  PRD-MOTOR-2HP
  PRD-PUMP-SERIES-A

Equivalent SQL (from Lakebase):
  PRD-GEARBOX-X1
  PRD-MOTOR-2HP
  PRD-PUMP-SERIES-A

Aggregation: parts per supplier
  S-ACME: 8
  S-BEARINGS-LTD: 5
  S-STEELCO: 12
  S-PREMIUM-PARTS: 3

Done. SPARQL queries complete.
```

## The numbers that matter

| What | Expected | Why it matters |
| ---- | -------- | -------------- |
| simple query latency | <5 ms | graph is indexed; queries are fast |
| multi-hop query latency | <10 ms | traversal across three relationships still sub-millisecond |
| products affected by one supplier | 3-15 | typical supply-chain distribution; the more suppliers you have, the more products each typically serves |
| result consistency | identical | SPARQL and SQL return the same product IDs, proving correctness |

> **Note**
> SPARQL's power becomes evident with deeper graphs. A 10-hop question in SQL would be 10 joins.
> In SPARQL, it's still a readable pattern. For production use, consider a dedicated triple store
> optimized for deep traversals.
