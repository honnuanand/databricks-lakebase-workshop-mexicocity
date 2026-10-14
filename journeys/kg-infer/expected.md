# Infer and derive facts, expected results

Use this to check your run. Your fund and instrument counts depend on the bank seed data you
loaded, but the inference chain and result shapes should match. The numbers below are for the
default bank seed (2 funds, 5 instruments, 5 holding edges).

## Step 2, define the simple rule

The script prints:

```text
Defining rule: instrument distressed → fund exposed

    Rule: if (fund holds instrument) and (instrument distressed) then (fund exposed)

    In logic:
        (?fund bank:contains ?instrument) AND (?instrument bank:distressed true)
            => (?fund bank:exposed true)

    'contains' is transitive here: a fund that holds a sleeve, and the sleeve holds the
    instrument, means the fund holds the instrument. So the rule chains down the tree.
```

## Step 3, assert a distressed instrument

```text
Marking INS-AAPL as distressed...
  Asserted: INS-AAPL distressed=true
```

## Step 4, query before inference

Running `python kg_infer.py --step query-before` shows:

```text
Funds exposed: []
```

No funds are marked exposed because you haven't asserted any directly, only that one instrument is
distressed.

## Step 5, apply entailment

Running `python kg_infer.py --step entail` shows:

```text
Applying entailment...
  Triples before: 13
  Triples after: 14
  Inferred: 1 new triples
```

One new triple: FUND-GROWTH-A is exposed. The graph reached INS-AAPL by walking FUND-GROWTH-A →
INS-SLEEVE-EQ → INS-AAPL. FUND-INCOME-B holds nothing, so nothing is inferred for it. The count of
inferred triples depends on how many funds hold the distressed instrument, directly or through a
sleeve.

## Step 6, query after inference

Running `python kg_infer.py --step query-after` shows:

```text
Funds exposed:
  FUND-GROWTH-A
```

FUND-GROWTH-A was inferred to be exposed because it holds INS-AAPL two hops down, through the
equity sleeve. The graph inferred it; you never stored that link.

## Step 7, the entailment chain

Running `python kg_infer.py --step rule-chain` prints the chaining rule in words:

```text
Defining chain rule: exposed sleeve → exposed fund

        Rule: if (fund contains sleeve) and (sleeve exposed) then (fund exposed)
```

The chain is exactly what Step 5 computed: the transitive `contains` walk *is* the multi-hop rule.
INS-AAPL distressed → INS-SLEEVE-EQ is on the path → FUND-GROWTH-A exposed.

## Full run output

Running the script end to end:

```text
Loading graph...
  Loaded 12 triples

Defining rule: instrument distressed → fund exposed
  [rule text]

Marking INS-AAPL as distressed...
  Asserted: INS-AAPL distressed=true

Query (before inference): which funds are exposed?
  Funds exposed: []

Applying entailment...
  Triples before: 13
  Triples after: 14
  Inferred: 1 new triples

Query (after inference): which funds are exposed?
  Funds exposed:
    FUND-GROWTH-A
```

## The numbers that matter

| What | Expected | Why it matters |
| ---- | -------- | -------------- |
| triples before entailment | 12 (default seed) | the base graph (funds + instruments + holding edges) |
| triples inferred by the rule | 1 (default seed) | depends on holdings fanout (how many funds reach the instrument) |
| query latency after entailment | <20 ms | reasoning adds overhead, but still fast at this scale |
| entailment depth | transitive (unbounded) | deeper holding trees (fund → sleeve → sub-sleeve → instrument) are all caught by the recursive walk |

> **Note**
> For production use, entailment can be expensive if you have many rules and a large graph.
> Options include: compute entailment once and persist the results (materialization), use a
> more efficient reasoner (e.g., Apache Jena), or limit rule depth. For this workshop, we
> demonstrate the concept with a small, in-memory graph.
