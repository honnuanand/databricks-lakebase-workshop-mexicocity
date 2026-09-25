# Journeys

This is the workshop. Each journey is a self-contained folder you can run on your own branch
after finishing [`00-setup/`](../00-setup/). **This page is the order.** Folders are named by
what they are, not by number, so the curriculum can grow without renaming anything; the sequence
below is the intended path, but every journey stands alone, so jump to what you care about.

Each folder holds `README.md` (what and why), `instructions.md` (copy-paste steps),
`expected.md` (results to check against), and `faq.md` (when it goes wrong), plus the runnable
artifacts right there in the folder: a step-by-step notebook (`<name>.ipynb` for Jupyter and
`<name>_databricks.py` for a Databricks workspace) and an all-in-one script. The shared helpers
they build on live in [`../common/`](../common/).

New to a term or acronym in any journey? The [glossary](../docs/glossary.md) defines every one in
plain language.

**Two status columns:**

- **Build** tracks how far this workshop has written the journey: ⬜ not started · 🟡 drafting ·
  🟢 done (all four files + a runnable artifact) · ⭐ proven on a live run.
- **Runs** tracks the capability itself: **live** = runs fully against your branch · **preview**
  = a roadmap capability shown honestly against Postgres, labeled as not-yet-GA.

## Start here: the Lakebase difference

The capabilities a plain Postgres cannot do. Run these first; they are why Lakebase exists.

| # | Journey | What you'll do | Build | Runs |
| - | ------- | -------------- | ----- | ---- |
| 1 | [Branch the brain](branch-the-brain/) | Fork your whole factory database in seconds (zero-copy), diverge it, throw it away with production untouched. | ⭐ | live |
| 2 | [Break it, then rewind](break-and-rewind/) | Delete live machine data on purpose, then point-in-time-restore the database to seconds ago. No backup job. | ⭐ | live |
| 3 | [Scale to zero](scale-to-zero/) | Idle compute auto-suspends to $0 on its own; the next query wakes it in about two seconds. | ⭐ | live |
| 4 | [One copy, both directions](write-to-analytics/) | Write a reading through Lakebase, compute a failure-risk score, write it back; the same rows read from the lakehouse (explainer). | ⭐ | live |
| 5 | [Fits your landscape](pg-integration/) | Point any Postgres driver, ORM, or BI tool at Lakebase and watch it map the schema. Governed by Unity Catalog. | 🟢 | live |

## AI on one database

Agents, memory, and vectors on the same governed database that serves your transactions.

| # | Journey | What you'll do | Build | Runs |
| - | ------- | -------------- | ----- | ---- |
| 6 | [Agent memory](agent-memory/) | Give two agents one shared Lakebase memory table; one writes, the other recalls and acts on it. | 🟢 | live |
| 7 | [The agent does the work](agentic-work/) | An agent reads live machine data with a tool, writes a work order back, and remembers what it did. | 🟢 | live |
| 8 | [Human-in-the-loop](learning-loop/) | AI reads maintenance write-ups with a confidence score; low-confidence ones route to a human; the system learns. | 🟢 | live |
| 9 | [Operational vectors](pg-vector/) | Rank the best-fit replacement part by spec-embedding similarity, in the same transaction as your data. | 🟢 | live |

## Postgres power, in Lakebase

The standard Postgres feature set, run on the factory. For teams migrating off Oracle or
SQL Server, this is the "it already does what you need" track.

| # | Journey | What you'll do | Build | Runs |
| -- | ------- | -------------- | ----- | ---- |
| 10 | [SQL you already know](pg-sql-parity/) | Window functions, recursive CTEs (the CONNECT BY replacement = a BOM explosion), MERGE, Oracle idiom map. | 🟢 | live |
| 11 | [JSON documents](pg-json/) | Store varying part/product spec sheets as JSONB, query containment and paths in-engine, GIN-index them. | 🟢 | live |
| 12 | [Geospatial](pg-geo/) | Plants, warehouses, and suppliers on a map: "within N km of a depot" and "nearest to" in SQL, with PostGIS. | 🟢 | live |
| 13 | [Search, three ways](pg-search/) | Full-text, fuzzy (typo-tolerant serial numbers), and hybrid search over decades of maintenance write-ups. | 🟢 | live |
| 14 | [Row-level security](pg-rls/) | Multiple plants share one machine table; each sees only its own rows, enforced by the database. Plus column encryption. | 🟢 | live |
| 15 | [No double-booking](pg-booking/) | The database refuses to schedule two overlapping operations on the same machine (GiST exclusion). | 🟢 | live |
| 16 | [Watch the planner](pg-explain/) | EXPLAIN ANALYZE a slow scan, add one index, watch the cost-based planner flip its plan, with real numbers. | 🟢 | live |
| 17 | [Tune the planner](pg-perf/) | Fix a bad row estimate on correlated columns with extended statistics. Measured, honest. | 🟢 | live |
| 18 | [One engine, every index](pg-index/) | One table, six index types (btree, hash, gin, brin, gist, hnsw); prove the planner picks each. | 🟢 | live |
| 19 | [MVCC and the WAL](pg-mvcc/) | Watch one row become two versions on UPDATE, dead tuples accumulate, VACUUM reclaim, the WAL advance. | 🟢 | live |
| 20 | [Isolation and locking](pg-iso/) | Two sessions hit one row; one waits on the other's lock; both writes land in order. No lost update. | 🟢 | live |
| 21 | [Scale-out: partitioning](pg-partition/) | Partition sensor readings by month; watch the planner prune to one partition. Analytics scales out to the lakehouse. | 🟢 | live |
| 22 | [Postgres in your browser](pg-lite/) | A full Postgres compiled to WebAssembly (PGlite), running client-side, speaking the same SQL as Lakebase. | 🟢 | live |
| 23 | [Feature store, served online](pg-features/) | Materialize per-machine features, serve a feature vector on a primary-key lookup in single-digit ms. | 🟢 | live |
| 24 | [One query, every type](pg-one-database/) | One SELECT spanning relational + JSON + vector + geospatial on a single table. Not four products. | 🟢 | live |
| 25 | [Your commits are a change feed](pg-cdc/) | Tap the commit log: every insert/update/delete as an ordered, LSN-stamped feed via logical decoding. | 🟢 | preview |

## The knowledge graph track

Model factory knowledge as a graph and reason over it, all on Lakebase.

| # | Journey | What you'll do | Build | Runs |
| -- | ------- | -------------- | ----- | ---- |
| 26 | [Build the knowledge graph](kg-build/) | Turn scattered facts (part → subassembly → product → plant) into RDF triples in Lakebase; draw the graph. | 🟢 | live |
| 27 | [Ask the graph in SPARQL](kg-sparql/) | A multi-hop question ("which products use a part from a disrupted supplier?") that's natural as SPARQL, ugly as SQL joins. | 🟢 | live |
| 28 | [The graph reasons](kg-infer/) | State a taxonomy and one rule; the graph derives facts you never wrote down (which products a recall touches). | 🟢 | live |

## Security and access

| # | Journey | What you'll do | Build | Runs |
| -- | ------- | -------------- | ----- | ---- |
| 29 | [Customer-managed keys](cmk/) | Your encryption key in your own KMS; revoke it and every project goes dark. The kill-switch is yours. (Explainer.) | 🟢 | live |
| 30 | [Data API (REST)](data-api/) | Your table as an auto-generated, PostgREST-compatible REST API, authenticated by Databricks OAuth. | 🟢 | live |

## Capstone

| # | Journey | What you'll do | Build | Runs |
| -- | ------- | -------------- | ----- | ---- |
| 31 | [Put an app on it](capstone-app/) | Build and deploy a small React + FastAPI app on Databricks Apps over the factory you built. Lakebase as the app backend. | 🟢 | live |

---

**Progress:** 31 of 31 written · 4 proven on a live run (⭐: branch-the-brain, break-and-rewind,
scale-to-zero, write-to-analytics). Live verification continues journey by journey. This table is
the source of truth for both order and build status.

*The journey slugs mirror the pitch app's journey ids in
`../lakebase-pitch/frontend/src/journeys.ts`. To add or reorder a journey, edit this table; do
not renumber the folders.*
