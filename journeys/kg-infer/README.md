# Infer and derive facts with knowledge graph rules

> ## What you'll learn
>
> **Key takeaways**
>
> - Knowledge graphs support inference: state a rule (if X is true, then Y must be true), and the graph automatically derives new facts you never stored. This uses [RDF Schema](../../docs/glossary.md) (RDFS) or [Web Ontology Language](../../docs/glossary.md) (OWL) rules for reasoning.
> - A practical rule for a bank: "if an instrument is distressed, then every fund that holds it is exposed." State this once; the graph applies it to every fund, following holdings through sleeves transitively.
> - This is analogous to database triggers or materialized views, but expressed as declarative logic (RDF/OWL) instead of procedural code. The graph does the work.
>
> **You'll be able to:** define [RDFS](../../docs/glossary.md)/[OWL](../../docs/glossary.md) rules on your holdings graph, apply them to derive facts (like "fund X is exposed to a distressed instrument"), and see how entailment makes implicit relationships explicit.
>
> **Time:** about 20 minutes  ·  **Status:** live

## The scenario

An instrument, INS-QTZL, becomes distressed (say its issuer is downgraded, or the position is
flagged). Your system stored the structure: "INS-QTZL is held inside INS-SLEEVE-EQ, and
INS-SLEEVE-EQ is held by FUND-GROWTH-A." But nobody explicitly stored "FUND-GROWTH-A is exposed to
INS-QTZL."

That's an inference: if FUND-GROWTH-A holds INS-SLEEVE-EQ, and INS-SLEEVE-EQ holds INS-QTZL, and
INS-QTZL is distressed, then FUND-GROWTH-A must be exposed. A knowledge graph with rules lets you
state this logic once, then apply it automatically to all funds, no matter how deep the holding
sits.

This is the difference between a static fact database and a reasoning system. You store the
structure; the graph reasons about it. For a risk desk, "which funds are exposed to this name?" is
a question you want answered by entailment, not by a hand-written join that forgets about sleeves.

## What knowledge graph inference is

Inference in [RDF](../../docs/glossary.md) is based on formal logic. You define rules (called entailment or [RDFS](../../docs/glossary.md)/[OWL](../../docs/glossary.md)
rules), which are implications: if certain triples exist, then additional triples must logically
follow.

Example rule:

```text
if (X contains Y) and (Y is_distressed) then (X is_exposed)
```

Because `contains` is transitive (a fund that holds a sleeve, and the sleeve holds an instrument,
holds the instrument), the rule chains down the tree. When you add this rule and assert that
INS-QTZL is_distressed, the graph automatically infers that FUND-GROWTH-A is_exposed, without you
explicitly inserting that triple.

This is particularly powerful for exposure analysis, compliance, and impact assessment. You define
the business logic once; the graph applies it to all your data.

## The wow moment

You write a simple rule: "if an instrument is distressed, every fund holding it is exposed." Mark
one instrument distressed, an instrument that no fund holds *directly*, only through a sleeve. Run
a query for "which funds are exposed?" and FUND-GROWTH-A shows up even though you never stored that
link. The graph walked the holdings tree two hops down and inferred it.

## What you'll do

1. Build the graph from the previous journeys (or rebuild it here).
2. Define a simple rule: "fund contains instrument; instrument distressed → fund exposed."
3. Assert that one instrument (INS-QTZL) is distressed.
4. Query: "which funds are exposed to this instrument?" and see the inferred results.
5. See the entailment chain apply through the sleeve: instrument distressed → sleeve holding it
   reached → fund exposed.

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
For a bank, this is the foundation for exposure analysis, compliance, and what-if scenarios. You've
now seen the full progression: build the graph, query it, and reason over it to derive conclusions.
