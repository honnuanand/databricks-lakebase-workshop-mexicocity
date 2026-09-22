# Infer and derive facts with knowledge graph rules

> ## What you'll learn
>
> **Key takeaways**
>
> - Knowledge graphs support inference: state a rule (if X is true, then Y must be true), and the graph automatically derives new facts you never stored.
> - A practical rule for manufacturing: "if a part is recalled, then all products containing that part are affected." State this once; the graph applies it to every product.
> - This is analogous to database triggers or materialized views, but expressed as declarative logic (RDF/OWL) instead of procedural code. The graph does the work.
>
> **You'll be able to:** define RDFS/OWL rules on your manufacturing graph, apply them to derive facts (like "product X is affected by recall"), and see how entailment makes implicit relationships explicit.
>
> **Time:** about 20 minutes  ·  **Status:** live

## The scenario

A part, PT-BEARING-6204, is recalled due to a defect. Your system stored: "PT-BEARING-6204 is
in bom_edge as child of PRD-GEARBOX-X1." But nobody explicitly stored "PRD-GEARBOX-X1 is
affected by the recall."

That's an inference: if PRD-GEARBOX-X1 contains PT-BEARING-6204, and PT-BEARING-6204 is recalled,
then PRD-GEARBOX-X1 must be affected. A knowledge graph with rules lets you state this logic
once, then apply it automatically to all products.

This is the difference between a static fact database and a reasoning system. You store the
structure; the graph reasons about it.

## What knowledge graph inference is

Inference in RDF is based on formal logic. You define rules (called entailment or RDFS/OWL
rules), which are implications: if certain triples exist, then additional triples must logically
follow.

Example rule:

```text
if (X contains Y) and (Y is_recalled) then (X is_affected_by_recall)
```

When you add this rule to the graph and assert that PT-BEARING-6204 is_recalled, the graph
automatically infers that PRD-GEARBOX-X1 is_affected_by_recall, without you explicitly inserting
that triple.

This is particularly powerful for supply-chain analysis, compliance, and impact assessment. You
define the business logic once; the graph applies it to all your data.

## The wow moment

You write a simple rule: "if a part is recalled, all products containing it are affected." Add
one recalled part to the graph. Run a query for "which products are affected?" and see products
show up in the results that you never explicitly marked as affected. The graph inferred it.

## What you'll do

1. Build the graph from the previous journeys (or rebuild it here).
2. Define a simple rule: "part → contains → product; part is recalled → product is affected."
3. Assert that one part is recalled.
4. Query: "which products are affected by this recall?" and see the inferred results.
5. Add a second rule and watch the entailment chain apply: part recalled → subassembly affected
   → finished product affected.

Full copy-paste steps are in [`instructions.md`](instructions.md); expected output is in
[`expected.md`](expected.md).

## Prerequisites

Finish [`../../00-setup/`](../../00-setup/) so you have a branch and can connect. Complete
[Build a knowledge graph](../kg-build/) and [Query with SPARQL](../kg-sparql/) first to
understand the graph structure; this journey layers rules on top of it.

Install rdflib:

```bash
pip install rdflib
```

## Wrapping up

Inference is the final piece of knowledge graphs: structure + relationships + logic = reasoning.
For manufacturing, this is the foundation for impact analysis, compliance, and what-if
scenarios. You've now seen the full progression: build the graph, query it, and reason over it
to derive conclusions.
