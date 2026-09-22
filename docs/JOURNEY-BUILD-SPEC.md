# Journey build spec (for contributors and build agents)

How to build a journey folder so it matches the rest of the workshop. Read this, then read the
finished exemplar at [`../journeys/branch-the-brain/`](../journeys/branch-the-brain/) and copy
its shape exactly.

## Where things live (colocation by ownership)

Everything specific to a journey lives IN that journey's folder: its four docs, its notebooks,
and its script. `common/` holds ONLY what is shared across journeys (`lakebase.py`, `provision.py`,
`branch.py`, `load_factory.py`, `factory_schema.sql`, `factory_seed.sql`). A journey never reaches
into `common/` for its own artifact; it reaches in only for the shared helper.

A journey script imports the shared helper with a path bootstrap at the top:

```python
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "common", "scripts"))
from lakebase import connect, run_sql
```

## The primary artifact is a STEP-BY-STEP NOTEBOOK, not a run-it-all script

A workshop is for learning, so the learner runs ONE step at a time and sees each result before
moving on. The main artifact per journey is a teaching notebook, in BOTH formats, in the journey
folder:

- `<slug>.ipynb` — a Jupyter notebook. Pattern per step: a markdown cell ("Step N: what we do and
  why"), then a code cell doing JUST that one operation, then the learner runs it and reads the
  output before the next step. Narrate; don't dump.
- `<slug>_databricks.py` — the same flow as a Databricks notebook (`# Databricks notebook source`,
  cells separated by `# COMMAND ----------`, markdown via `# MAGIC %md`), importable into a
  workspace.

The all-in-one `<slug>.py` script stays as an OPTION ("just run the whole thing"), not the norm.
Its `--step` flags back the notebook's individual steps.

**Show the right interface for each step — SQL, Python, or both, by context.** Do NOT bolt SQL
onto everything; represent each step in its real interface:

- A step that is **a query** (SELECT / UPDATE / CREATE INDEX / EXPLAIN / VACUUM): SQL is the star.
  Databricks: a `%sql` cell runs it directly. Jupyter: show the ```sql in markdown, then a small
  Python cell that runs it via the helper. Learning the SQL is often the real goal, and it proves
  the "just Postgres" point: the learner can copy it into psql, the Lakebase SQL editor, or a BI
  tool.
- A step that is a **control-plane / SDK operation** (fork a branch, provision, scale to zero,
  generate a credential, call a model): there is NO SQL for it. Show the Python (SDK) and, where
  useful, the equivalent `databricks ...` CLI. Never invent a fake SQL statement for a
  control-plane action, that is dishonest, like claiming an interface that does not exist.
- A step that is **both** (run SQL and interpret the result in code): show both.

Judge per step: "what is this operation actually?" Keep any SQL copy-pasteable and real against
the `factory` schema, never pseudocode.

## Deliverables per journey

Each `journeys/<slug>/` folder needs four docs + the step-by-step notebooks + the optional script:

1. **README.md**, book-style. Structure:
   - `# <Title>`
   - A hero block (see below).
   - `## The scenario`, open with a concrete manufacturing situation, NOT a definition.
   - Build the concept with prose; explain the mechanism.
   - `## The wow moment`, the single beat worth watching.
   - `## What you'll do`, a short numbered preview (steps live in instructions.md).
   - `## Prerequisites`, usually just 00-setup; note any journey that must run first.
   - `## Wrapping up`, connect forward to the next journey. Do not restate.
2. **instructions.md**, numbered, copy-paste steps. Each step: what to run + what you should
   see. Reference the runnable artifact; also show the raw SQL so a reader learns it.
3. **expected.md**, the real output/shape per step, plus a "numbers that matter" table. Honest
   timings (see facts below). Use ```text fenced output blocks.
4. **faq.md**, the real errors (auth/refresh-token, missing env var, permission, table not
   found), why they happen, fixes, and a couple of "why did X happen" concept clarifications.

## The hero block (top of every README, right after the H1)

```
> ## What you'll learn
>
> **Key takeaways**
>
> - <aha learning 1, with a real number where it lands>
> - <aha learning 2>
> - <aha learning 3>
>
> **You'll be able to:** <concrete capability>
>
> **Time:** about N minutes  ·  **Status:** live | preview
```

## Acronyms (each journey must read cold)

Because a learner may jump straight to any journey, expand every acronym on its FIRST use within
that journey (in each of the four files, since each is read on its own), then link it to the
glossary. Example: `[row-level security](../../docs/glossary.md) (RLS)`, then use "RLS" after.
Prefer plain words where an acronym is not the actual feature name. Keep names that are names
(JSONB, pgvector, PostGIS) but still glossary-link them once. The glossary is
[`docs/glossary.md`](glossary.md); add any missing term there.

## Voice (from the book's STYLE.md, enforce it)

- Open with a scenario or field anecdote, not a definition.
- Show code, then show what it prints. Never leave output to imagination.
- Callouts as blockquotes with bold labels: `> **Note**`, `> **Tip**`, `> **Warning**`,
  `> **From the field**` (war story / real numbers).
- NO em dashes or en dashes. Use commas, periods, parentheses, "and"/"but".
- NO AI filler (delve, leverage, seamless, robust, unlock, harness, dive into, furthermore).
- Numbers, not adjectives. Name the catch honestly.
- Close with a short "Wrapping up" that connects to the next journey.

## The running example (use these tables, do not invent aviation nouns)

A multi-plant smart factory. Schema in `common/scripts/factory_schema.sql`, seed in
`factory_seed.sql`. Core tables: `plant`, `machine`, `sensor_reading`, `product`, `part`,
`bom_edge` (the BOM tree), `work_order`, `operation` (routing/scheduling), `supplier`,
`warehouse`, `inventory`, `part_supplier`, `maintenance_log`, `agent_memory`. Journeys that need
scale (pg-explain, pg-index, pg-partition) or an extension (pgvector, PostGIS) create their own
data/columns on top of the seed, self-contained, and clean up or use their own tables.

## Connecting (every runnable artifact uses the shared helper)

```python
from lakebase import connect, run_sql   # common/scripts/lakebase.py
with connect() as conn:                  # connects to the learner's branch via env vars
    with conn.cursor() as cur:
        cur.execute("SELECT ...")
```

Env vars the helper reads: `LB_PROFILE`, `LB_PROJECT`, `LB_BRANCH`, `LB_SCHEMA` (all from
00-setup). Never hard-code hosts, profiles, or instance names. See `docs/lakebase-sdk.md`.

## Verified facts to reuse (do not re-derive; keep timings honest)

- Object model: Project > Branch > Endpoint > Database > Schema > Tables.
- create_project API ~0.8s; project ACTIVE ~3.7s. create_branch API ~0.7s; branch ACTIVE ~2.4s.
  connect + SELECT 1 ~200ms. Say "in seconds"; the "sub-500ms" figure is only the copy-on-write
  metadata accept, not end-to-end. Never fake a number; if you didn't measure it, describe the
  shape ("single-digit milliseconds", "a couple of seconds") and label it.
- Endpoint readiness is `status.current_state == 'ACTIVE'` (NOT `.state`).
- preview journeys (pg-cdc): logical decoding is roadmap on Lakebase; label it clearly and give
  the honest Postgres-capability preview, not a false "live on Lakebase" claim.

## Source material (mirror structure, re-map nouns to manufacturing)

The pitch app `../lakebase-pitch` has the real SQL/story: `backend/story.py`,
`backend/*_service.py`, `frontend/src/cannedQueries.ts`, `frontend/src/journeys.ts` (the beats
per journey). The book `../lakebase-book/lb-book` has conceptual explanations. Reuse both; swap
aviation nouns (aircraft/tail/engine) for factory nouns (machine/part/work order).

## Build status

When a journey's four files + artifact all exist, set its Build column in
`journeys/README.md` to 🟢 and update the progress line.
