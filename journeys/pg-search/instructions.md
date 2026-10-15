# Search, three ways, instructions

## How to run this journey

There are a few ways to work through the steps. Pick one:

- **Notebook, step by step (recommended for learning):** open [`pg_search.ipynb`](pg_search.ipynb) and run one cell at a time. Reading each result before the next step is where the learning happens.
- **In a Databricks workspace:** import [`pg_search_databricks.py`](pg_search_databricks.py) and run it cell by cell there.
- **By hand:** follow the numbered steps below, copying each command yourself.
- **Just see it work:** run `python pg_search.py` from this folder to execute the whole thing at once. Fast, but you learn the most from the notebook.

Run these on your own branch. If you haven't done [`../../00-setup/`](../../00-setup/), do that first; you need `LB_PROFILE`, `LB_PROJECT`, `LB_BRANCH`, and `LB_SCHEMA` set, and the bank schema loaded.

Everything here is a single script you can read: [`./pg_search.py`](./pg_search.py). You can run it end to end, or follow the steps by hand to see each piece.

## Run it end to end

```bash
cd journeys/pg-search
python pg_search.py
```

This walks through the entire journey and prints results. Read on for what each step does; the exact output to expect is in [`expected.md`](expected.md).

## Or step through it by hand

### Step 1, inspect case notes

Case notes contain free-text analyst write-ups on fraud and AML alerts:

```bash
python ../../common/scripts/lakebase.py --sql \
  "SELECT note_id, account_id, writeup FROM bank.case_note LIMIT 3"
```

These are unstructured analyst notes, the kind of data that's hard to search with traditional filters.

### Step 2, full-text search

Full-text search ranks results by relevance. Here's a query to find notes mentioning "wire" or "fraud":

```bash
python pg_search.py --step fts
```

The script runs:

```sql
SELECT note_id, account_id, writeup,
       ts_rank(to_tsvector('english', writeup), 
               to_tsquery('english', 'wire | fraud')) as rank
  FROM bank.case_note
 WHERE to_tsvector('english', writeup) @@ to_tsquery('english', 'wire | fraud')
 ORDER BY rank DESC
 LIMIT 5;
```

The `to_tsvector` converts text to a "text search vector" (a ranked list of lexemes, word stems). The `@@` operator matches the query against the vector. `ts_rank` scores the match. Results are ranked by relevance, not just presence.

### Step 3, fuzzy matching with trigrams

Fuzzy matching tolerates typos. Enable [pg_trgm](../../docs/glossary.md) and find account IDs close to a given string:

```bash
python pg_search.py --step fuzzy
```

The script runs:

```sql
CREATE EXTENSION IF NOT EXISTS pg_trgm;

SELECT account_id,
       similarity(account_id, 'CTA-100240') as sim
  FROM bank.account
 WHERE account_id %% 'CTA-100240'  -- %% means "similar to" (doubled for psycopg parameter marker)
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
CREATE INDEX IF NOT EXISTS idx_case_note_fts
  ON bank.case_note
  USING gin(to_tsvector('english', writeup));
```

Then re-run the FTS query. On the bank dataset (a few hundred notes) the difference is subtle, but on production data (millions of notes) GIN is essential.

### Step 5, hybrid search (keyword + semantic)

If you have embeddings (from pgvector), combine keyword and semantic ranking:

```bash
python pg_search.py --step hybrid
```

This is optional and requires pgvector. The script runs:

```sql
SELECT note_id, account_id,
       ts_rank(...) as keyword_rank,
       1 - (embedding <-> query_embedding) as semantic_sim,
       ts_rank(...) * 0.6 + (1 - (embedding <-> query_embedding)) * 0.4 as blended_rank
  FROM bank.case_note
 WHERE ... -- FTS filter
 ORDER BY blended_rank DESC;
```

This combines two signals: keyword relevance (60%) and semantic similarity (40%). The weights are tunable depending on your use case.

## What you just did

You searched case notes using full-text search (ranked by relevance), fuzzy matching (typo-tolerant account and instrument IDs), and hybrid ranking (blending keyword and semantic signals). All of that is native Postgres, indexed for speed, queryable in SQL.
