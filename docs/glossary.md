# Glossary

Every term and acronym the workshop uses, in plain language. Each journey spells out an acronym
the first time it appears and links here, so you can start with whichever journey matters to you
and never get stuck on a word.

**Jump to:** [Lakebase & Databricks](#lakebase--databricks) · [PostgreSQL features](#postgresql-features) · [Manufacturing](#manufacturing-the-running-example) · [Security](#security) · [Knowledge graphs](#knowledge-graphs) · [APIs & web](#apis--web)

## Lakebase & Databricks

The platform this workshop runs on: the operational database and the governance and analytics
around it.

| Term | What it means |
| ---- | ------------- |
| **Lakebase** | The operational (transactional) database built into Databricks. Speaks standard PostgreSQL, and adds branching, point-in-time restore, and scale to zero. |
| **Branch** | A full, isolated, copy-on-write copy of a database. Creating one copies no data; only your later changes take space. This is what lets a whole room work in parallel. |
| **Copy-on-write** | A branch shares the source's storage until you change something; only changed pages are written separately. That is why branching is fast and near-free. |
| **Point-in-time restore (PITR)** | Recovering a database to how it looked at a past moment, by branching at an earlier point in its history. |
| **Endpoint** | The compute you connect to for a branch, reachable over the Postgres wire on port 5432. |
| **Project** | The Lakebase container that holds branches and their endpoints. |
| **Unity Catalog (UC)** | Databricks' governance layer: access control, lineage, and auditing across operational and analytical data. |
| **Lakehouse** | The analytical side of Databricks (Delta tables governed by Unity Catalog), as opposed to the operational Lakebase side. |
| **Service principal (SP)** | A non-human identity an application uses to authenticate, as opposed to a person logging in. |
| **On-behalf-of (OBO)** | When an app calls Databricks as the signed-in user, so that user's permissions apply rather than the app's own. |
| **Foundation Model API** | The Databricks endpoint for calling a hosted large language model. |

## PostgreSQL features

Lakebase is real PostgreSQL, so the standard Postgres machinery is all here.

| Term | What it means |
| ---- | ------------- |
| **OLTP** (online transaction processing) | The many small, fast reads and writes an application makes. The operational workload Lakebase serves. |
| **OLAP** (online analytical processing) | Large scans and aggregations over lots of data. The analytical workload the lakehouse serves. |
| **WAL** (write-ahead log) | The running journal of every change Postgres makes. Branching and point-in-time restore both work off it. |
| **LSN** (log sequence number) | A position in the write-ahead log. "The database five seconds ago" means the log sequence number from five seconds ago. |
| **MVCC** (multi-version concurrency control) | How Postgres lets readers and writers work at once without blocking: an update writes a new row version instead of overwriting. |
| **VACUUM** | The maintenance step that reclaims space from old row versions. |
| **RLS** (row-level security) | A rule on a table so the same query returns different rows depending on who asks. The database enforces it, not the app. |
| **JSONB** | Postgres' binary JSON column type, with operators and indexes for querying inside documents. |
| **Index access methods** (btree, hash, GIN, GiST, BRIN, HNSW) | Kinds of index, each suited to a query shape: exact lookups, text and JSON, geometry and ranges, large ordered data, vectors. See [One engine, every index](../journeys/pg-index/). |
| **pgvector** | A Postgres extension that stores embedding vectors and finds nearest matches, for similarity search. |
| **PostGIS** | A Postgres extension for geographic data: points, distances, and "within N km" queries. |
| **pg_trgm** | A Postgres extension for fuzzy, typo-tolerant text matching using trigrams (three-character slices). |
| **FTS** (full-text search) | Ranking documents by how well they match search words, built into Postgres. |
| **CTE** (common table expression) | A named subquery in a `WITH` clause. A recursive one walks a tree, such as a bill of materials. |
| **Embedding** | A list of numbers representing the meaning of text or an item, so similar things sit close together. Used for similarity search. |
| **CDC** (change data capture) | Reading a stream of every insert, update, and delete as they happen, off the write-ahead log. |
| **Live data flow** | Running operational and analytical work against one database copy, with no pipeline or sync lag: write through Lakebase, read the same rows from the lakehouse the same moment. |

## Manufacturing (the running example)

The workshop's factory. See [Meet the factory](../00-setup/#meet-the-factory) in setup for the
full cast.

| Term | What it means |
| ---- | ------------- |
| **MES** (manufacturing execution system) | The operational system that runs the shop floor: work orders, routing, machine status. In this workshop, Lakebase plays that role. |
| **BOM** (bill of materials) | The tree of parts that make up a product: a product is built from parts, built from sub-parts, all the way down. |
| **Digital twin** | A live data model of a physical asset (here, a machine or plant) kept in sync with its real state. |
| **Work order** | An instruction to produce a quantity of a product, made up of routing steps (operations) run on machines. |
| **Operation** | One routing step of a work order, scheduled onto a machine for a time window. |
| **OEE** (overall equipment effectiveness) | A standard measure of how well a machine is used: availability, performance, and quality. |
| **OT / IT** | Operational technology (machines and sensors on the floor) versus information technology (analytics and business systems). Live data flow connects them. |
| **Predictive maintenance** | Using sensor data to predict a failure before it happens, so you service a machine before it breaks. |

## Security

| Term | What it means |
| ---- | ------------- |
| **CMK** (customer-managed keys) | You supply the encryption key, held in your own cloud key service, so you control access to your data at rest and can revoke it. |
| **KMS** (key management service) | The cloud service (for example AWS KMS) that holds and controls encryption keys. |
| **pgcrypto** | A Postgres extension for encrypting individual column values. |

## Knowledge graphs

| Term | What it means |
| ---- | ------------- |
| **RDF** (Resource Description Framework) | A W3C standard for representing facts as triples (subject, predicate, object), forming a graph of linked data. |
| **SPARQL** (SPARQL Protocol and RDF Query Language) | A query language for RDF graphs, like SQL for tables. Queries pattern-match on triples. |
| **OWL** (Web Ontology Language) | An extension of RDF that adds inference rules and consistency checks, so the system derives new facts from rules you state. |
| **RDFS** (RDF Schema) | A lighter version of OWL that defines classes and properties, for basic type hierarchies without full inference. |

## APIs & web

| Term | What it means |
| ---- | ------------- |
| **REST** | An architectural style for web APIs using HTTP verbs (GET, POST, PATCH, DELETE) and standard response formats, usually JSON. |
| **PostgREST** | A tool that generates a REST API straight from a PostgreSQL schema, following REST conventions. |
| **OAuth** | An authentication standard that lets a user delegate access to their Databricks resources without sharing passwords. |
