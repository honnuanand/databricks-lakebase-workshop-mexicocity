# Query a knowledge graph with SPARQL, FAQ

## Common errors and fixes

### `ModuleNotFoundError: No module named 'rdflib'`

Install rdflib:

```bash
pip install rdflib
```

If you're on a Databricks-managed laptop and the default PyPI is blocked, use your organization's
internal proxy index for the install.

### `Missing required env var LB_PROFILE`

Set your environment variables (see [`../../00-setup/auth.md`](../../00-setup/auth.md)):

```bash
export LB_PROFILE=<your-profile>
export LB_PROJECT=<project-id>
export LB_BRANCH=<branch-id>
export LB_SCHEMA=bank
```

### SPARQL query returns empty results

Check that the counterparty you're querying actually exists in the graph:

```bash
python kg_sparql.py --step list-counterparties
```

This lists all counterparties in the graph. Pick one that trades instruments, then retry.

If no counterparties trade instruments, the holding or trade_counterparty relationship might not
have been loaded correctly. See [Build a knowledge graph](../kg-build/) FAQ for troubleshooting.

## Concept clarifications

### Why does SPARQL read backward?

[SPARQL](../../docs/glossary.md) patterns use [RDF](../../docs/glossary.md)'s subject-predicate-object triple notation, which can feel backward
compared to SQL. A SPARQL pattern:

```sparql
?fund holds ?instrument
```

means "bind ?fund to a subject, ?instrument to an object, where the predicate is holds." In
subject-verb-object English, this is "(subject) holds (object)," which is natural.

Sometimes the vocabulary in the graph follows the object-subject convention (e.g.
`?instrument traded_by ?counterparty`), which also reads naturally in English. The important thing
is consistency: define your predicates (relationship names) to be readable.

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
- Transitive property paths (the `+` and `*` operators, like a recursive CTE)
- Optional relationships (OPTIONAL keyword, like LEFT JOIN)
- Union (UNION keyword)

SPARQL is less commonly used for complex analytics (like window functions) and doesn't have some
of SQL's procedural features (triggers, stored procedures). For most graph queries, SPARQL is as
expressive as SQL.

### When should I use SPARQL instead of SQL?

Use SPARQL when:
- Your domain is naturally a graph of relationships (holdings trees, counterparty networks, ownership chains).
- You have multi-hop queries that would require recursion or many self-joins in SQL.
- You want to add inference rules that derive new facts (next journey).

Use SQL when:
- Your data is naturally tabular (transactions, time-series, ledgers).
- You need complex aggregations, analytics, or statistical functions.
- Your team is already expert in SQL.

For the bank, holdings and counterparty-exposure questions are natural graphs; transaction
telemetry and settlement scheduling are better handled with SQL. Use the right tool for the domain.

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
