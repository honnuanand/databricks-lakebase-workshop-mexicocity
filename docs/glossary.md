# Glossary

Plain-language definitions for the terms and acronyms used across the workshop. Each journey
spells out an acronym the first time it uses it and links here, so you can start with whichever
journey matters to you and never be stuck on a term.

## Lakebase and Databricks

- **Lakebase** — the operational (transactional) database built into Databricks. It speaks
  standard PostgreSQL and adds capabilities like branching, point-in-time restore, and scale to
  zero.
- **Branch** — a full, isolated, copy-on-write copy of a database. Creating one copies no data;
  only changes you make afterward take space. This is what lets a whole room work in parallel.
- **Copy-on-write** — a branch shares the source's storage until you change something; only the
  changed pages get written separately. That is why branching is fast and cheap.
- **Point-in-time restore (PITR)** — recovering a database to how it looked at a past moment, by
  branching at an earlier point in its history.
- **Endpoint** — the compute you actually connect to for a branch, reachable over the Postgres
  wire on port 5432.
- **Project** — the Lakebase container that holds branches and their endpoints.
- **Unity Catalog (UC)** — Databricks' governance layer for data: access control, lineage, and
  auditing across both operational and analytical data.
- **Lakehouse** — the analytical side of Databricks (Delta tables governed by Unity Catalog),
  as opposed to the operational Lakebase side.
- **Service principal (SP)** — a non-human identity an application uses to authenticate, as
  opposed to a person logging in.
- **On-behalf-of (OBO)** — when an app calls Databricks using the signed-in user's identity, so
  that user's permissions apply, rather than the app's own identity.
- **Foundation Model API** — the Databricks endpoint for calling a hosted large language model.

## PostgreSQL features

- **OLTP (online transaction processing)** — the many small, fast reads and writes an
  application makes (the operational workload Lakebase serves).
- **OLAP (online analytical processing)** — large scans and aggregations over lots of data (the
  analytical workload the lakehouse serves).
- **WAL (write-ahead log)** — the running journal of every change Postgres makes. Branching and
  point-in-time restore both work off it.
- **LSN (log sequence number)** — a position in the write-ahead log. "The database five seconds
  ago" means the log sequence number from five seconds ago.
- **MVCC (multi-version concurrency control)** — how Postgres lets readers and writers work at
  once without blocking: an update writes a new version of a row instead of overwriting it.
- **VACUUM** — the Postgres maintenance step that reclaims space from old row versions.
- **RLS (row-level security)** — a rule attached to a table so the same query returns different
  rows depending on who is asking. The database enforces it, not the application.
- **JSONB** — Postgres' binary JSON column type, with operators and indexes for querying inside
  documents.
- **GIN / GiST / BRIN / HNSW / btree / hash** — kinds of database index, each suited to a
  different query shape (text and JSON, geometry and ranges, large ordered data, vectors, exact
  lookups). See [One engine, every index](../journeys/pg-index/).
- **pgvector** — a Postgres extension that stores embedding vectors and finds nearest matches,
  for similarity search.
- **PostGIS** — a Postgres extension for geographic data: points, distances, and "within N km"
  queries.
- **pg_trgm** — a Postgres extension for fuzzy, typo-tolerant text matching using trigrams
  (three-character slices).
- **FTS (full-text search)** — ranking documents by how well they match search words, built into
  Postgres.
- **CTE (common table expression)** — a named subquery in a `WITH` clause. A recursive one walks
  a tree, such as a bill of materials.
- **Embedding** — a list of numbers representing the meaning of text or an item, so similar
  things sit close together. Used for similarity search.
- **CDC (change data capture)** — reading a stream of every insert, update, and delete as they
  happen, off the write-ahead log.

## Manufacturing terms (the running example)

- **MES (manufacturing execution system)** — the operational system that runs the shop floor:
  work orders, routing, machine status. In this workshop, Lakebase plays that role.
- **BOM (bill of materials)** — the tree of parts that make up a product: a product is built
  from parts, which are built from sub-parts, all the way down.
- **Digital twin** — a live data model of a physical asset (here, a machine or plant) kept in
  sync with its real state.
- **Work order** — an instruction to produce a quantity of a product, made up of routing steps
  (operations) run on machines.
- **Operation** — one routing step of a work order, scheduled onto a machine for a time window.
- **OEE (overall equipment effectiveness)** — a standard manufacturing measure of how well a
  machine is used (availability, performance, quality).
- **OT / IT** — operational technology (the machines and sensors on the floor) versus
  information technology (the analytics and business systems). "Live data flow" connects them.
- **Predictive maintenance** — using sensor data to predict a failure before it happens, so you
  service a machine before it breaks.

## Security

- **CMK (customer-managed keys)** — you supply the encryption key, held in your own cloud key
  service, so you control access to your data at rest and can revoke it.
- **KMS (key management service)** — the cloud service (for example AWS KMS) that holds and
  controls encryption keys.
- **pgcrypto** — a Postgres extension for encrypting individual column values.
