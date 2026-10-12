# Human-in-the-loop

> ## What you'll learn
>
> **Key takeaways**
>
> - An AI extracts structured data from free-text fraud and AML case notes with a confidence
>   score, all in one SQL table, live.
> - High-confidence extractions auto-accept; uncertain ones route to a human analyst's review
>   queue in the same table.
> - Corrections write back atomically: the operational state and the audit trail are one
>   update, not two systems.
> - Analytics on the *same governed table* measure accuracy and drift, the signal that
>   would train the next model iteration.
>
> **You'll be able to:** feed free-text case notes to Claude, watch it extract category/finding/action
> with a confidence score, see high-confidence entries auto-accept and low-confidence route to
> a human analyst, and measure the AI's accuracy from plain SQL.
>
> **Time:** about 25 minutes  ·  **Status:** live

## The scenario

Your bank's fraud and AML teams write free-text case notes all day. Analysts write them in a
hurry: "Cardholder reports three card-not-present charges to an overseas merchant they do not
recognize; velocity spike overnight. Suspect card compromise, recommend freeze and reissue."
Another one: "Something looks off on the wires out of this account, maybe layering? take a
look." A third: "Large outbound wire to a new beneficiary in a high-risk jurisdiction, just
under the reporting threshold. Structuring pattern? Needs AML review."

The investigations team wants to extract the key facts from each note: which category (fraud,
AML, dispute), what was the finding, what action was taken or recommended. That's normally a
human job, or a model that gets it right 70% of the time and is wrong enough that no one trusts
the output.

On Lakebase, the model scores its own confidence in the extraction. High-confidence entries
(a clear note with standard terminology) auto-accept and flow to the case management queue.
Uncertain ones (a vague note like "something looks off, maybe layering?") route to a human
analyst's review queue. When the analyst corrects it, the correction writes back atomically:
one SQL row updated with both the final answer and the correction timestamp. No two systems.
The analytics team then reads the same table and measures: how often did the model get
high-confidence entries right? How many low-confidence ones did humans need to fix? That signal
goes straight to the ML team.

## What a learning loop actually is

The loop has four steps, all on one table:

1. **Extract**: Claude reads a case note, pulls out category/finding/action, and scores how
   confident it is (0-1).
2. **Route**: if confidence > 0.75, status = `auto_accepted`; else status = `needs_review`.
3. **Correct**: a human analyst reads the uncertain ones, optionally changes the extraction,
   updates the row with `status = corrected` and a timestamp.
4. **Learn**: analytics count by status and confidence; track accuracy over time. The signal
   feeds the next model iteration.

All four steps read and write the same table. The database enforces atomicity: a correction
doesn't lose the AI's original extraction; it updates the row in place with a timestamp.

## The wow moment

The beat worth watching: you feed 5 case notes to Claude. It extracts 5 structured results with
varying confidence (some clear, some ambiguous). You see 2 auto-accept immediately, 3 stay in
the review queue. A human analyst corrects the single lowest-confidence one. You query the table
and see every finding (the AI's plus the human correction) with timestamps and lineage in Unity
Catalog. One table is the case store, the review queue, the audit trail, and the analytics source.

## What you'll do

1. Check the `case_note` table structure (see the bank schema).
2. Seed it with 5 real fraud/AML case notes (messy, intentionally ambiguous on some).
3. Run Claude extraction on each: model gets category/finding/action + confidence.
4. See the auto-accept/review-queue split.
5. Simulate a human correction on the lowest-confidence uncertain entry (picked dynamically).
6. Query analytics: count extractions by status, accuracy of high-confidence vs. corrected.

Full copy-paste steps are in [`instructions.md`](instructions.md); the exact output to check
against is in [`expected.md`](expected.md).

## Prerequisites

Finish [`../../00-setup/`](../../00-setup/) so you have a branch and can connect. You'll need a
Foundation Model API endpoint (the default `databricks-claude-opus-4-8` is assumed, override it
with `FM_ENDPOINT`). This journey builds on the memory and account tables from prior journeys,
but you can run it standalone.

## Wrapping up

You've now seen the full agentic loop: memory, work, and learning. The last AI journey goes
deeper into a different capability: `pg_vector`. Instead of extracting text, you'll embed it,
find similar items by cosine distance in the same transaction, and use vector search for
operational decisions. That's [Operational vectors](../pg-vector/).
