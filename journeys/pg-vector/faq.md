# Operational vectors, FAQ

## It failed with a "refresh token" or authentication error

Your Databricks login expired. Re-run the login from [`../../00-setup/auth.md`](../../00-setup/auth.md):

```bash
databricks auth login --host https://<your-workspace>.cloud.databricks.com --profile workshop
```

Then re-run the script.

## "Missing required env var LB_PROJECT / LB_BRANCH"

Re-source your environment:

```bash
source workshop.env
```

Or re-export `LB_PROFILE`, `LB_PROJECT`, `LB_BRANCH`, `LB_SCHEMA` by hand.

## "pgvector extension not available"

The pgvector extension must be installed in your Lakebase instance. If you see "ERROR: extension
pgvector does not exist", it means:

1. **The instance doesn't have pgvector**: Ask your administrator to enable it (it's a standard
   Postgres extension). This is typically done at the instance level, not per branch.
2. **Check Postgres version**: pgvector requires Postgres 12+. Lakebase uses Postgres 17, so this
   should not be an issue.
3. **Try creating it anyway**: Some instances allow users to create the extension:
   ```bash
   python lakebase.py --sql "CREATE EXTENSION pgvector"
   ```

If that fails with a permission error, the extension must be pre-installed by an admin.

## The embedding column didn't get added

If `ALTER TABLE` failed, check:

1. **Are you on the right branch?** Confirm: `echo $LB_BRANCH`.
2. **Does the instrument table exist?** `python lakebase.py --sql "SELECT count(*) FROM bank.instrument"`.
3. **Do you have ALTER permissions?** If you're on a shared instance/project with restricted
   permissions, you may not be able to alter the table. Check with your instructor.

## The embedding population is slow

If the script hangs or takes several seconds, check:

1. **Network latency**: If you're calling an external embedding API (e.g., OpenAI), network
   latency could add up. The script uses deterministic hashes to avoid this.
2. **Batch size**: The script updates one instrument at a time. For 1000+ instruments, consider batching:
   ```sql
   UPDATE bank.instrument SET embedding = ... WHERE ...;  -- all at once
   ```
3. **Is there a large table scan?** If the instrument table is huge, the UPDATE could take time. Limit
   the scope:
   ```sql
   UPDATE bank.instrument SET embedding = ... WHERE embedding IS NULL;  -- only missing
   ```

## The similarity search returned no results

If the query returned zero rows, check:

1. **Are there embeddings?** Verify at least one instrument has an embedding:
   ```bash
   python lakebase.py --sql "SELECT count(*) FROM bank.instrument WHERE embedding IS NOT NULL"
   ```
   Should be > 0.

2. **Is the query syntax correct?** Check that you're using the `<=>` operator (cosine distance):
   ```bash
   python lakebase.py --sql \
     "SELECT 1 - (embedding <=> embedding) FROM bank.instrument LIMIT 1"
   ```
   Should return a value close to 1 (exact match with itself).

3. **Is the reference instrument in the table?** The query filters out the reference instrument
   (`WHERE instrument_id != 'INS-AAPL'`). Make sure that instrument exists and has an embedding.

## The similarity scores don't make sense (all 0.5, or all the same)

If all scores are identical or suspiciously similar, the embeddings may not be diverse:

1. **Check an embedding**: `python lakebase.py --sql "SELECT embedding FROM bank.instrument LIMIT 1"`.
   You should see a vector of floating-point numbers, e.g., `[-0.1, 0.5, ..., 0.02]`.

2. **Are the embeddings reproducible?** The script uses deterministic hashes, so running twice
   should produce the same embedding for the same instrument.

3. **Is the cosine operator working?** Test it directly:
   ```bash
   python lakebase.py --sql \
     "SELECT embedding <=> embedding FROM bank.instrument LIMIT 1"
   ```
   Should return 0 (identical vectors have distance 0).

## I want to use real embeddings (not hashes)

The script uses deterministic hashes for reproducibility. To use real embeddings:

1. Call an embedding API for each instrument spec:
   ```python
   from databricks.sdk import WorkspaceClient
   w = WorkspaceClient()
   response = w.serving_endpoints.query(
       name="bge-large-en-v1.5",
       inputs=[{"text": part_spec_text}]
   )
   embedding = response.data[0]
   ```

2. Store in the database:
   ```python
   cur.execute("UPDATE bank.instrument SET embedding=%s WHERE instrument_id=%s", [embedding, instrument_id])
   ```

The pattern is identical; only the embedding source changes.

## Can I search by a custom vector (not an existing instrument)?

Yes. If you have a query vector (e.g., the spec of a failing security), you can search without
it being a instrument in the table:

```bash
python lakebase.py --sql \
  "SELECT instrument_id, 1 - (embedding <=> ARRAY[0.1, 0.2, ..., 0.3]::vector(768)) AS similarity
   FROM bank.instrument WHERE embedding IS NOT NULL
   ORDER BY similarity DESC LIMIT 5"
```

Pass the custom vector as a literal `ARRAY[...]::vector(768)`.

## Why cosine distance (<=>), not L2 distance (<->)?

Both are supported:
- **`<=>`** (cosine): magnitude-invariant, good for comparing "direction" (e.g., instrument specs).
- **`<->`** (L2): Euclidean distance, good for geometric queries (e.g., warehouse locations).

For instrument similarity, cosine distance is more robust because it ignores magnitude (a large security
is still similar to a small one if the proportions are the same). For the warehouse scenario, L2
would be used to find nearest warehouses by actual coordinates.

## Why pgvector on Lakebase, not Vector Search?

**pgvector**: single-transaction, in-process, live data, <1ms queries, supports any embedding.
Best for: operational decisions (is there a comparable instrument in stock right now?).

**Vector Search**: large-scale, batch-synced, multi-table, supports hybrid search, Databricks-managed.
Best for: RAG at scale (search lakehouse documents), large catalogs (millions of products).

Use pgvector for operational queries on live transactional data. Use Vector Search for large
data lakes that feed AI applications.

## How do I scale pgvector to millions of vectors?

pgvector with an HNSW index scales well:

1. **Create the index** (Step 6 in instructions):
   ```sql
   CREATE INDEX ON bank.instrument USING hnsw (embedding vector_cosine_ops)
   ```

2. **Tune [Hierarchical Navigable Small Worlds](../../docs/glossary.md) (HNSW) parameters** (optional): reduce `m` (max degree) or `ef_construction` for faster
   indexing on very large tables:
   ```sql
   CREATE INDEX ON bank.instrument USING hnsw (embedding vector_cosine_ops)
   WITH (m=16, ef_construction=64)
   ```

3. **Use batch queries**: instead of one query per embedding, batch 100+ similarity searches in
   a single SQL statement.

For billions of vectors, Vector Search is the recommended platform tool.
