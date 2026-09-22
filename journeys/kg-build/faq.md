# Build a knowledge graph, FAQ

## Common errors and fixes

### `ModuleNotFoundError: No module named 'rdflib'`

The rdflib library isn't installed. Install it:

```bash
pip install rdflib
```

If you're on a Databricks-managed laptop and the default PyPI is blocked, use the internal proxy:

```bash
pip install rdflib
```

### `Missing required env var LB_PROFILE`

The script can't connect to Lakebase because your environment variables aren't set. See
[`../../00-setup/auth.md`](../../00-setup/auth.md) to set:

```bash
export LB_PROFILE=<your-profile>
export LB_PROJECT=<project-id>
export LB_BRANCH=<branch-id>
export LB_SCHEMA=factory
```

Then run the script again.

### `table "factory.bom_edge" does not exist`

The factory schema hasn't been loaded yet. Run [`../../00-setup/`](../../00-setup/) to provision
the instance, project, and load the factory schema.

### Graph query returns empty

If the SPARQL query returns no results, the product or relationship you're querying may not exist
in your factory data. Check what products are in the graph:

```bash
python kg_build.py --step list-products
```

This prints all products in the graph. Pick one that exists and retry the query.

## Concept clarifications

### Why RDF and not just SQL?

SQL is excellent for relational queries over tabular data. But when you have relationships that
traverse multiple steps (product → part → supplier → logistics), or when you want to add rules
that derive new facts, a graph representation makes the structure explicit.

[Resource Description Framework](../../docs/glossary.md) (RDF) also separates the *schema* from the *data*: you can add new predicates (relationships) or
nodes without migrating table schemas. For manufacturing, this is useful when you add a new type
of relationship (e.g. a part was `certified_for` an industry standard) without altering the
production database.

### What does "triple" mean?

A triple is (subject, predicate, object). Example: (Alice, knows, Bob). In manufacturing:
(PRD-GEARBOX-X1, contains, PT-BEARING-6204).

Every fact in an RDF graph is a triple. By composing triples, you build a graph. A SPARQL query
navigates those triples to find patterns.

### Is the graph always in memory?

Yes, for this workshop. rdflib loads the entire graph into RAM. For a factory with thousands of
parts and suppliers, that's typically under 100 MB. For production graphs with millions of
triples, you'd use a dedicated triple store that stores on disk and indexes for fast lookup.

### Why not use a SQL recursive CTE?

You *can* use a recursive CTE for BOM queries (see [`../../journeys/pg-sql-parity/`](../../journeys/pg-sql-parity/) for that
pattern). The graph approach shines when you have multiple types of relationships (BOM, suppliers,
machines, maintenance history) and want to ask cross-cutting questions. It also makes it easier to
add inference rules (next journey).

## Tracing and debugging

To see what triples the script loaded, add `--verbose` flag:

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
