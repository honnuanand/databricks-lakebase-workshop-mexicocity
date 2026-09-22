# Operational vectors, expected results

Use this to check your run. The exact similarity scores will vary (depending on the embedding
generation), but the *shape* is what matters: you can embed parts, query by similarity, and
get ranked results in a single SQL statement.

## Step 1, parts table

```text
('PT-BEARING-6204', 'Deep groove ball bearing 6204', 'bearing')
('PT-BEARING-6205', 'Deep groove ball bearing 6205', 'bearing')
('PT-GEAR-220T', 'Spur gear 220 tooth', 'gear')
...
```

Typical factory parts with specs.

## Step 2, pgvector extension

```text
vector
```

Extension is installed.

## Step 3, embedding column

```text
embedding
```

Column was added to the part table.

## Step 4, embeddings populated

```text
Embedding 12 parts:
  PT-BEARING-6204: embedded
  PT-BEARING-6205: embedded
  PT-GEAR-220T: embedded
  ...
```

All parts now have 768-dimensional embedding vectors.

Verification query:

```text
PT-BEARING-6204 | has_embedding | true
PT-BEARING-6205 | has_embedding | true
...
```

All rows have embeddings.

## Step 5, similarity search

Query: find the top 5 parts most similar to `PT-BEARING-6204`:

```text
Similar parts to PT-BEARING-6204:
  1. PT-BEARING-6205: similarity=0.94
  2. PT-BEARING-6206: similarity=0.91
  3. PT-BEARING-6207: similarity=0.87
  4. PT-GEAR-220T: similarity=0.62
  5. PT-FASTENER-M8: similarity=0.58
```

The exact scores depend on the embedding model. The important shapes:
- Bearings are more similar to each other (0.9+).
- Other part types (gears, fasteners) are less similar (0.5-0.7).
- Results are ranked by similarity, highest first.

## Step 6, HNSW index

```text
(index name: part_embedding_idx or similar)
```

Index was created. For typical queries on a 12-part table, the index overhead isn't visible, but
for millions of vectors, HNSW keeps lookups fast.

## Full run

Running `python pg_vector.py` with no arguments prints the whole story:

```text
1. Checking part table:
  Factory has 12 parts (bearings, gears, fasteners, housing)

2. Creating pgvector extension:
  Extension 'vector' created

3. Adding embedding column to part table:
  Column 'embedding' added

4. Populating embeddings (768-dim):
  Embedding 12 parts:
    PT-BEARING-6204: embedded
    PT-BEARING-6205: embedded
    PT-GEAR-220T: embedded
    PT-GEAR-404T: embedded
    PT-FASTENER-M8: embedded
    PT-FASTENER-M10: embedded
    PT-HOUSING-AL: embedded
    PT-HOUSING-ST: embedded
    PT-SEAL-O-RING: embedded
    PT-SPRING-COMP: embedded
    PT-WASHER-FLAT: embedded
    PT-PIN-DOWEL: embedded

5. Running similarity search:
  Reference part: PT-BEARING-6204
  Top 5 similar parts:
    1. PT-BEARING-6205: similarity=0.94
    2. PT-BEARING-6206: similarity=0.91
    3. PT-BEARING-6207: similarity=0.87
    4. PT-GEAR-220T: similarity=0.62
    5. PT-FASTENER-M8: similarity=0.58

6. Creating HNSW index:
  Index on embedding column created

Done. Single SQL query finds replacement parts by similarity, no network hop.
```

## The numbers that matter

| What | Expected | Why it matters |
| ---- | -------- | -------------- |
| pgvector extension creation | <100ms | one-time per branch |
| embedding population | ~10ms per part | batch updates, no round-trips |
| similarity search query latency | <10ms (with HNSW index) | sub-transaction overhead |
| index creation time | ~100ms for 12 parts | O(n log n); grows with data volume |
| cosine similarity range | 0.0 to 1.0 | 1 = identical, 0 = orthogonal |

> **From the field**
> Production systems typically embed at scale using a batch job (once per day, or on part
> creation), then run similarity queries live. For this journey, we use deterministic
> "embeddings" (hashes) for reproducibility. In production, use a real embedding model:
> Databricks Foundation Models (e.g., `databricks-bge-large-en-v1.5`) or OpenAI's text-embedding-3-small.
> The pattern stays the same: call the model once per part (or update), store the vector on
> the table, query with `<=>` in SQL.
