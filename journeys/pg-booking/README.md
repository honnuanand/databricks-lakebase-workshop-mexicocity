# No double-booking

> ## What you'll learn
>
> **Key takeaways**
>
> - A GiST exclusion constraint prevents overlapping bookings (operations on the same machine or resource) from ever existing. If two bookings' time ranges overlap for the same machine, the database rejects the second one, atomically.
> - This is stronger than app-layer checks ("read calendar, check for clash, then insert"). Race conditions can't happen because the constraint is enforced in the database engine, not in app code.
> - The numbers that matter: an exclusion constraint adds negligible overhead (< 1 millisecond per INSERT). The guarantee is a database-enforced contract.
>
> **You'll be able to:** use a GiST exclusion constraint on tstzrange (time ranges) to guarantee no two operations ever overlap on the same machine, no matter how many requests race.
>
> **Time:** about 20 minutes  ·  **Status:** live

## The scenario

Production scheduling: you have two requests to run operations on machine M-204. One is 2 p.m. to 3 p.m., the other is 2:30 p.m. to 3:30 p.m. The time ranges overlap. Both requests hit the app at the same time. The app reads the calendar, sees the first operation is there, and... the second request also read the calendar before the first one was written, so the second request also thinks the slot is free and INSERTs.

Now you have two overlapping operations on the same machine. The normal answer is transaction isolation (SERIALIZABLE mode), but that's expensive. The better answer is a constraint: make it impossible for overlapping operations to exist. The database rejects the second INSERT before it can happen.

## Why GiST exclusion matters

GiST exclusion constraints are one of Postgres' hidden superpowers. They're not well-known, but they solve a huge class of problems: no double-booking, no overlapping shifts, no competing reservations. The constraint runs in the database and cannot be bypassed, the only way to insert an overlapping row is to successfully delete the conflicting row first, which requires a transaction that sees both rows (impossible for concurrent requests).

## The wow moment

You insert an operation into a busy machine's schedule. You then try to insert an overlapping operation. The database rejects it instantly with a constraint violation. No app code can accidentally allow it. The guarantee is at the database level, not delegated to the app.

## What you'll do

1. Inspect the operation table and its time ranges (starts_at, ends_at).
2. Create a GiST exclusion constraint on the operation table: `EXCLUDE USING gist (machine_id WITH =, tstzrange(starts_at, ends_at) WITH &&)`.
3. Try to insert an overlapping operation and see the constraint violation.
4. Verify the constraint is being used with EXPLAIN.

Full copy-paste steps are in [`instructions.md`](instructions.md); the exact output and reference numbers are in [`expected.md`](expected.md).

## Prerequisites

Finish [`../../00-setup/`](../../00-setup/) so you have a branch with the factory schema loaded. Lakebase Postgres 15+ is required for full GiST support; earlier versions may have limitations.

## Wrapping up

Exclusion constraints are a form of database-enforced correctness. They're part of a broader theme in Postgres: making it impossible to write incorrect code. The next journey investigates the opposite question: [Watch the planner](../pg-explain/), how does Postgres decide what algorithm to use for your query?
