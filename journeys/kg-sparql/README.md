# Query a knowledge graph with SPARQL

> ## What you'll learn
>
> **Key takeaways**
>
> - [SPARQL Protocol and RDF Query Language](../../docs/glossary.md) (SPARQL) is a query language for RDF graphs, analogous to SQL for tables. It uses pattern matching on triples: specify the shape of data you want (subject, predicate, object variables), and SPARQL returns all matches.
> - A multi-hop portfolio question like "which funds hold an instrument traded by counterparty X?" is a single readable SPARQL pattern in the graph, but becomes a recursive CTE plus a join in SQL.
> - SPARQL also supports aggregation, filtering, and optional relationships, just like SQL WHERE, GROUP BY, and LEFT JOIN.
>
> **You'll be able to:** write SPARQL queries to answer multi-hop exposure questions that would require recursion and self-joins in SQL, and compare the two approaches.
>
> **Time:** about 20 minutes  ·  **Status:** live

## The scenario

A credit alert names a counterparty, `CP-ALTAMAR`. Risk wants a complete list of funds that could
be exposed: any fund that holds an instrument traded by CP-ALTAMAR, directly or through a nested
sleeve.

In SQL, you walk the holdings tree with a recursive CTE and then join to the counterparty edge:

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

That's correct, but only if you already know to seed the recursion at each fund and walk the tree
in that order. A graph representation makes the relationship chain visible: fund holds instrument
traded_by counterparty. SPARQL lets you write that pattern directly.

## What SPARQL is

[SPARQL](../../docs/glossary.md) is a query language for [RDF](../../docs/glossary.md) graphs. Like SQL, it
returns tuples of results. Unlike SQL's table columns, SPARQL patterns are triples: you specify
variables for the parts of each triple you want to retrieve, and SPARQL matches them against the
graph.

A SPARQL query for "funds that hold instruments" looks like:

```sparql
SELECT ?fund ?instrument WHERE {
  ?fund holds ?instrument .
}
```

Add another relationship, and use the `+` property-path to walk nested sleeves, and you get a
multi-hop query:

```sparql
SELECT DISTINCT ?fund WHERE {
  ?fund holds+ ?instrument .
  ?instrument traded_by <http://bank.local/CP-ALTAMAR> .
}
```

SPARQL reads like a declarative description of the pattern you're looking for, not an imperative
set of recursion and join steps.

## The wow moment

You write a SPARQL query that reads like English ("funds that hold something traded by CP-ALTAMAR"),
run it on the graph you built earlier, and get the answer in milliseconds. Then you write the
equivalent SQL with a recursive CTE and a join and see the difference in readability. Both are
correct; the graph query is closer to how you actually think about the problem.

## What you'll do

1. Build on the graph from the previous journey (or rebuild it here).
2. Write a simple SPARQL query: "which instruments does FUND-GROWTH-A hold directly?"
3. Extend it to a multi-hop query: "which funds hold an instrument traded by CP-ALTAMAR?"
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
than recursive SQL. The next journey, [Infer and derive](../kg-infer/), shows how to layer
rules on top: state that "a fund holding anything a distressed counterparty trades is exposed," and
let the graph derive those relationships automatically.
