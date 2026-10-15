# Build a knowledge graph

> ## What you'll learn
>
> **Key takeaways**
>
> - A knowledge graph represents facts as triples (subject, predicate, object): `FUND-GROWTH-A booked_at BR-CDMX`, `INS-QTZL traded_by CP-ALTAMAR`. The same relationships you would express in SQL joins become explicit, queryable nodes.
> - [Resource Description Framework](../../docs/glossary.md) (RDF) and semantic tools like rdflib let you load these triples into an in-memory graph, add reasoning rules, and ask questions that would require multiple SQL self-joins.
> - The bank schema's holdings tree is already a tree (`holding` parent to child). Converting it to triples and loading it into a graph makes that structure speak for itself: "which funds hold an instrument traded by counterparty X?" is a single hop in the graph, a multi-join in SQL.
>
> **You'll be able to:** load the bank's holdings tree, funds, and counterparty relationships into an [RDF](../../docs/glossary.md) knowledge graph using Python and rdflib, then query the graph to answer portfolio-risk questions.
>
> **Time:** about 20 minutes  ·  **Status:** live

## The scenario

You run a bank with funds that hold instruments, branches that book those funds, and counterparties that trade those instruments. A credit alert comes in: counterparty `CP-ALTAMAR` is flagged. You need to know fast: which funds hold anything that counterparty trades?

In SQL, this is a multi-join query: funds that hold instruments that are traded by CP-ALTAMAR, following the holdings tree up through its sleeves. With a graph representation, those relationships become nodes you traverse: fund holds instrument, instrument traded_by counterparty. Ask the same question, get a single-hop answer.

A knowledge graph is a way to surface relationships explicitly, so complex chains become navigable paths instead of nested queries.

## What a knowledge graph actually is

A knowledge graph is built from triples: (subject, predicate, object). Each triple is a fact. A trading statement `CP-ALTAMAR trades INS-QTZL` becomes:

```
(INS-QTZL, traded_by, CP-ALTAMAR)
```

Store millions of these triples, and you have a graph where each node (INS-QTZL, CP-ALTAMAR) can have incoming and outgoing edges (traded_by relationships). Query it by traversing those edges.

[Resource Description Framework](../../docs/glossary.md) (RDF) is a standard format for triples. rdflib is a Python library that lets you load RDF into memory, add rules, and run [SPARQL](../../docs/glossary.md) queries (a query language for graphs, similar in power to SQL but built for linked data).

## The wow moment

You write 15 lines of Python to load the bank's holdings tree into a graph, then ask "which instruments does FUND-GROWTH-A hold?" by traversing edges. The same question in SQL would be a join and a subquery. The graph makes it readable.

## What you'll do

1. Load the bank funds, instruments, holdings tree, branches, and counterparty relationships from Lakebase into an [RDF](../../docs/glossary.md) triple store.
2. Run a simple query: "which instruments does FUND-GROWTH-A hold?"
3. Compare the graph query to an equivalent SQL query.
4. Leave the graph ready for the multi-hop SPARQL and inference journeys that follow.

Full copy-paste steps are in [`instructions.md`](instructions.md); the exact output is in [`expected.md`](expected.md).

## Prerequisites

Finish [`../../00-setup/`](../../00-setup/) so you have a branch and can connect. You'll need `rdflib` installed:

```bash
pip install rdflib
```

This journey stands alone; no other journeys need to complete first. You'll use this graph as the foundation for [SPARQL queries](../kg-sparql/) and [inference and entailment](../kg-infer/) next.

## Wrapping up

Once you see the holdings tree as a graph instead of nested table joins, you have a new tool for portfolio-risk questions: exposure paths, counterparty impact, concentration analysis. The next journey goes deeper into SPARQL, the query language for graphs, to ask multi-hop questions without writing nested SQL. Then [Infer and derive](../kg-infer/) shows how to layer rules on top of the graph so it can answer questions about facts you never stored, like which funds are exposed to a distressed counterparty.
