# Search, three ways, instructions

Run these on your own branch. If you haven't done [`../../00-setup/`](../../00-setup/), do that first; you need `LB_PROFILE`, `LB_PROJECT`, `LB_BRANCH`, and `LB_SCHEMA` set, and the factory loaded.

Everything here is a single script you can read: [`../../common/scripts/pg_search.py`](../../common/scripts/pg_search.py). You can run it end to end, or follow the steps by hand to see each piece.

## Run it end to end

```bash
cd common/scripts
python pg_search.py
```

This walks through the entire journey and prints results. Read on for what each step does; the exact output to expect is in [`expected.md`](expected.md).

## Or step through it by hand

### Step 1, inspect maintenance write-ups

Maintenance logs contain free-text notes from engineers:

```bash
python lakebase.py --sql \
  "SELECT log_id, machine_id, writeup FROM factory.maintenance_log LIMIT 3"
```

These are unstructured engineer notes, the kind of data that's hard to search with traditional filters.

### Step 2, full-text search

Full-text search ranks results by relevance. Here's a query to find notes mentioning "hydraulic" and "bearing":

```bash
python pg_search.py --step fts
```

The script runs:

```sql
SELECT log_id, machine_id, writeup,
       ts_rank(to_tsvector('english', writeup), 
               to_tsquery('english', 'hydraulic & bearing')) as rank
  FROM factory.maintenance_log
 WHERE to_tsvector('english', writeup) @@ to_tsquery('english', 'hydraulic & bearing')
 ORDER BY rank DESC
 LIMIT 10;
```

The `to_tsvector` converts text to a "text search vector" (a ranked list of lexemes, word stems). The `@@` operator matches the query against the vector. `ts_rank` scores the match. Results are ranked by relevance, not just presence.

### Step 3, fuzzy matching with trigrams

Fuzzy matching tolerates typos. Enable [pg_trgm](../../docs/glossary.md) and find part numbers close to a given string:

```bash
python pg_search.py --step fuzzy
```

The script runs:

```sql
CREATE EXTENSION IF NOT EXISTS pg_trgm;

SELECT part_id, name,
       similarity(part_id, 'PT-BEARING-6204') as sim
  FROM factory.part
 WHERE part_id % 'PT-BEARING-6204'  -- % means "similar to"
 ORDER BY sim DESC
 LIMIT 5;
```

The `%` operator asks "is this string similar?" Similarity is measured by overlapping [trigrams](../../docs/glossary.md) (3-character substrings). A typo usually preserves most trigrams, so the match still works. `similarity()` returns a score (0 to 1); higher is more similar.

### Step 4, create a GIN index on full-text search

[GIN](../../docs/glossary.md) indexes accelerate full-text search:

```bash
python pg_search.py --step index
```

The script creates:

```sql
CREATE INDEX IF NOT EXISTS idx_maintenance_log_fts
  ON factory.maintenance_log
  USING gin(to_tsvector('english', writeup));
```

Then re-run the FTS query. On the factory dataset (a few hundred logs) the difference is subtle, but on production data (millions of logs) GIN is essential.

### Step 5, hybrid search (keyword + semantic)

If you have embeddings (from pgvector), combine keyword and semantic ranking:

```bash
python pg_search.py --step hybrid
```

This is optional and requires pgvector. The script runs:

```sql
SELECT log_id, machine_id,
       ts_rank(...) as keyword_rank,
       1 - (embedding <-> query_embedding) as semantic_sim,
       ts_rank(...) * 0.6 + (1 - (embedding <-> query_embedding)) * 0.4 as blended_rank
  FROM factory.maintenance_log
 WHERE ... -- FTS filter
 ORDER BY blended_rank DESC;
```

This combines two signals: keyword relevance (60%) and semantic similarity (40%). The weights are tunable depending on your use case.

## What you just did

You searched maintenance write-ups using full-text search (ranked by relevance), fuzzy matching (typo-tolerant part numbers), and hybrid ranking (blending keyword and semantic signals). All of that is native Postgres, indexed for speed, queryable in SQL.
