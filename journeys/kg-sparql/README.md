# Query a knowledge graph with SPARQL

> ## What you'll learn
>
> **Key takeaways**
>
> - [SPARQL Protocol and RDF Query Language](../../docs/glossary.md) (SPARQL) is a query language for RDF graphs, analogous to SQL for tables. It uses pattern matching on triples: specify the shape of data you want (subject, predicate, object variables), and SPARQL returns all matches.
> - A multi-hop manufacturing question like "which finished products contain a part supplied by vendor V?" is a single readable SPARQL pattern in the graph, but becomes a 3-table join in SQL.
> - SPARQL also supports aggregation, filtering, and optional relationships, just like SQL WHERE, GROUP BY, and LEFT JOIN.
>
> **You'll be able to:** write SPARQL queries to answer multi-hop manufacturing questions that would require self-joins in SQL, and compare the two approaches.
>
> **Time:** about 20 minutes  ·  **Status:** live

## The scenario

You know a supplier, SUP-FASTENALL, was disrupted. You need a complete list of finished products that
could be affected: any product that contains a part supplied by SUP-FASTENALL, directly or in a
subassembly.

In SQL, you'd write:

```sql
SELECT DISTINCT p.product_id
  FROM product p
  JOIN bom_edge b1 ON p.product_id = b1.parent_id
  JOIN part pt ON b1.child_part = pt.part_id
  JOIN part_supplier ps ON pt.part_id = ps.part_id
  JOIN supplier s ON ps.supplier_id = s.supplier_id
 WHERE s.supplier_id = 'SUP-FASTENALL'
```

That's readable, but only if you already know to join those specific tables in that order. A
graph representation makes the relationship chain visible: product → contains → part →
supplied_by → supplier. SPARQL lets you write that pattern directly.

## What SPARQL is

[SPARQL](../../docs/glossary.md) is a query language for [RDF](../../docs/glossary.md) graphs. Like SQL, it
returns tuples of results. Unlike SQL's table columns, SPARQL patterns are triples: you specify
variables for the parts of each triple you want to retrieve, and SPARQL matches them against the
graph.

A SPARQL query for "products that contain parts" looks like:

```sparql
SELECT ?product ?part WHERE {
  ?product contains ?part .
}
```

Add another relationship and you get a multi-hop query:

```sparql
SELECT ?product WHERE {
  ?product contains ?part .
  ?part supplied_by ?supplier .
  FILTER (?supplier = <http://factory.local/SUP-FASTENALL>)
}
```

SPARQL reads like a declarative description of the pattern you're looking for, not an imperative
set of join steps.

## The wow moment

You write a SPARQL query that reads like English ("products that contain parts from SUP-FASTENALL"),
run it on the graph you built earlier, and get the answer in milliseconds. Then you write the
equivalent SQL with 3 joins and see the difference in readability. Both are correct; the graph
query is closer to how you actually think about the problem.

## What you'll do

1. Build on the graph from the previous journey (or rebuild it here).
2. Write a simple SPARQL query: "which parts does product PRD-GEARBOX-X1 contain?"
3. Extend it to a multi-hop query: "which finished products contain a part from supplier SUP-FASTENALL?"
4. Write the equivalent SQL and compare readability and performance.

Full copy-paste steps are in [`instructions.md`](instructions.md); expected output is in
[`expected.md`](expected.md).

## Prerequisites

Finish [`../../00-setup/`](../../00-setup/) so you have a branch and can connect. You should
also complete [Build a knowledge graph](../kg-build/) first, so you understand the graph
structure; this journey builds directly on top of it.

Install rdflib if you haven't already:

```bash
pip install rdflib
```

## Wrapping up

SPARQL queries on a graph scale well for multi-hop questions and read closer to business logic
than nested SQL joins. The next journey, [Infer and derive](../kg-infer/), shows how to layer
rules on top: state that "a recall of part P affects all products containing P," and let the
graph derive those relationships automatically.
