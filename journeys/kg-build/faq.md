# Build a knowledge graph, FAQ

## Common errors and fixes

### `ModuleNotFoundError: No module named 'rdflib'`

The rdflib library isn't installed. Install it:

```bash
pip install rdflib
```

If you're on a Databricks-managed laptop and the default PyPI is blocked, use your organization's
internal proxy index for the install.

### `Missing required env var LB_PROFILE`

The script can't connect to Lakebase because your environment variables aren't set. See
[`../../00-setup/auth.md`](../../00-setup/auth.md) to set:

```bash
export LB_PROFILE=<your-profile>
export LB_PROJECT=<project-id>
export LB_BRANCH=<branch-id>
export LB_SCHEMA=bank
```

Then run the script again.

### `table "bank.holding" does not exist`

The bank schema hasn't been loaded yet. Run [`../../00-setup/`](../../00-setup/) to provision
the instance, project, and load the bank schema.

### Graph query returns empty

If the query returns no results, the fund or relationship you're querying may not exist
in your bank data. Check what funds are in the graph:

```bash
python kg_build.py --step list-funds
```

This prints all funds in the graph. Pick one that exists and retry the query.

## Concept clarifications

### Why RDF and not just SQL?

SQL is excellent for relational queries over tabular data. But when you have relationships that
traverse multiple steps (fund to sleeve to instrument to counterparty), or when you want to add
rules that derive new facts, a graph representation makes the structure explicit.

[Resource Description Framework](../../docs/glossary.md) (RDF) also separates the *schema* from the *data*: you can add new predicates (relationships) or
nodes without migrating table schemas. For a bank, this is useful when you add a new type
of relationship (e.g. an instrument was `rated_by` a credit agency) without altering the
operational database.

### What does "triple" mean?

A triple is (subject, predicate, object). Example: (Alice, knows, Bob). In the bank:
(INS-AAPL, traded_by, CP-GOLDMAN).

Every fact in an RDF graph is a triple. By composing triples, you build a graph. A SPARQL query
navigates those triples to find patterns.

### Is the graph always in memory?

Yes, for this workshop. rdflib loads the entire graph into RAM. For a bank with thousands of
instruments and counterparties, that's typically under 100 MB. For production graphs with millions
of triples, you'd use a dedicated triple store that stores on disk and indexes for fast lookup.

### Why not use a SQL recursive CTE?

You *can* use a recursive CTE for holdings-tree queries (see [`../../journeys/pg-sql-parity/`](../../journeys/pg-sql-parity/) for that
pattern). The graph approach shines when you have multiple types of relationships (holdings,
counterparties, branches, case notes) and want to ask cross-cutting questions. It also makes it
easier to add inference rules (next journey).

## Tracing and debugging

To see what triples the script loaded, add the `--verbose` flag:

```bash
python kg_build.py --verbose
```

This prints every triple as it's added, so you can see the structure being built. For large
graphs this produces a lot of output; use it to spot issues with malformed URIs or missing data.

To inspect the graph structure:

```bash
python kg_build.py --step inspect
```

This prints a summary: node counts, predicate counts, and sample triples, so you can verify the
graph was built correctly.
