# No settlement overlap

> ## What you'll learn
>
> **Key takeaways**
>
> - A [GiST](../../docs/glossary.md) exclusion constraint prevents overlapping settlement time windows on the same account from ever existing. If two settlements' time ranges overlap for the same account, the database rejects the second one, atomically.
> - This is stronger than app-layer checks ("read settlement calendar, check for clash, then insert"). Race conditions can't happen because the constraint is enforced in the database engine, not in app code.
> - The numbers that matter: an exclusion constraint adds negligible overhead, under 1 millisecond per INSERT. The guarantee is a database-enforced contract.
>
> **You'll be able to:** use a [GiST](../../docs/glossary.md) exclusion constraint on tstzrange (time ranges) to guarantee no two settlements ever overlap on the same account, no matter how many requests race.
>
> **Time:** about 20 minutes  ·  **Status:** live

## The scenario

Settlement operations at a bank: you have two requests to settle transactions on account CTA-100240. One is from 2 p.m. to 3 p.m., the other is from 2:30 p.m. to 3:30 p.m. The time ranges overlap. Both requests hit the system at the same time. The app reads the settlement log, sees the first settlement is there, and the second request also read the log before the first one was written, so the second request also thinks the slot is available and INSERTs.

Now you have two overlapping settlements on the same account, which violates settlement rules. The normal answer is transaction isolation (SERIALIZABLE mode), but that's expensive. The better answer is a constraint: make it impossible for overlapping settlements to exist. The database rejects the second INSERT before it can happen.

## Why GiST exclusion matters

[GiST](../../docs/glossary.md) exclusion constraints are one of Postgres' hidden superpowers. They're not well-known, but they solve a huge class of problems: no overlapping settlements, no double-booking, no competing reservations. The constraint runs in the database and cannot be bypassed, the only way to insert an overlapping row is to successfully delete the conflicting row first, which requires a transaction that sees both rows (impossible for concurrent requests).

## The wow moment

You insert a settlement into a busy account's timeline. You then try to insert an overlapping settlement. The database rejects it instantly with a constraint violation. No app code can accidentally allow it. The guarantee is at the database level, not delegated to the app.

## What you'll do

1. Inspect the settlement table and its time ranges (starts_at, ends_at).
2. Create a [GiST](../../docs/glossary.md) exclusion constraint on the settlement table: `EXCLUDE USING gist (account_id WITH =, tstzrange(starts_at, ends_at) WITH &&)`.
3. Try to insert an overlapping settlement and see the constraint violation.
4. Verify the constraint is being used with EXPLAIN.

Full copy-paste steps are in [`instructions.md`](instructions.md); the exact output and reference numbers are in [`expected.md`](expected.md).

## Prerequisites

Finish [`../../00-setup/`](../../00-setup/) so you have a branch with the bank schema loaded. Lakebase Postgres 15+ is required for full GiST support; earlier versions may have limitations.

## Wrapping up

Exclusion constraints are a form of database-enforced correctness. They're part of a broader theme in Postgres: making it impossible to write incorrect code. The next journey investigates the opposite question: [Watch the planner](../pg-explain/), how does Postgres decide what algorithm to use for your query?
