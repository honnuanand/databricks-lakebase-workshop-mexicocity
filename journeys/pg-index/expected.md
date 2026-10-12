# One engine, every index, expected results

Use this to check your run. Numbers are representative; your actual timings will vary.
The key: each query shows an Index in the EXPLAIN output.

## Setup

```text
Created account_index_demo with 60k rows and all data types
```

## Indexes created

```text
✓ BTREE index on account_id (relational lookups)
✓ HASH index on mcc (integer equality)
✓ GIN index on spec (JSON containment @>)
✓ BRIN index on opened_at (time-series range scans)
✓ GIST index on location (geospatial distance <->)
✓ HNSW index on embedding (vector similarity <=>)
```

## EXPLAIN results

Each query type uses its matching index:

```text
✓ BTREE     query uses index
✓ HASH      query uses index
✓ GIN       query uses index
✓ BRIN      query uses index
✓ GIST      query uses index
```

(HNSW skipped if pgvector not available on your instance.)

## Full run

```text
1. Creating demo table with every data type:
Created account_index_demo with 60k rows and all data types

2. Creating six index types:
✓ BTREE index on account_id (relational lookups)
✓ HASH index on mcc (integer equality)
✓ GIN index on spec (JSON containment @>)
✓ BRIN index on opened_at (time-series range scans)
✓ GIST index on location (geospatial distance <->)
✓ HNSW index on embedding (vector similarity <=>)

3. Running EXPLAIN to show planner chooses each index:

Explain shows which index each query uses:
  ✓ BTREE    query uses index
  ✓ HASH     query uses index
  ✓ GIN      query uses index
  ✓ BRIN     query uses index
  ✓ GIST     query uses index

✓ One table, every type. One engine, every index.
```

## The numbers that matter

| Index AM | Data type | Query pattern | Typical use |
| --------- | --------- | ------------- | ----------- |
| BTREE | relational | exact match / range | account IDs, codes, lookups |
| HASH | relational | exact match only | merchant category comparisons |
| GIN | JSONB | containment (@>) | searching account/product specs |
| BRIN | TIMESTAMP | range queries | time-series (accounts opened in date range) |
| GIST | geometry/geography | spatial distance (<->) | proximity queries |
| HNSW | vector | similarity (<=>) | account similarity search |

> **From the field**
> All six indexes exist on a single table. The planner chooses which to use (or none) based on the
> query. This is why Postgres scales to diverse workloads: it's not a "relational only" system or
> a "JSON store" or a "vector database", it's one engine with one planner that optimizes any
> combination. The indexes ensure performance; the planner ensures choice.
