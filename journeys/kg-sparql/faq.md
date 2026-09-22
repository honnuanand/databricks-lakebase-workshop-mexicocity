# Query a knowledge graph with SPARQL, FAQ

## Common errors and fixes

### `ModuleNotFoundError: No module named 'rdflib'`

Install rdflib:

```bash
pip install rdflib
```

Or on a Databricks-managed laptop:

```bash
pip install rdflib
```

### `Missing required env var LB_PROFILE`

Set your environment variables (see [`../../00-setup/auth.md`](../../00-setup/auth.md)):

```bash
export LB_PROFILE=<your-profile>
export LB_PROJECT=<project-id>
export LB_BRANCH=<branch-id>
export LB_SCHEMA=factory
```

### SPARQL query returns empty results

Check that the supplier you're querying actually exists in the graph:

```bash
python kg_sparql.py --step list-suppliers
```

This lists all suppliers in the graph. Pick one that has parts, then retry.

If no suppliers have parts, the bom_edge or part_supplier relationship might not have been loaded
correctly. See [Build a knowledge graph](../kg-build/) FAQ for troubleshooting.

### Why does SPARQL read backward?

[SPARQL](../../docs/glossary.md) patterns use [RDF](../../docs/glossary.md)'s subject-predicate-object triple notation, which can feel backward
compared to SQL. A SPARQL pattern:

## Concept clarifications

### Why does SPARQL read backward?

SPARQL patterns use RDF's subject-predicate-object triple notation, which can feel backward
compared to SQL. A SPARQL pattern:

```sparql
?product contains ?part
```

means "bind ?product to a subject, ?part to an object, where the predicate is contains." In
subject-verb-object English, this is "(subject) contains (object)," which is natural.

Sometimes the vocabulary in the graph follows the object-subject convention (e.g.
`?part supplied_by ?supplier`), which also reads naturally in English. The important thing is
consistency: define your predicates (relationship names) to be readable.

### How is SPARQL performance on large graphs?

For graphs in memory (rdflib), performance is good up to tens of millions of triples if you're
careful with queries. For larger graphs, use a purpose-built triple store like Apache Jena or
AllegroGraph, which uses disk-based indexes and query optimization.

### Can SPARQL do everything SQL does?

Almost. [SPARQL](../../docs/glossary.md) supports:
- Patterns (like SELECT ... WHERE in SQL)
- Filtering (WHERE clauses)
- Aggregation (GROUP BY, COUNT, SUM)
- Sorting (ORDER BY)
- Optional relationships (OPTIONAL keyword, like LEFT JOIN)
- Union (UNION keyword)

SPARQL is less commonly used for complex analytics (like window functions) and doesn't have some
of SQL's procedural features (triggers, stored procedures). For most graph queries, SPARQL is as
expressive as SQL.

### When should I use SPARQL instead of SQL?

Use SPARQL when:
- Your domain is naturally a graph of relationships (supply chains, knowledge bases, genealogies).
- You have multi-hop queries that would require many self-joins in SQL.
- You want to add inference rules that derive new facts (next journey).

Use SQL when:
- Your data is naturally tabular (transactions, time-series, financial records).
- You need complex aggregations, analytics, or statistical functions.
- Your team is already expert in SQL.

For the factory, BOM and supply-chain questions are natural graphs; sensor telemetry and work-order scheduling are better handled with SQL. Use the right tool for the domain.

## Tracing and debugging

To see what triples the script loaded, add `--verbose`:

```bash
python kg_sparql.py --verbose
```

To see the internal SPARQL query the script generates:

```bash
python kg_sparql.py --step multi-hop --verbose
```

This prints the exact SPARQL query text before running it, so you can debug patterns or verify
you're asking what you think you're asking.

To compare SQL and SPARQL directly:

```bash
python kg_sparql.py --step sql --show-both
```

This prints both the SPARQL query and the equivalent SQL, then runs both and shows results side
by side.
