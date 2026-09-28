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

Running `python kg_sparql.py --step multi-hop` shows the [SPARQL](../../docs/glossary.md) pattern:

```text
SPARQL multi-hop query: which products contain a part from SUP-FASTENALL?
  PRD-GEARBOX-X1
```

In the seed, SUP-FASTENALL supplies PT-BOLT-M8, which is in the PRD-GEARBOX-X1 bill of materials,
so that product comes back. These are the finished products that, directly or indirectly, contain
parts supplied by SUP-FASTENALL.
The SPARQL pattern traverses:
  product contains part
  part supplied_by supplier
  filter supplier = SUP-FASTENALL

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
 WHERE s.supplier_id = 'SUP-FASTENALL'

Results:
  PRD-GEARBOX-X1
```

Both queries return the same product IDs. The SPARQL version reads as a description of the
relationship chain; the SQL version is explicit about join order and table names.

## Step 5, aggregation query

Running `python kg_sparql.py --step aggregate` shows:

```text
SPARQL aggregation query: parts per supplier
  SUP-BEARINGCO: 1
  SUP-FASTENALL: 1
  SUP-GEARWORKS: 1
```

The SPARQL GROUP BY aggregates across all triples, counting distinct parts per supplier. In the
small seed each supplier supplies one part; with more `part_supplier` rows the counts grow.

## Full run output

Running the script end to end (your triple count and ordering may vary slightly):

```text
Loading graph...
  Loaded 18 triples

Simple query: parts in PRD-GEARBOX-X1?
  PT-HOUSING-GX
  PT-GEAR-ASSY
  PT-BOLT-M8

Multi-hop query: products with SUP-FASTENALL parts?
  PRD-GEARBOX-X1

Equivalent SQL (from Lakebase):
  PRD-GEARBOX-X1

Aggregation: parts per supplier
  SUP-BEARINGCO: 1
  SUP-FASTENALL: 1
  SUP-GEARWORKS: 1

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
