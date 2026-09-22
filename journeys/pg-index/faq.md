# One engine, every index, FAQ

## "pgvector extension not available" or HNSW index fails

PGlite (WASM Postgres) and some managed instances don't ship pgvector by default. The script
handles this gracefully, if HNSW fails, you'll see a warning and the other five indexes will work.

If you're running on a full Postgres instance and want pgvector, install it:

```bash
CREATE EXTENSION IF NOT EXISTS vector WITH SCHEMA public
```

## The query didn't use the index I created

Indexes are hints; the planner ignores them if a full table scan is faster (e.g., on a 60k-row table,
sometimes a seq scan beats an index). This is correct behavior, the planner is doing its job.

To force the planner to use an index for testing, temporarily disable seq scans:

```bash
SET enable_seqscan = off
EXPLAIN ... your query ...
SET enable_seqscan = on
```

Don't leave this setting on in production; it breaks many legitimate queries.

## Can I have both BTREE and HASH on the same column?

Yes, but only one will be used per query. BTREE is more flexible (handles both equality and ranges);
HASH only handles equality. In practice, BTREE is almost always the better choice for a general index.
HASH is used primarily for specific patterns where it has a cost advantage.

## Why BRIN for timestamps, not BTREE?

Both can index timestamps. BRIN is *smaller* (useful on very large tables) and still fast for range scans
on natural time ordering. BTREE is more flexible. For 60k rows, either works; BRIN teaches the pattern:
for billion-row time-series tables, BRIN is often the better choice.

## This is a toy 60k-row table. Does this matter on real data?

Very much. On a 1 billion-row machine-telemetry table:
- A BRIN index on created_at might be 1 MB (vs 100 MB for BTREE).
- A GIN index on JSON specs makes "find all machines with spec.model = 'Press'" instant.
- An HNSW index on embeddings enables "find similar machines" predictions.

The planner still arbitrates all six indexes on every query. The principles don't change.

## Which index should I create first?

Start with queries. Index whatever columns appear in WHERE clauses, JOIN conditions, and ORDER BY.
Then:
1. BTREE for equality/range filters on relational columns (default choice).
2. HASH if you do only exact-match queries on integer columns (rare).
3. GIN for frequent JSON-containment filters.
4. BRIN for natural-order time-series.
5. GIST for spatial queries.
6. HNSW for vector similarity.

Most systems end up with BTREE on relational columns plus GIN or HNSW on special types.

## Can I have indexes on multiple columns?

Yes:

```sql
CREATE INDEX idx_composite ON table(col1, col2, col3)
```

Multi-column indexes are useful when queries filter on multiple columns together. The first
column is "most useful" for filtering; the rest help avoid fetching the table.

This journey shows single-column indexes per type for clarity; production systems often use multi-column.
