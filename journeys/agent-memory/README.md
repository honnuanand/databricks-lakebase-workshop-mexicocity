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
> **You'll be able to:** set up two agents (fraud_advisor and ops_assistant) that share one
> Lakebase memory table, write a fraud note as one agent and watch the other agent read and
> act on it.
>
> **Time:** about 20 minutes  ·  **Status:** live

## The scenario

You run a retail bank with two AI agents deployed on Model Serving:

- **Fraud Advisor**: reasons about account risk, reads transaction anomaly scores, decides
  whether an account should be cleared or frozen for suspected fraud.
- **Ops Assistant**: handles day-to-day account servicing, answers questions from the branch
  like "can we release the hold on CTA-100240, or does it stay frozen?"

They never talk to each other directly. But the fraud advisor needs to tell the ops assistant
something: "CTA-100240 sent a late-night SPEI transfer of MXN 38,500 to a new beneficiary, anomaly score
hit 8.7. Keep it on watch, do not release the hold until the customer is reached." The ops assistant
needs to know that before it touches the account.

On most systems, the answer is "build a message queue" or "cache the state in Redis and hope
both systems stay in sync." On Lakebase, the answer is simpler: the agents' **only link is a
governed Postgres table in the same database that stores everything else**. One agent appends
a fraud note. The other agent reads it at the start of the next session. No orchestration.
No second system.

## What shared agent memory actually is

In Lakebase, agent memory is a table with a few columns:

```text
id | agent_id      | role      | content                       | created_at
1  | fraud_advisor | assistant | CTA-100240 anomaly 8.7, watch | 2026-10-04 10:00:00
2  | ops_assistant | user      | Can we release the hold?       | 2026-10-04 10:00:15
3  | ops_assistant | assistant | Hold stays, per fraud advisor  | 2026-10-04 10:00:16
```

Each agent can write rows (append its turns). Each agent reads *all* rows on startup to load
context. The database guarantees isolation: the fraud advisor's write is durable before the
ops assistant reads it. The table is governed by Unity Catalog, the agents' shared brain is a
first-class asset, not a black box.

## The wow moment

The beat worth watching: you ask the fraud advisor "Is CTA-100240 cleared, or do we freeze
it?" It answers and writes the answer to the shared memory table. Then you ask the ops
assistant the same question, and it reads the *exact same answer from the same table*, even
though the two agents never sent each other a message. Multi-agent shared state, governed,
with one database call per query.

## What you'll do

1. Connect to your workshop branch and check the `agent_memory` table structure.
2. Seed the table with some initial context (a fraud note from the overnight alert queue).
3. Ask the fraud advisor a question; watch it append its response to the memory table.
4. Ask the ops assistant the same question; watch it read the fraud advisor's note and respond.
5. Query the shared memory table directly: all the turns are plain SQL rows with full lineage
   in Unity Catalog.

Full copy-paste steps are in [`instructions.md`](instructions.md); the exact output to check
against is in [`expected.md`](expected.md).

## Prerequisites

Finish [`../../00-setup/`](../../00-setup/) so you have a branch and can connect. Nothing else;
this journey stands on its own. You'll need a Foundation Model API endpoint (the default
`databricks-claude-opus-4-8` is assumed, override it with `FM_ENDPOINT`). If you don't have
agents deployed, we provide an honest fallback path that shows the pattern without live agent
calls.

## Wrapping up

Once agent memory lives in the database that's also the app store, you stop treating it as a
separate system. The next journey goes deeper: an agent doesn't just remember; it acts, it
reads live account and transaction data with a tool, writes a hold back, and remembers what it
did so it won't repeat itself. That's [The agent does the work](../agentic-work/).
