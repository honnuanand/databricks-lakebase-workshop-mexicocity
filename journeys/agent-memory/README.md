# Agent memory

> ## What you'll learn
>
> **Key takeaways**
>
> - Two independent agents deployed anywhere can share a governed Lakebase table as their
>   only link: one writes, the other recalls and acts on it.
> - Agent memory on a database that's also the app store means no Redis, no vector cache, no
>   separate memory service.
> - Unity Catalog governs the memory table as a first-class asset with lineage and access
>   control.
>
> **You'll be able to:** set up two agents (maintenance_advisor and mes_assistant) that share
> one Lakebase memory table, write a maintenance note as one agent and watch the other agent
> read and act on it.
>
> **Time:** about 20 minutes  ·  **Status:** live

## The scenario

You run a smart factory with two AI agents deployed on Model Serving:

- **Maintenance Advisor**: reasons about machine health, forecasts wear, recommends maintenance
  windows.
- **MES Assistant**: manages production orders, allocates machines, answers operator questions
  like "is M-204 ready to run the next work order?"

They never talk to each other directly. But the maintenance advisor needs to tell the MES
assistant something: "M-204 just had a bearing replaced; it's cleared to run shifts for
another 72 hours." The MES assistant needs to know that before it schedules work.

On most systems, the answer is "build a message queue" or "cache the state in Redis and hope
both systems stay in sync." On Lakebase, the answer is simpler: the agents' **only link is a
governed Postgres table in the same database that stores everything else**. One agent appends
a maintenance note. The other agent reads it at the start of the next session. No orchestration.
No second system.

## What shared agent memory actually is

In Lakebase, agent memory is a table with five columns:

```text
id          | agent_id            | role      | content           | created_at
1           | maintenance_advisor | user      | Check M-204       | 2025-09-22 10:00:00
2           | maintenance_advisor | assistant | M-204 is OK       | 2025-09-22 10:00:05
3           | mes_assistant       | user      | Ready for shifts? | 2025-09-22 10:00:15
4           | mes_assistant       | assistant | Yes, 72h OK       | 2025-09-22 10:00:16
```

Each agent can write rows (append its turns). Each agent reads *all* rows on startup to load
context. The database guarantees isolation: the maintenance advisor's write is durable before
the MES assistant reads it. The table is governed by Unity Catalog, the agents' brain is a
first-class asset, not a black box.

## The wow moment

The beat worth watching: you ask the maintenance advisor "Is M-204 cleared?" It answers and
writes the answer to the shared memory table. Then you ask the MES assistant the same question,
and it reads the *exact same answer from the same table*, even though the two agents never
sent each other a message. Multi-agent shared state, governed, with one database call per
query.

## What you'll do

1. Connect to your workshop branch and check the `agent_memory` table structure.
2. Seed the table with some initial context (a maintenance note from last shift).
3. Ask the maintenance advisor a question; watch it append its response to the memory table.
4. Ask the MES assistant the same question; watch it read the maintenance advisor's note and
   respond.
5. Query the shared memory table directly: all four turns (two per agent) are plain SQL rows
   with full lineage in Unity Catalog.

Full copy-paste steps are in [`instructions.md`](instructions.md); the exact output to check
against is in [`expected.md`](expected.md).

## Prerequisites

Finish [`../../00-setup/`](../../00-setup/) so you have a branch and can connect. Nothing else;
this journey stands on its own. You'll need a Foundation Model API endpoint (the default
`databricks-claude-opus-4-8` is assumed). If you don't have agents deployed, we provide an
honest fallback path that shows the pattern without live agent calls.

## Wrapping up

Once agent memory lives in the database that's also the app store, you stop treating it as a
separate system. The next journey goes deeper: an agent doesn't just remember; it acts, it
reads live data with a tool, writes state changes back, and remembers what it did so it won't
repeat itself. That's [The agent does the work](../agentic-work/).
