# Build a knowledge graph, expected results

Use this to check your run. Your exact triple counts may vary slightly depending on the bank
data you loaded, but the structure and query shapes should match.

## Step 1, load the holdings tree as triples

Running the full script prints a summary of triples loaded. With the standard workshop seed you
should see:

```text
Loaded 28 triples:
  - 2 funds
  - 5 instruments
  - 5 holdings
  - 3 counterparties
  - 3 traded_by_edges
  - 3 branches
  - 2 booked_at_edges
```

The exact counts depend on your bank seed data, but you should see a few dozen triples: each
instrument contributes a name and a kind triple, each fund, branch, and counterparty a name
triple, plus the holdings, traded_by, and booked_at edges.

## Step 2, query the holdings tree

Running `python kg_build.py --step query` (or the full script) shows:

```text
Query: which instruments does FUND-GROWTH-A hold directly?
  INS-CASH-USD
  INS-MSFT
  INS-SLEEVE-EQ
```

These are the direct children of FUND-GROWTH-A in the holdings tree. Note that `INS-SLEEVE-EQ` is
itself a sub-sleeve that holds `INS-AAPL` and `INS-UST-10Y`; the direct query stops at the first
level, while the SPARQL journey walks the whole tree.

The traversal is over the graph's `holds` relationship, equivalent to this [SPARQL](../../docs/glossary.md):

```sparql
SELECT ?instrument WHERE {
  ?fund <http://bank.local/holds> ?instrument .
  FILTER (?fund = <http://bank.local/FUND-GROWTH-A>)
}
```

## Step 3, equivalent SQL

The script shows the same query in SQL:

```text
SQL equivalent:
SELECT instrument_id FROM bank.holding WHERE parent_id = 'FUND-GROWTH-A'
```

Both return the same instrument IDs. In this simple case they're equally readable. But when you
ask a multi-hop question like "which funds hold an instrument traded by CP-GOLDMAN?", the SQL joins
grow and have to walk the sleeve nesting, while the graph query stays shallow.

## Full run output

Running the whole script end to end produces output like:

```text
Loading graph...
  Loaded 28 triples
  Loaded 2 funds
  Loaded 5 instruments
  Loaded 5 holdings
  Loaded 3 counterparties
  Loaded 3 traded_by edges
  Loaded 3 branches
  Loaded 2 booked_at edges

Querying: which instruments does FUND-GROWTH-A hold directly?
  INS-CASH-USD
  INS-MSFT
  INS-SLEEVE-EQ

Equivalent SQL:
SELECT instrument_id FROM bank.holding WHERE parent_id = 'FUND-GROWTH-A'
  Result: [('INS-CASH-USD',), ('INS-SLEEVE-EQ',), ('INS-MSFT',)]

Done. Graph ready for SPARQL queries.
```

## The numbers that matter

| What | Expected | Why it matters |
| ---- | -------- | -------------- |
| triples loaded | 25-35 | reflects your bank's holdings depth and counterparty relationships |
| instruments per fund | typically 2-4 direct | holdings complexity; deeper sleeves mean richer exposure analysis |
| counterparties in graph | 3 | counterparty network density |
| time to load | under 1 second | rdflib is fast for small to medium graphs |

> **Note**
> For production graphs with millions of triples, you'd use a purpose-built triple store
> (Apache Jena, RDF4J, or a managed service). For this workshop, in-memory rdflib is sufficient
> and teaches the mechanics directly.
