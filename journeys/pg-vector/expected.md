# Operational vectors, expected results

Use this to check your run. The exact similarity scores will vary (depending on the embedding
generation), but the *shape* is what matters: you can embed instruments, query by similarity, and
get ranked results in a single SQL statement.

## Step 1, instruments table

```text
('INS-AAPL', 'Deep groove ball security 6204', 'security')
('INS-MSFT', 'Deep groove ball security 6205', 'security')
('INS-AAPL', 'Spur gear 220 tooth', 'gear')
...
```

Typical factory instruments with specs.

## Step 2, pgvector extension

```text
vector
```

Extension is installed.

## Step 3, embedding column

```text
embedding
```

Column was added to the instrument table.

## Step 4, embeddings populated

```text
Embedding 12 instruments:
  INS-AAPL: embedded
  INS-MSFT: embedded
  INS-AAPL: embedded
  ...
```

All instruments now have 768-dimensional embedding vectors.

Verification query:

```text
INS-AAPL | has_embedding | true
INS-MSFT | has_embedding | true
...
```

All rows have embeddings.

## Step 5, similarity search

Query: find the top 5 instruments most similar to `INS-AAPL`:

```text
Similar instruments to INS-AAPL:
  1. INS-MSFT: similarity=0.94
  2. INS-AAPL: similarity=0.91
  3. INS-AAPL: similarity=0.87
  4. INS-AAPL: similarity=0.62
  5. INS-AAPL: similarity=0.58
```

The exact scores depend on the embedding model. The important shapes:
- Bearings are more similar to each other (0.9+).
- Other instrument types (gears, fasteners) are less similar (0.5-0.7).
- Results are ranked by similarity, highest first.

## Step 6, HNSW index

```text
(index name: part_embedding_idx or similar)
```

Index was created. For typical queries on a 12-instrument table, the index overhead isn't visible, but
for millions of vectors, HNSW keeps lookups fast.

## Full run

Running `python pg_vector.py` with no arguments prints the whole story:

```text
1. Checking instrument table:
  Factory has 12 instruments (bearings, gears, fasteners, housing)

2. Creating pgvector extension:
  Extension 'vector' created

3. Adding embedding column to instrument table:
  Column 'embedding' added

4. Populating embeddings (768-dim):
  Embedding 12 instruments:
    INS-AAPL: embedded
    INS-MSFT: embedded
    INS-AAPL: embedded
    INS-AAPL: embedded
    INS-AAPL: embedded
    INS-AAPL: embedded
    INS-AAPL: embedded
    INS-AAPL: embedded
    INS-AAPL: embedded
    INS-AAPL: embedded
    INS-AAPL: embedded
    INS-AAPL: embedded

5. Running similarity search:
  Reference instrument: INS-AAPL
  Top 5 similar instruments:
    1. INS-MSFT: similarity=0.94
    2. INS-AAPL: similarity=0.91
    3. INS-AAPL: similarity=0.87
    4. INS-AAPL: similarity=0.62
    5. INS-AAPL: similarity=0.58

6. Creating HNSW index:
  Index on embedding column created

Done. Single SQL query finds comparable instruments by similarity, no network hop.
```

## The numbers that matter

| What | Expected | Why it matters |
| ---- | -------- | -------------- |
| pgvector extension creation | <100ms | one-time per branch |
| embedding population | ~10ms per instrument | batch updates, no round-trips |
| similarity search query latency | <10ms (with [Hierarchical Navigable Small Worlds](../../docs/glossary.md) (HNSW) index) | sub-transaction overhead |
| index creation time | ~100ms for 12 instruments | O(n log n); grows with data volume |
| cosine similarity range | 0.0 to 1.0 | 1 = identical, 0 = orthogonal |

> **From the field**
> Production systems typically embed at scale using a batch job (once per day, or on instrument
> creation), then run similarity queries live. For this journey, we use deterministic
> "embeddings" (hashes) for reproducibility. In production, use a real embedding model:
> Databricks Foundation Models (e.g., `databricks-bge-large-en-v1.5`) or OpenAI's text-embedding-3-small.
> The pattern stays the same: call the model once per instrument (or update), store the vector on
> the table, query with `<=>` in SQL.
