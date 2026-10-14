# Operational vectors, expected results

Use this to check your run. The exact similarity scores depend on how the embeddings are
generated; the *shape* is what matters: you can embed instruments, query by similarity, and get
ranked results in a single SQL statement.

**An honesty note up front.** This journey embeds each instrument with a *deterministic hash* of
its text (`name kind spec`), not a real embedding model. A hash is reproducible and needs no model
call, which is why the workshop uses it, but it carries no financial meaning: the resulting
"similarity" ranking is an artifact of hashing, not a judgement that two securities actually
resemble each other. So do not expect "AAPL and MSFT come back as the closest pair" here, even
though they are the two tech equities. What you *are* verifying is the mechanism, store a vector on
the row, rank the rest with `<=>` in one SQL statement. Swap the hash for a real embedding model
(see "From the field" below) and the same query returns semantically meaningful neighbours.

## Step 1, instruments table

```text
('INS-AAPL', 'Apple Inc')
('INS-CASH-USD', 'US Dollar Cash')
('INS-MSFT', 'Microsoft Corp')
('INS-SLEEVE-EQ', 'Equity Sleeve')
('INS-UST-10Y', 'US Treasury 10Y')
```

The bank seed has 5 instruments: two tech equities (AAPL, MSFT), a cash position, an equity-sleeve
ETF, and a 10-year Treasury bond. Each has a JSONB `spec` (ticker, sector, beta, tenor, coupon).

## Step 2, pgvector extension

```text
Extension 'vector' created
```

Extension is installed.

## Step 3, embedding column

```text
Column 'embedding' added to bank.instrument
```

A 768-dimensional `vector` column was added to the instrument table.

## Step 4, embeddings populated

```text
Embedding 5 instruments:
  INS-AAPL: embedded
  INS-CASH-USD: embedded
  INS-MSFT: embedded
  INS-SLEEVE-EQ: embedded
  INS-UST-10Y: embedded
```

All 5 instruments now have 768-dimensional embedding vectors.

## Step 5, similarity search

Query: find the instruments most similar to `INS-AAPL` by cosine similarity (`<=>`):

```text
Running similarity search:
  Reference instrument: INS-AAPL
  Top comparable instruments:
    1. INS-UST-10Y: similarity=0.11 (US Treasury 10Y, bond)
    2. INS-SLEEVE-EQ: similarity=0.03 (Equity Sleeve, etf)
    3. INS-MSFT: similarity=-0.09 (Microsoft Corp, equity)
    4. INS-CASH-USD: similarity=-0.22 (US Dollar Cash, cash)
```

The ranking and the exact scores will differ from run to run only if you change the embedding
method. With the hash embedding they are stable but, as noted above, financially arbitrary: here
the Treasury happens to hash closest to Apple. The important shapes are:
- Four rows come back (every instrument except the reference itself), ranked by similarity.
- The whole ranking is one SQL statement against the same table that holds your positions.

## Step 6, HNSW index

```text
HNSW index created on embedding column
```

Index was created. On a 5-row table the index overhead is invisible, but for millions of vectors
HNSW keeps lookups fast.

## Full run

Running `python pg_vector.py` with no arguments prints the whole story:

```text
Checking instrument table:
  Total instruments: 5
  Sample instruments:
    - INS-AAPL: Apple Inc
    - INS-CASH-USD: US Dollar Cash
    - INS-MSFT: Microsoft Corp
    - INS-SLEEVE-EQ: Equity Sleeve
    - INS-UST-10Y: US Treasury 10Y

Creating pgvector extension:
  Extension 'vector' created

Adding embedding column (768-dim):
  Column 'embedding' added to bank.instrument

Populating embeddings:
  Embedding 5 instruments:
    INS-AAPL: embedded
    INS-CASH-USD: embedded
    INS-MSFT: embedded
    INS-SLEEVE-EQ: embedded
    INS-UST-10Y: embedded

Running similarity search:
  Reference instrument: INS-AAPL
  Top comparable instruments:
    1. INS-UST-10Y: similarity=0.11 (US Treasury 10Y, bond)
    2. INS-SLEEVE-EQ: similarity=0.03 (Equity Sleeve, etf)
    3. INS-MSFT: similarity=-0.09 (Microsoft Corp, equity)
    4. INS-CASH-USD: similarity=-0.22 (US Dollar Cash, cash)

Creating HNSW index:
  HNSW index created on embedding column

Done. A single SQL query finds comparable instruments by similarity, no network hop.
```

## The numbers that matter

| What | Expected | Why it matters |
| ---- | -------- | -------------- |
| pgvector extension creation | <100ms | one-time per branch |
| embedding population | ~10ms per instrument | batch updates, no round-trips |
| similarity search query latency | <10ms (with [Hierarchical Navigable Small Worlds](../../docs/glossary.md) (HNSW) index) | sub-transaction overhead |
| index creation time | ~100ms for 5 instruments | O(n log n); grows with data volume |
| cosine similarity range | -1.0 to 1.0 | 1 = identical direction, 0 = orthogonal, negative = opposite |

> **From the field**
> Production systems typically embed at scale using a batch job (once per day, or on instrument
> creation), then run similarity queries live. For this journey, we use deterministic
> "embeddings" (hashes) for reproducibility, which is why the rankings above are not financially
> meaningful. In production, use a real embedding model: Databricks Foundation Models (e.g.,
> `databricks-bge-large-en-v1.5`) or OpenAI's text-embedding-3-small. The pattern stays the same:
> call the model once per instrument (or update), store the vector on the table, query with `<=>`
> in SQL, and the neighbours it returns actually resemble the reference.
