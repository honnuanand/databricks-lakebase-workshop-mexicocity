# Infer and derive facts, FAQ

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

### Entailment produces no new triples

If the script says "inferred 0 triples," the rule may not have matched your graph structure. Check:

1. Does the distressed instrument actually exist in the graph?
   ```bash
   python kg_infer.py --step list-instruments
   ```
   Pick an instrument that exists and mark it distressed (edit `DISTRESSED` near the top of the
   script if you want a different one than INS-QTZL).

2. Does that instrument appear in any `holding` edges? If no fund holds it (directly or through a
   sleeve), the rule has nothing to infer from. The default INS-QTZL is held through INS-SLEEVE-EQ
   by FUND-GROWTH-A, so it does fire.

3. Is the rule pattern right? The script prints the rule (`--step rule-simple`) before applying it;
   check that it matches the triple pattern in your graph.

### `Missing required env var LB_PROFILE`

Set your environment variables (see [`../../00-setup/auth.md`](../../00-setup/auth.md)):

```bash
export LB_PROFILE=<your-profile>
export LB_PROJECT=<project-id>
export LB_BRANCH=<branch-id>
export LB_SCHEMA=bank
```

## Concept clarifications

### What's the difference between a rule and a query?

A *query* asks: "what triples match this pattern?" A *rule* says: "if these triples exist, then
these new triples logically follow."

After you apply a rule, those new triples become part of the graph. Future queries will see them
as if they were always there. Rules are a way to encode business logic and let the graph apply it
automatically.

### Is entailment the same as a SQL trigger?

Conceptually, yes. A trigger in SQL says "when X happens, do Y." A rule in [RDF](../../docs/glossary.md) says "if X is
true, then Y logically follows." The main differences:

- Triggers are procedural (imperative code); rules are declarative (logical statements).
- Triggers execute on specific events; rules are applied to the entire graph when you invoke
  entailment.
- Triggers can have side effects (updates, deletes); rule consequences are pure logical
  derivations (new triples).

For the banking use case, rules are cleaner: you state the exposure logic once, and it applies
consistently across all your holdings, however deeply nested.

### Can I define conditional rules?

Yes. Rules can include filters:

```
(?fund contains ?instrument) (?instrument high_yield true) -> (?fund flagged_for_review true)
```

This rule only fires for high-yield instruments. You can also combine multiple conditions:

```
(?fund contains ?instrument) (?instrument distressed true) (?fund mandate conservative) -> (?fund breach_candidate true)
```

### What happens if rules conflict?

[RDF](../../docs/glossary.md) entailment is monotonic: rules can only add new triples, never remove them. So conflicts
aren't possible in the traditional sense. However, you can have contradictory facts (e.g., an
instrument marked both performing and distressed). [OWL](../../docs/glossary.md) (the full ontology language) has consistency checking to
catch these; rdflib's basic inference doesn't. For production use, consider using a full OWL
reasoner if you need consistency validation.

### Performance: what's the cost of entailment?

For small graphs (thousands to tens of thousands of triples), entailment is fast (under a second).
For large graphs (millions of triples), it depends on rule complexity and graph structure. Options:

1. **Materialize results:** compute entailment once, store the inferred triples, then just query
   them (no repeated reasoning).
2. **Use a specialized reasoner:** Apache Jena, RDF4J, and others have optimized entailment
   engines.
3. **Limit rule depth:** avoid deep rule chains that require many iterations.

For this workshop, we're demonstrating the concept with a small graph.

## Tracing and debugging

To see the rule text:

```bash
python kg_infer.py --step rule-simple
```

To see the triple counts before and after entailment (how many new facts were inferred):

```bash
python kg_infer.py --step entail
```

It prints `Triples before`, `Triples after`, and `Inferred: N new triples`. To list the
instruments the graph knows about (so you can pick one to mark distressed):

```bash
python kg_infer.py --step list-instruments
```

To see the exposed funds after inference:

```bash
python kg_infer.py --step query-after
```
