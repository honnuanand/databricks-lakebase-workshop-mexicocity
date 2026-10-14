# Facilitator agenda: pick the journeys for your room

You will rarely run all 31 journeys. This page helps you choose a subset that fits your audience
and the time you have. Pick a ready-made track, or build your own from the persona matrix at the
bottom.

Two rules for any agenda:

- **[`00-setup/`](../00-setup/) always comes first** (about 20 minutes). It provisions each
  learner's branch and loads the bank. Nothing runs without it.
- **Budget about 15 minutes per journey** hands-on (10 for a quick one, 20 for the AI or app
  journeys). Add a few minutes between journeys for questions.

> **Tip**
> Every learner works on their own zero-copy branch, so a room of any size runs in parallel with
> no contention. The one exception is [Scale to zero](../journeys/scale-to-zero/), which stops
> shared instance compute; run it as a facilitator-led demo, not a whole-room exercise, unless
> each learner has their own instance.

## Ready-made tracks

### Taster (about 60 minutes)

The "why Lakebase is different" highlights for a mixed or executive-leaning room. Facilitator
can drive; light hands-on.

`00-setup` → [Branch the brain](../journeys/branch-the-brain/) →
[Break it, then rewind](../journeys/break-and-rewind/) →
[One copy, both directions](../journeys/write-to-analytics/) →
[Agent memory](../journeys/agent-memory/)

### Oracle / SQL Server migration, for DBAs (about half a day)

For a data-team or DBA room asking "will my SQL and my instincts port?" Heavy on the Postgres
track and the migration story.

`00-setup` → [SQL you already know](../journeys/pg-sql-parity/) →
[JSON documents](../journeys/pg-json/) → [Watch the planner](../journeys/pg-explain/) →
[One engine, every index](../journeys/pg-index/) → [MVCC and the WAL](../journeys/pg-mvcc/) →
[Isolation and locking](../journeys/pg-iso/) → [Row-level security](../journeys/pg-rls/) →
[Tune the planner](../journeys/pg-perf/) → [Fits your landscape](../journeys/pg-integration/)

### AI / agent builders (about 90 minutes)

For teams building agents and AI features who want one governed database behind it all.

`00-setup` → [Agent memory](../journeys/agent-memory/) →
[The agent does the work](../journeys/agentic-work/) →
[Human-in-the-loop](../journeys/learning-loop/) →
[Operational vectors](../journeys/pg-vector/) →
[Branch the brain](../journeys/branch-the-brain/) →
[Feature store, served online](../journeys/pg-features/)

### Platform / architect, central IT (about 90 minutes)

For the people who decide whether Lakebase fits the landscape: cost, governance, operations,
integration.

`00-setup` → [Scale to zero](../journeys/scale-to-zero/) (demo) →
[Break it, then rewind](../journeys/break-and-rewind/) →
[One copy, both directions](../journeys/write-to-analytics/) →
[Fits your landscape](../journeys/pg-integration/) →
[Customer-managed keys](../journeys/cmk/) → [Data API (REST)](../journeys/data-api/)

### App developers (about 90 minutes)

For developers who will build on Lakebase: the Postgres features they will actually reach for,
plus putting an app on top.

`00-setup` → [JSON documents](../journeys/pg-json/) →
[Operational vectors](../journeys/pg-vector/) → [Search, three ways](../journeys/pg-search/) →
[No double-booking](../journeys/pg-booking/) → [Data API (REST)](../journeys/data-api/) →
[Put an app on it](../journeys/capstone-app/)

### Security and governance (about 60 minutes)

`00-setup` → [Row-level security](../journeys/pg-rls/) →
[Customer-managed keys](../journeys/cmk/) →
[Fits your landscape](../journeys/pg-integration/) (Unity Catalog governance) →
[Break it, then rewind](../journeys/break-and-rewind/)

### Full hands-on (a full day)

Run the whole spine in TOC order: the Lakebase-difference track, the AI track, a chosen slice of
the Postgres-power track, the knowledge-graph track, security, and the capstone. Use the per-track
groupings in the [journeys index](../journeys/) and time-box each block.

## The everyone-sees-these set

If you only have time for a handful and the room is mixed, these four land the core message:

1. [Branch the brain](../journeys/branch-the-brain/), branching a live database in seconds.
2. [Break it, then rewind](../journeys/break-and-rewind/), point-in-time recovery as a normal operation.
3. [One copy, both directions](../journeys/write-to-analytics/), operational and analytical on one copy.
4. [Agent memory](../journeys/agent-memory/), the app store and the agent backend are one database.

## Build your own: persona matrix

Each journey is tagged with the audiences it serves best. Pick your primary persona, take its
journeys, and trim to your time budget. (Tags mirror the pitch app's journey registry.)

| Journey | Best for | Theme | Runs |
| ------- | -------- | ----- | ---- |
| [Branch the brain](../journeys/branch-the-brain/) | AI/ML, DataEng, Engineer | Agility, Cost, AI | live |
| [Break it, then rewind](../journeys/break-and-rewind/) | DBA, Engineer, DataEng | Agility, Governance | live |
| [Scale to zero](../journeys/scale-to-zero/) | Engineer, DBA, DataEng | Cost, Simplicity | live |
| [One copy, both directions](../journeys/write-to-analytics/) | DataEng, Engineer, AppDev | Simplicity, Performance | live |
| [Fits your landscape](../journeys/pg-integration/) | Engineer, DataEng, DBA | Migration, Governance | live |
| [Agent memory](../journeys/agent-memory/) | AI/ML, AppDev, Engineer | AI, Governance | live |
| [The agent does the work](../journeys/agentic-work/) | AI/ML, AppDev, Engineer | AI, Simplicity | live |
| [Human-in-the-loop](../journeys/learning-loop/) | AI/ML, AppDev, Engineer | AI, Governance | live |
| [Operational vectors](../journeys/pg-vector/) | AI/ML, AppDev, Engineer | AI, Migration | live |
| [SQL you already know](../journeys/pg-sql-parity/) | DBA, DataEng, AppDev | Migration, Performance | live |
| [JSON documents](../journeys/pg-json/) | AppDev, DBA | Migration, Agility | live |
| [Geospatial](../journeys/pg-geo/) | AppDev, DBA, Engineer | Migration, Performance | live |
| [Search, three ways](../journeys/pg-search/) | AppDev, DataEng, AI/ML | Migration, AI | live |
| [Row-level security](../journeys/pg-rls/) | Security, DBA, AppDev | Governance, Migration | live |
| [No double-booking](../journeys/pg-booking/) | AppDev, DBA, Engineer | Migration, Simplicity | live |
| [Watch the planner](../journeys/pg-explain/) | DBA, AppDev, Engineer | Performance, Migration | live |
| [Tune the planner](../journeys/pg-perf/) | DBA, Engineer | Performance, Migration | live |
| [One engine, every index](../journeys/pg-index/) | DBA, Engineer, AppDev | Migration, Performance | live |
| [MVCC and the WAL](../journeys/pg-mvcc/) | DBA, Engineer | Migration, Performance | live |
| [Isolation and locking](../journeys/pg-iso/) | DBA, Engineer, AppDev | Migration, Performance | live |
| [Scale-out: partitioning](../journeys/pg-partition/) | DBA, DataEng, Engineer | Performance, Migration | live |
| [Postgres in your browser](../journeys/pg-lite/) | AppDev, AI/ML, DataEng | Simplicity, AI | live |
| [Feature store, served online](../journeys/pg-features/) | AI/ML, DataEng, AppDev | AI, Performance | live |
| [One query, every type](../journeys/pg-one-database/) | DBA, Engineer | Simplicity, Migration | live |
| [Your commits are a change feed](../journeys/pg-cdc/) | AppDev, DBA, DataEng | Simplicity, Agility | preview |
| [Build the knowledge graph](../journeys/kg-build/) | Engineer, DataEng, AI/ML | Governance, AI | live |
| [Ask the graph in SPARQL](../journeys/kg-sparql/) | Engineer, DataEng, AI/ML | Agility, Governance | live |
| [The graph reasons](../journeys/kg-infer/) | Engineer, AI/ML, DataEng | AI, Governance | live |
| [Customer-managed keys](../journeys/cmk/) | Security, Engineer, DBA | Governance | live |
| [Data API (REST)](../journeys/data-api/) | AppDev, AI/ML, Engineer | Simplicity, AI | live |
| [Put an app on it](../journeys/capstone-app/) | AppDev, Engineer | (capstone) | live |

## Before the room arrives

- Confirm each learner (or the shared workshop) can reach a Lakebase workspace and has the CLI,
  Python, and the two libraries (see [`00-setup/prereqs.md`](../00-setup/prereqs.md)).
- Decide: does everyone provision their own project, or do you provision one shared project and
  each learner branches off it? For a room, one shared project + per-user branches is simplest.
- If you plan to run [Scale to zero](../journeys/scale-to-zero/), make sure it is your own
  instance, since stopping compute pauses everything on that instance.
- Have the [glossary](glossary.md) link handy to drop in chat for anyone who hits an unfamiliar term.
