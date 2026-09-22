# Journey build spec (for contributors and build agents)

How to build a journey folder so it matches the rest of the workshop. Read this, then read the
finished exemplar at [`../journeys/branch-the-brain/`](../journeys/branch-the-brain/) and copy
its shape exactly.

## Deliverables per journey

Each `journeys/<slug>/` folder needs four files, plus at least one runnable artifact in
`common/scripts/` (a `<slug_with_underscores>.py`) or `common/notebooks/`:

1. **README.md** — book-style. Structure:
   - `# <Title>`
   - A hero block (see below).
   - `## The scenario` — open with a concrete manufacturing situation, NOT a definition.
   - Build the concept with prose; explain the mechanism.
   - `## The wow moment` — the single beat worth watching.
   - `## What you'll do` — a short numbered preview (steps live in instructions.md).
   - `## Prerequisites` — usually just 00-setup; note any journey that must run first.
   - `## Wrapping up` — connect forward to the next journey. Do not restate.
2. **instructions.md** — numbered, copy-paste steps. Each step: what to run + what you should
   see. Reference the runnable artifact; also show the raw SQL so a reader learns it.
3. **expected.md** — the real output/shape per step, plus a "numbers that matter" table. Honest
   timings (see facts below). Use ```text fenced output blocks.
4. **faq.md** — the real errors (auth/refresh-token, missing env var, permission, table not
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

## Voice (from the book's STYLE.md — enforce it)

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
