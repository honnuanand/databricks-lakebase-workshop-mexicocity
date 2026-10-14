# Infer and derive facts, expected results

Use this to check your run. Your product and part counts depend on the bank seed data you
loaded, but the inference chain and result shapes should match.

## Step 2, define a simple rule

The script prints:

```text
Rule defined: if (product contains part) and (part recalled) then (product affected_by_recall)
Rule added to graph.
```

## Step 3, assert a recalled part

```text
Marked PT-BEARING-6204 as recalled.
```

## Step 4, query before inference

Running `python kg_infer.py --step query-before` shows:

```text
Products affected (before inference): []
```

No products are marked as affected because you haven't asserted any directly, only that one part
is recalled.

## Step 5, apply entailment

Running `python kg_infer.py --step entail` shows:

```text
Entailment applied.
New triples inferred: 3
```

The number depends on how many products contain the recalled part, directly or indirectly.

## Step 6, query after inference

Running `python kg_infer.py --step query-after` shows:

```text
Products affected (after inference):
  FUND-GROWTH-A
  PRD-MOTOR-ASSEMBLY-2HP
  PRD-PUMP-SERIES-A
```

These are all products that contain the recalled part (directly or in a subassembly). The graph
inferred them.

## Step 7, multi-rule entailment

Running `python kg_infer.py --step rule-chain` shows:

```text
Chain rule defined: if (assembly part_of product) and (part recalled) then (assembly affected_by_recall)
Entailment applied.
New triples inferred (chain): 2
```

If your BOM has assemblies (parts that are themselves part of larger products), the chain rule
derives that those assemblies are also affected.

## Full run output

Running the script end to end:

```text
Loading graph...
  Loaded 250 triples

Rule 1: part recalled -> product affected
  Rule defined.

Mark PT-BEARING-6204 as recalled.

Products affected (before inference): []

Applying entailment (rule 1)...
  Inferred 3 new triples.

Products affected (after inference):
  FUND-GROWTH-A
  PRD-MOTOR-ASSEMBLY-2HP
  PRD-PUMP-SERIES-A

Chain rule: affected parts -> affected assemblies
  Rule defined.

Applying entailment (rule 2)...
  Inferred 2 new triples.

Final affected products:
  FUND-GROWTH-A
  PRD-MOTOR-ASSEMBLY-2HP
  PRD-PUMP-SERIES-A
  PRD-TOP-LEVEL-ASSEMBLY

Done. Inference complete.
```

## The numbers that matter

| What | Expected | Why it matters |
| ---- | -------- | -------------- |
| triples before entailment | 250+ | the base graph |
| triples inferred by one rule | 1-10 | depends on BOM fanout (how many products contain the part) |
| query latency after entailment | <20 ms | reasoning adds overhead, but still fast for factory-scale graphs |
| rule chaining depth | 2-5 levels | deeper chains (part → subassembly → assembly → product) catch more affected items |

> **Note**
> For production use, entailment can be expensive if you have many rules and a large graph.
> Options include: compute entailment once and persist the results (materialization), use a
> more efficient reasoner (e.g., Apache Jena), or limit rule depth. For this workshop, we
> demonstrate the concept with a small, in-memory graph.
