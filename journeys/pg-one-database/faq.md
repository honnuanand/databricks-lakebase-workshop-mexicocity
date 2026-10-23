# One query, every type, FAQ

## I got an error about PostGIS not being available

[PostGIS](../../docs/glossary.md) (the geospatial extension) may not be installed on your instance. The script handles this gracefully
by showing a note if geometry functions fail. If you want to test geospatial anyway, you can install PostGIS:

```bash
CREATE EXTENSION IF NOT EXISTS postgis WITH SCHEMA public
```

Then re-run the script.

## The embedding column is failing

[pgvector](../../docs/glossary.md) may not be available on your instance. The script handles missing pgvector gracefully. If you want vectors,
install the extension:

```bash
CREATE EXTENSION IF NOT EXISTS vector WITH SCHEMA public
```

Then re-run the script.

## The query ran but results look odd

The demo uses generated random data for embeddings and locations. Results depend on random values. Re-run the script
and you'll get different results (but the same query structure).

## Can I use this pattern in production?

Yes. This is a real pattern:
- Relational columns: account IDs, timestamps, categories.
- JSON: flexible attributes (specs that vary per account type).
- Vectors: embeddings for similarity search.
- Geospatial: branch locations, counterparty locations, service areas.

All in one table, all queried together. Common in banking (accounts with specs + locations + similarity),
fintech (customer profiles + embedding-based recommendations), and financial services (counterparties + risk profiles + geo).

## What about performance? Won't a four-type query be slow?

Not if indexed correctly. The script creates a table; in production you'd add indexes:
- [BTREE](../../docs/glossary.md) on relational columns (branch_id, line).
- [GIN](../../docs/glossary.md) on [JSONB](../../docs/glossary.md) (spec).
- [HNSW](../../docs/glossary.md) on vectors (embedding).
- [GiST](../../docs/glossary.md) on geospatial (location).

With proper indexes, the planner chooses the best path. The unified query is as fast as a single-type query
would be on a single-purpose system.

## Should I always put all data types on one table?

No. Use one table when:
- The data is conceptually one entity (an account has a location, a spec, an embedding, all part of the account).
- Queries often join all or most of the types.
- You want strong consistency and simplicity.

Split into multiple tables if:
- The data is conceptually separate (accounts and trades are different entities).
- Queries rarely need both (then a JOIN is fine and keeps data organized).

This journey shows the unified pattern; [`../pg-iso/`](../pg-iso/) implicitly showed the multi-table pattern
(accounts in one table, settlement slots in another).

## Can I update JSON or vectors in place?

Yes. The same UPDATE syntax works:

```sql
UPDATE account_unified_demo
SET spec = spec || '{"new_field": "value"}'::jsonb
WHERE account_id = 'CTA-123'
```

Vectors can be updated the same way. Geospatial columns (geometry) can also be updated.

## What's the cost of having all four types on one table?

Storage: slightly higher (four columns worth of data), but reasonable. Query overhead: none (you only
query the columns you need). Write overhead: none (all types write at Postgres speed). The unified pattern
is a win: simpler code, no sync, one transaction.
