# Search, three ways, FAQ

## It failed with a "refresh token" or authentication error

Your Databricks login expired. Re-run the login from [`../../00-setup/auth.md`](../../00-setup/auth.md):

```bash
databricks auth login --host https://<your-workspace>.cloud.databricks.com --profile workshop
```

Then re-run the step.

## "Missing required env var LB_PROJECT / LB_BRANCH"

You're in a terminal that didn't load your environment. Re-source it:

```bash
source workshop.env
```

Or re-export `LB_PROFILE`, `LB_PROJECT`, `LB_BRANCH`, `LB_SCHEMA` by hand.

## "table factory.maintenance_log does not exist" or writeup is NULL

The factory schema was not loaded, or the maintenance logs were not seeded. Go back to [`../../00-setup/`](../../00-setup/) and run the load-factory step.

## Full-text search query returns no results

Check that the table has data with actual text:

```sql
SELECT COUNT(*) FROM factory.maintenance_log WHERE writeup IS NOT NULL;
```

If it's zero, the logs weren't seeded. Also check the language parameter in `to_tsvector`. The query uses `'english'` as the language; if your writeups are in another language, that won't work.

## pg_trgm is not available

This is rare. [pg_trgm](../../docs/glossary.md) is a standard Postgres extension. If it's not available:

```bash
CREATE EXTENSION IF NOT EXISTS pg_trgm;
```

If this fails, contact your Databricks team. It's built into Postgres and should be available.

## My full-text search query is slow even with a GIN index

Large FTS queries can be slow if the query term matches many documents. Check the query plan:

```sql
EXPLAIN (ANALYZE, BUFFERS) 
SELECT * FROM factory.maintenance_log
 WHERE to_tsvector('english', writeup) @@ to_tsquery('english', 'hydraulic & bearing')
 ORDER BY ts_rank(...) DESC;
```

Look for "Index Scan" in the plan. If you see "Seq Scan", either:
1. The dataset is too small (< 1000 rows) for the index to be worthwhile.
2. The index doesn't exist. Create it: `CREATE INDEX idx_maintenance_log_fts ON factory.maintenance_log USING gin(to_tsvector('english', writeup));`
3. The query is so selective that a sequential scan is faster.

## What's the difference between `to_tsquery` and `plainto_tsquery`?

- **`plainto_tsquery`**: simpler; treats input as plain text and adds AND operators. `plainto_tsquery('english', 'hydraulic bearing')` becomes `'hydraulic' & 'bearing'`.
- **`to_tsquery`**: more powerful; lets you write operators directly. `to_tsquery('english', 'hydraulic | bearing')` searches for either word (OR logic).

Use `plainto_tsquery` for simple queries (just words), `to_tsquery` when you need boolean logic.

## How do I combine full-text search with other filters?

Use AND in the WHERE clause:

```sql
SELECT * FROM factory.maintenance_log
 WHERE to_tsvector('english', writeup) @@ to_tsquery('english', 'hydraulic')
   AND machine_id = 'M-204'
   AND ts > now() - INTERVAL '1 year';
```

This finds notes about hydraulic issues on machine M-204 from the past year, ranked by relevance.

## Can I search across multiple columns?

Yes, combine them in `to_tsvector`:

```sql
SELECT * FROM factory.maintenance_log
 WHERE to_tsvector('english', writeup || ' ' || COALESCE(system, '')) 
       @@ to_tsquery('english', 'hydraulic');
```

This searches both the writeup and the system (subsystem) column. The `||` concatenates them; the COALESCE handles NULLs.

## pgvector is not available

pgvector is optional (only for the hybrid search step). If it's not available, skip that step. Keyword search (FTS) and fuzzy matching work without it.

## How do I tune the blend in hybrid search?

Change the weights in the formula:

```sql
ts_rank(...) * 0.5 + (1 - (embedding <-> query_embedding)) * 0.5  -- 50/50
ts_rank(...) * 0.7 + (1 - (embedding <-> query_embedding)) * 0.3  -- 70/30
```

Start with 60/40 (keyword/semantic) and adjust based on your results. If you're getting too many off-topic results, increase keyword weight. If you're missing nuanced results, increase semantic weight.

## What's the trigram approach, really?

A trigram is a 3-character substring. "BEARING" has trigrams: " BE", "BEA", "EAR", "ARI", "RIN", "ING", "NG ". "BEARING" and "BERING" (missing the A) share most trigrams (" BE", "ERI", "RIN", "ING"). The `similarity()` function counts overlapping trigrams and returns a score (0 to 1). It's simple but surprisingly effective for typo tolerance.

## Can I search on exact phrases?

Yes, use phrase queries in `to_tsquery`:

```sql
SELECT * FROM factory.maintenance_log
 WHERE to_tsvector('english', writeup) @@ to_tsquery('english', '"hydraulic pressure"');
```

The quotes make it a phrase query. It matches only if the words appear in that order and are adjacent.
