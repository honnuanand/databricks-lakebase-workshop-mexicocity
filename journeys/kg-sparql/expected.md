# Query a knowledge graph with SPARQL, expected results

Use this to check your run. Your fund and counterparty lists depend on the bank seed data you
loaded, but the structure of the queries and results should match.

## Step 2, simple SPARQL query

Running `python kg_sparql.py --step simple-query` shows:

```text
SPARQL query: which instruments does FUND-GROWTH-A hold directly?
  INS-CASH-MXN
  INS-ZAFR
  INS-SLEEVE-EQ
```

These are the direct children of FUND-GROWTH-A in the holdings tree. `INS-SLEEVE-EQ` is itself a
sub-sleeve; the simple query stops at the first level.

## Step 3, multi-hop SPARQL query

Running `python kg_sparql.py --step multi-hop` shows the [SPARQL](../../docs/glossary.md) pattern result:

```text
SPARQL multi-hop query: which funds hold an instrument traded by CP-ALTAMAR?
  FUND-GROWTH-A
```

In the seed, CP-ALTAMAR trades INS-QTZL. INS-QTZL sits under INS-SLEEVE-EQ, which FUND-GROWTH-A
holds, so `holds+` reaches it and that fund comes back. FUND-INCOME-B holds nothing in the seed,
so it is not exposed.
The SPARQL pattern traverses:
  fund holds+ instrument
  instrument traded_by counterparty
  filter counterparty = CP-ALTAMAR

## Step 4, equivalent SQL

Running `python kg_sparql.py --step sql` shows:

```text
Equivalent SQL query:
WITH RECURSIVE tree(root_fund, node) AS (
    SELECT f.fund_id, f.fund_id FROM bank.fund f
  UNION ALL
    SELECT t.root_fund, h.instrument_id
    FROM tree t JOIN bank.holding h ON h.parent_id = t.node
)
SELECT DISTINCT t.root_fund
  FROM tree t
  JOIN bank.trade_counterparty tc ON tc.instrument_id = t.node
 WHERE tc.counterparty_id = 'CP-ALTAMAR'
   AND t.root_fund LIKE 'FUND-%'

  SQL Result: [('FUND-GROWTH-A',)]
```

Both queries return the same fund ID. The SPARQL version reads as a description of the
relationship chain; the SQL version is explicit about the recursion and the join.

## Step 5, aggregation query

Running `python kg_sparql.py --step aggregate` shows:

```text
SPARQL aggregation query: instruments per counterparty
  CP-CUMBRE: 1
  CP-MIRADOR: 1
  CP-ALTAMAR: 1
```

The SPARQL GROUP BY aggregates across all triples, counting distinct instruments per counterparty.
In the small seed each counterparty trades one instrument; with more `trade_counterparty` rows the
counts grow.

## Full run output

Running the script end to end (your triple count and ordering may vary slightly):

```text
Loading graph...
  Loaded 18 triples

SPARQL query: which instruments does FUND-GROWTH-A hold directly?
  INS-CASH-MXN
  INS-ZAFR
  INS-SLEEVE-EQ

SPARQL multi-hop query: which funds hold an instrument traded by CP-ALTAMAR?
  FUND-GROWTH-A

Equivalent SQL query:
  SQL Result: [('FUND-GROWTH-A',)]

Done. SPARQL queries complete.
```

## The numbers that matter

| What | Expected | Why it matters |
| ---- | -------- | -------------- |
| simple query latency | <5 ms | graph is indexed; queries are fast |
| multi-hop query latency | <10 ms | traversal across the holdings tree plus one edge is still sub-millisecond |
| funds exposed to one counterparty | 1-5 | typical portfolio distribution; the more holdings you load, the more funds each counterparty touches |
| result consistency | identical | SPARQL and SQL return the same fund IDs, proving correctness |

> **Note**
> SPARQL's power becomes evident with deeper graphs. A 10-hop question in SQL would be a 10-level
> recursion. In SPARQL, it's still a readable property path. For production use, consider a
> dedicated triple store optimized for deep traversals.
