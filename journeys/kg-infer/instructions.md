# Infer and derive facts, instructions

## How to run this journey

There are a few ways to work through the steps. Pick one:

- **Notebook, step by step (recommended for learning):** open [`kg_infer.ipynb`](kg_infer.ipynb) and run one cell at a time. Reading each result before the next step is where the learning happens.
- **In a Databricks workspace:** import [`kg_infer_databricks.py`](kg_infer_databricks.py) and run it cell by cell there.
- **By hand:** follow the numbered steps below, copying each command yourself.
- **Just see it work:** run `python kg_infer.py` from this folder to execute the whole thing at once. Fast, but you learn the most from the notebook.

Build on the graph from the previous journeys, or run this script to rebuild it. If you haven't
done [`../../00-setup/`](../../00-setup/), do that first; you need `LB_PROFILE`, `LB_PROJECT`,
`LB_BRANCH`, and `LB_SCHEMA` set.

Everything here is in a single script: [`./kg_infer.py`](./kg_infer.py).
You can run it end to end, or follow the steps by hand.

## Run it end to end

```bash
cd journeys/kg-infer
python kg_infer.py
```

This builds the graph, defines the inference rule, and shows the derived facts. Read on for what
each step does; expected output is in [`expected.md`](expected.md).

## Or step through it by hand

### Step 1, load the graph

```bash
python kg_infer.py --step load
```

This loads the funds, instruments, and holding edges from Lakebase. Each `holding` row becomes a
`contains` edge; a sleeve instrument that holds other instruments makes the graph a tree.

### Step 2, define the simple rule

Define the rule: "if an instrument is distressed, and a fund holds that instrument, then the fund
is exposed."

```bash
python kg_infer.py --step rule-simple
```

In [RDF](../../docs/glossary.md)/[OWL](../../docs/glossary.md) logic (forward-chaining):

```text
(?fund contains ?instrument) (?instrument distressed true) -> (?fund exposed true)
```

`contains` is transitive, so the rule chains down through sleeves. The script prints the rule.

### Step 3, assert a distressed instrument

Mark a specific instrument as distressed:

```bash
python kg_infer.py --step distress
```

The script adds a triple:

```
(INS-AAPL, distressed, true)
```

INS-AAPL is held only *through* INS-SLEEVE-EQ, not directly by any fund, so a naive one-hop lookup
would miss its exposure. That is the point.

### Step 4, query for exposed funds (without inference)

Before applying the rule, ask: "which funds are exposed?" The answer is empty, because you never
explicitly marked any fund as exposed.

```bash
python kg_infer.py --step query-before
```

Output:

```text
Funds exposed: []
```

### Step 5, apply entailment

Now apply the inference rule. The graph computes all logical consequences of the facts you stated
plus the rule you defined, walking `contains` transitively.

```bash
python kg_infer.py --step entail
```

The script prints how many new triples were derived. For INS-AAPL distressed in this holdings tree
you'll see 1 new triple (FUND-GROWTH-A exposed).

### Step 6, query for exposed funds (after inference)

Now ask the same question:

```bash
python kg_infer.py --step query-after
```

Output:

```text
Funds exposed:
  FUND-GROWTH-A
```

FUND-GROWTH-A is inferred to be exposed because it holds INS-AAPL through INS-SLEEVE-EQ.
FUND-INCOME-B holds nothing in this tree, so it stays unexposed, the correct contrast.

### Step 7, the entailment chain

The `--step rule-chain` option prints the chaining rule in words:

```bash
python kg_infer.py --step rule-chain
```

The chain is already what Step 5 computed: instrument distressed → the sleeve that holds it is on
the path → the fund that holds the sleeve is exposed. The transitive walk *is* the multi-hop rule.

## What you just did

You defined business logic as a rule on the graph, then let the graph reason about your holdings
data to derive an exposure you never explicitly stored, following the tree through a sleeve.
Compare your output to [`expected.md`](expected.md); if anything went wrong, check [`faq.md`](faq.md).
