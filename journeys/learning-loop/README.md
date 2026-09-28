# Human-in-the-loop

> ## What you'll learn
>
> **Key takeaways**
>
> - An AI extracts structured data from free-text maintenance write-ups with a confidence
>   score all in one SQL table, live.
> - High-confidence extractions auto-accept; uncertain ones route to a human review queue in
>   the same table.
> - Corrections write back atomically: the operational state and the audit trail are one
>   update, not two systems.
> - Analytics on the *same governed table* measure accuracy and drift, the signal that
>   would train the next model iteration.
>
> **You'll be able to:** feed maintenance write-ups to Claude, watch it extract system/defect/action
> with a confidence score, see high-confidence entries auto-accept and low-confidence route to
> a human review queue, and measure the AI's accuracy from plain SQL.
>
> **Time:** about 25 minutes  ·  **Status:** live

## The scenario

Your factory has decades of free-text maintenance write-ups. Engineers write them in a hurry:
"Hydraulic line to the bearing housing leaking on the press downstroke, isolated the line,
monitor pressure." Another one: "Vibration, something off, maybe bearings? Take a look." A third:
"CNC spindle running hot, thermal alarm at 71C, coolant flow low, replace pump at next PM."

The operations team wants to extract the key facts from each write-up: which subsystem broke,
what was the defect, what action was taken. That's normally a human job, or a model that gets it
right 70% of the time and is wrong enough that no one trusts the output.

On Lakebase, the model scores its own confidence in the extraction. High-confidence entries
(e.g., a clear write-up with standard terminology) auto-accept and flow to operations. Uncertain
ones (e.g., a vague note like "something off with the thing on the right side?") route to an
engineer's review queue. When the engineer corrects it, the correction writes back atomically:
one SQL row updated with both the final answer and the correction timestamp. No two systems.
The analytics team then reads the same table and measures: how often did the model get high-confidence
entries right? How many low-confidence ones did humans need to fix? That signal goes straight to
the ML team.

## What a learning loop actually is

The loop has four steps, all on one table:

1. **Extract**: Claude reads a write-up, pulls out system/defect/action, and scores how
   confident it is (0-1).
2. **Route**: if confidence > 0.75, status = `auto_accepted`; else status = `needs_review`.
3. **Correct**: a human reviewer reads the uncertain ones, optionally changes the extraction,
   updates the row with `status = corrected` and a timestamp.
4. **Learn**: analytics count by status and confidence; track accuracy over time. The signal
   feeds the next model iteration.

All four steps read and write the same table. The database enforces atomicity: a correction
doesn't lose the AI's original extraction; it adds a corrected version in the same row with a
timestamp.

## The wow moment

The beat worth watching: you feed 5 maintenance write-ups to Claude. It extracts 5 extractions
with varying confidence (some clear, some ambiguous). You see 3 auto-accept immediately, 2
stay in the review queue. A human approves one, fixes the other. You query the table and see all
10 facts (the AI's + the human corrections) with timestamps and lineage in Unity Catalog. One
table is the operational store, the review queue, the audit trail, and the analytics source.

## What you'll do

1. Check the `maintenance_log` table structure (see factory schema).
2. Seed it with 5 real maintenance write-ups (messy, intentionally ambiguous on some).
3. Run Claude extraction on each: model gets system/defect/action + confidence.
4. See the auto-accept/review-queue split.
5. Simulate a human correction on one uncertain entry.
6. Query analytics: count extractions by status, accuracy of high-confidence vs. corrected.

Full copy-paste steps are in [`instructions.md`](instructions.md); the exact output to check
against is in [`expected.md`](expected.md).

## Prerequisites

Finish [`../../00-setup/`](../../00-setup/) so you have a branch and can connect. You'll need a
Foundation Model API endpoint (the default `databricks-claude-opus-4-8` is assumed). This journey
builds on the memory and work tables from prior journeys, but you can run it standalone.

## Wrapping up

You've now seen the full agentic loop: memory, work, and learning. The last AI journey goes
deeper into a different capability: `pg_vector`. Instead of extracting text, you'll embed it,
find similar items by cosine distance in the same transaction, and use vector search for
operational decisions. That's [Operational vectors](../pg-vector/).
