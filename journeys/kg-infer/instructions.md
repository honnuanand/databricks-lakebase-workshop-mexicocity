# Infer and derive facts, instructions

Build on the graph from the previous journeys, or run this script to rebuild it. If you haven't
done [`../../00-setup/`](../../00-setup/), do that first; you need `LB_PROFILE`, `LB_PROJECT`,
`LB_BRANCH`, and `LB_SCHEMA` set.

Everything here is in a single script: [`../../common/scripts/kg_infer.py`](../../common/scripts/kg_infer.py).
You can run it end to end, or follow the steps by hand.

## Run it end to end

```bash
cd common/scripts
python kg_infer.py
```

This builds the graph, defines inference rules, and shows derived facts. Read on for what each
step does; expected output is in [`expected.md`](expected.md).

## Or step through it by hand

### Step 1, load the graph

```bash
python kg_infer.py --step load
```

This loads the same BOM, supplier, and machine relationships from Lakebase.

### Step 2, define a simple rule

Define the rule: "if a part is recalled, and a product contains that part, then the product is
affected by the recall."

```bash
python kg_infer.py --step rule-simple
```

In RDF/OWL logic (using rdflib's forward-chaining rules):

```python
rule = rdflib.plugin.get('rules:BFPR', rdflib.plugin.Plugin)(graph)
rule += rdflib.plugin.get('rules:BFPR', rdflib.plugin.Plugin).Rule(
    "(?product contains ?part) (?part recalled true) -> (?product affected_by_recall true)"
)
```

The script prints the rule being added.

### Step 3, assert a recalled part

Mark a specific part as recalled:

```bash
python kg_infer.py --step recall-part
```

The script adds a triple:

```
(PT-BEARING-6204, recalled, true)
```

### Step 4, query for affected products (without inference)

Before applying the rule, ask: "which products are affected?" The answer is empty, because you
never explicitly marked any product as affected.

```bash
python kg_infer.py --step query-before
```

Output:

```text
Products affected (before inference): []
```

### Step 5, apply entailment

Now apply the inference rule. The graph computes all logical consequences of the facts you
stated plus the rules you defined.

```bash
python kg_infer.py --step entail
```

The script prints how many new triples were derived. For a single recalled part in a BOM with
multiple products containing it, you'll see 1-5 new triples depending on the graph depth.

### Step 6, query for affected products (after inference)

Now ask the same question:

```bash
python kg_infer.py --step query-after
```

Output:

```text
Products affected (after inference):
  PRD-GEARBOX-X1
  PRD-MOTOR-ASSEMBLY-2HP
```

These are the products inferred to be affected because they contain the recalled part.

### Step 7, multi-rule entailment

Add a second rule: "if a product is part of a larger assembly, and the product is affected, then
the assembly is affected."

```bash
python kg_infer.py --step rule-chain
```

Now apply entailment again. The graph will chain the rules: recalled part → product affected →
assembly affected.

## What you just did

You defined business logic as rules on the graph, then let the graph reason about your
manufacturing data to derive conclusions you never explicitly stored. Compare your output to
[`expected.md`](expected.md); if anything went wrong, check [`faq.md`](faq.md).
