# Build a knowledge graph

> ## What you'll learn
>
> **Key takeaways**
>
> - A knowledge graph represents facts as triples (subject, predicate, object): `M-204 operates_in PL-DETROIT`, `PT-BEARING-6204 contained_in PRD-GEARBOX-X1`. The same relationships you'd express in SQL joins become explicit, queryable nodes.
> - [Resource Description Framework](../../docs/glossary.md) (RDF) and semantic tools like rdflib let you load these triples into an in-memory graph, add reasoning rules, and ask questions that would require multiple SQL self-joins.
> - The factory schema's bill of materials is already a tree (bom_edge parent→child). Converting it to triples and loading into a graph makes that structure speak for itself: "which finished products use parts supplied by vendor V?" is a single hop in the graph, a multi-join in SQL.
>
> **You'll be able to:** load the factory's BOM, machines, and supply relationships into an [RDF](../../docs/glossary.md) knowledge graph using Python and rdflib, then query the graph to answer manufacturing questions.
>
> **Time:** about 20 minutes  ·  **Status:** live

## The scenario

You have a stamping plant with machines, a bill of materials connecting products to parts, and suppliers that provide those parts. A regulatory recall comes in: supplier `S-ACME` recalled one bearing. You need to know fast: which finished products could be affected?

In SQL, this is a multi-join query: products that contain parts that come from S-ACME. With a graph representation, those relationships become nodes you traverse: product → contains → part → supplied_by → supplier. Ask the same question, get a single-hop answer.

A knowledge graph is a way to surface relationships explicitly, so complex chains become navigable paths instead of nested queries.

## What a knowledge graph actually is

A knowledge graph is built from triples: (subject, predicate, object). Each triple is a fact. A supplier statement `S-ACME supplies PT-BEARING-6204` becomes:

```
(S-ACME, supplies, PT-BEARING-6204)
```

Store millions of these triples, and you have a graph where each node (S-ACME, PT-BEARING-6204) can have incoming and outgoing edges (supplies relationships). Query it by traversing those edges.

[Resource Description Framework](../../docs/glossary.md) (RDF) is a standard format for triples. rdflib is a Python library that lets you load RDF into memory, add rules, and run [SPARQL](../../docs/glossary.md) queries (a query language for graphs, similar in power to SQL but built for linked data).

## The wow moment

You write 15 lines of Python to load the factory's BOM into a graph, then ask "which products contain a part from supplier S-ACME?" by traversing edges. The same question in SQL would be 3 joins and a subquery. The graph makes it readable.

## What you'll do

1. Load the factory BOM, machines, and supplier relationships from Lakebase into an [RDF](../../docs/glossary.md) triple store.
2. Run a simple query: "which parts does product PRD-GEARBOX-X1 contain?"
3. Add a rule and derive new facts the database never stored.
4. Compare the graph query to an equivalent SQL multi-join.

Full copy-paste steps are in [`instructions.md`](instructions.md); the exact output is in [`expected.md`](expected.md).

## Prerequisites

Finish [`../../00-setup/`](../../00-setup/) so you have a branch and can connect. You'll need `rdflib` installed:

```bash
pip install rdflib
```

This journey stands alone; no other journeys need to complete first. You'll use this graph as the foundation for [SPARQL queries](../kg-sparql/) and [inference/entailment](../kg-infer/) next.

## Wrapping up

Once you see the BOM as a graph instead of nested table joins, you have a new tool for manufacturing questions: assembly paths, recall impact, supply-chain disruption analysis. The next journey goes deeper into SPARQL, the query language for graphs, to ask multi-hop questions without writing nested SQL. Then [Infer and derive](../kg-infer/) shows how to layer rules on top of the graph so it can answer questions about facts you never stored.
