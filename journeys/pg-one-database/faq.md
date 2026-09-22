# One query, every type, FAQ

## I got an error about PostGIS not being available

PostGIS (the geospatial extension) may not be installed on your instance. The script handles this gracefully
by showing a note if geometry functions fail. If you want to test geospatial anyway, you can install PostGIS:

```bash
CREATE EXTENSION IF NOT EXISTS postgis WITH SCHEMA public
```

Then re-run the script.

## The embedding column is failing

pgvector may not be available on your instance. The script handles missing pgvector gracefully. If you want vectors,
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
- Relational columns: user IDs, timestamps, categories.
- JSON: flexible attributes (specs that vary per product).
- Vectors: embeddings for similarity search.
- Geospatial: store locations, service areas, etc.

All in one table, all queried together. Common in e-commerce (products with specs + locations + similarity),
smart manufacturing (machines + specs + locations), and healthcare (patients + attributes + locations).

## What about performance? Won't a four-type query be slow?

Not if indexed correctly. The script creates a table; in production you'd add indexes:
- BTREE on relational columns (plant_id, line).
- GIN on JSONB (spec).
- HNSW on vectors (embedding).
- GIST on geospatial (location).

With proper indexes, the planner chooses the best path. The unified query is as fast as a single-type query
would be on a single-purpose system.

## Should I always put all data types on one table?

No. Use one table when:
- The data is conceptually one entity (a machine has a location, a spec, an embedding, all part of the machine).
- Queries often join all or most of the types.
- You want strong consistency and simplicity.

Split into multiple tables if:
- The data is conceptually separate (machines and suppliers are different entities).
- Queries rarely need both (then a JOIN is fine and keeps data organized).

This journey shows the unified pattern; [`../pg-iso/`](../pg-iso/) implicitly showed the multi-table pattern
(machines in one table, availability slots in another).

## Can I update JSON or vectors in place?

Yes. The same UPDATE syntax works:

```sql
UPDATE machine_unified_demo
SET spec = spec || '{"new_field": "value"}'::jsonb
WHERE machine_id = 'M-123'
```

Vectors can be updated the same way. Geospatial columns (geometry) can also be updated.

## What's the cost of having all four types on one table?

Storage: slightly higher (four columns worth of data), but reasonable. Query overhead: none (you only
query the columns you need). Write overhead: none (all types write at Postgres speed). The unified pattern
is a win: simpler code, no sync, one transaction.
