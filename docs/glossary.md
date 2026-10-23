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
| **Lakebase Search** | A Lakebase project setting (enabled in the UI, cannot be turned off) that adds the `lakebase_text`, `lakebase_vector`, and `lakebase_tokenizer` extensions. See [Lakebase Search](../journeys/lakebase-search/). |
| **BM25** | The standard relevance score for keyword search: it rewards rare and repeated words and short, focused text. `lakebase_text` computes it with a `lakebase_bm25` index. |
| **ANN** (approximate nearest neighbor) | Finding the closest embeddings without comparing against every row, trading a little accuracy for speed. `lakebase_vector`'s `lakebase_ann` index does it with IVF and RaBitQ. |
| **IVF** (inverted file index) | An ANN technique that groups vectors into partitions and only scans the partitions closest to the query. |
| **Hybrid search** | Combining keyword (BM25) and vector results into one ranking, so a row found by words or by meaning can appear. |
| **RRF** (Reciprocal Rank Fusion) | A simple way to merge ranked lists: each row gets `1 / (60 + rank)` from every list it appears in. |
| **CTE** (common table expression) | A named subquery in a `WITH` clause. A recursive one walks a tree, such as a bill of materials. |
| **Embedding** | A list of numbers representing the meaning of text or an item, so similar things sit close together. Used for similarity search. |
| **CDC** (change data capture) | Reading a stream of every insert, update, and delete as they happen, off the write-ahead log. |
| **Live data flow** | Running operational and analytical work against one database copy, with no pipeline or sync lag: write through Lakebase, read the same rows from the lakehouse the same moment. |

## Banking (the running example)

The workshop's bank. See [Meet the bank](../00-setup/#meet-the-bank) in setup for the
full cast.

| Term | What it means |
| ---- | ------------- |
| **MXN** | The Mexican peso. All amounts in the workshop's bank are in MXN. |
| **SPEI** | Mexico's real-time interbank transfer system, run by Banco de México. A `txn` with `channel = 'SPEI'` is a bank transfer, so it has no merchant category code. |
| **CLABE** | The 18-digit standardized bank account number used for SPEI transfers: bank code, plaza code, account number, and a check digit. The workshop's CLABEs are synthetic. |
| **CoDi** | Cobro Digital, a QR-code payment scheme built on SPEI. |
| **Core banking** | The operational system that runs accounts, transactions, and balances. In this workshop, Lakebase plays that role. |
| **Holdings tree** | The tree of instruments that make up a fund: a fund holds instruments, some of which are sleeves that themselves hold instruments, all the way down. |
| **Sleeve** | An instrument that is itself a basket of other instruments (a fund-of-funds building block); it makes the holdings tree more than one level deep. |
| **Trade / settlement** | A trade is an instruction to buy or sell an instrument; its settlement is the clearing step scheduled into a time window. |
| **Counterparty / custodian** | The counterparty is the other side of a trade or the issuer behind an instrument; the custodian is the institution that holds the assets. |
| **Fraud / AML** | Fraud is unauthorized use of an account; AML (anti-money-laundering) is detecting illicit movement of funds, for example structuring just under a reporting threshold. |
| **Exposure** | How much a fund (or the bank) stands to lose if a given instrument or counterparty goes bad; the knowledge-graph journeys derive it by look-through. |

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
