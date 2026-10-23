# Branch the brain

> ## What you'll learn
>
> **Key takeaways**
>
> - A Lakebase branch is a full, isolated copy of the database that costs almost nothing to
>   create, because storage is copy-on-write: nothing is duplicated until you change it.
> - The branch's data is ready in well under a second; the compute endpoint you connect to
>   reaches `ACTIVE` in about two seconds. Say "in seconds" and mean it.
> - Diverging on a branch never touches production. Discarding the branch leaves zero storage
>   behind. Fork, experiment, throw away, as cheaply as a git branch, for a live database.
>
> **You'll be able to:** fork your production bank database into a new branch, change an account on
> the branch, prove production is untouched, and discard the branch clean.
>
> **Time:** about 15 minutes  ·  **Status:** live

## The scenario

You run the operational core of a retail and commercial bank. Right now production says account
`CTA-100240` is on `watch` and still open for spending. A fraud analyst wants to try something
risky: freeze the account and watch how the downstream flows react, because an overnight
transaction scored high for fraud. But this is the live operational database. Freezing a live
customer account in production to run an experiment is exactly the kind of thing that pages
someone at 2 a.m.

The normal answer is "spin up a copy of the database." On most systems that means a dump and
restore, or a storage-level clone that takes minutes to stand up and real disk to hold. You do
it rarely, and you feel it every time.

Lakebase's answer is a branch. You fork the whole database, get an isolated copy in seconds,
make your risky change there, and throw it away when you're done. Production never knew.

## What a branch actually is

A branch is copy-on-write. When you create one, Lakebase does not copy your data. It records
that the new branch shares production's storage as of a point in time, and only the pages you
*change* on the branch get written separately. So a branch of a 2 GB database and a branch of a
2 TB database cost about the same to create: close to nothing.

> **Note**
> This is the same mechanism behind point-in-time restore. A branch is "the database as of an
> LSN"; restoring is branching at a past LSN. You'll meet that again in
> [Break it, then rewind](../break-and-rewind/). The write-ahead log position, the LSN, is the
> cursor underneath both. [MVCC and the WAL](../pg-mvcc/) shows it directly.

Here is the object model you're working in. You have your own branch, `u-<name>`, off the shared
`production`. In this journey you fork *your* branch to create a short-lived experiment branch.

```text
Project (bank)
 ├─ production            the protected, shared source
 ├─ u-alex                your working branch (from 00-setup)
 └─ u-alex-exp            the experiment fork you create here, then discard
```

## The wow moment

The beat worth watching: you click create, and a full copy of the database is ready to query on
its own endpoint in about two seconds. Not a progress bar for a clone job. Seconds. Then you set
`CTA-100240` to `frozen` on the fork, read it back changed, switch to production, and read the
same row still on `watch`. Two live databases, one of them forked from the other moments ago,
holding different facts about the same account.

> **From the field**
> The honest number: the branch's *data* is ready almost instantly, the copy-on-write metadata
> is accepted in roughly 400 milliseconds. What takes the extra time is attaching a compute
> endpoint you can connect to, which lands `ACTIVE` in about two seconds in our measurements. So
> "in seconds" is true and defensible. If someone quotes you "sub-500ms end to end," that's the
> metadata step alone, not a queryable database. Compare that to an Aurora fast clone, which
> typically takes several minutes before you can use it.

## What you'll do

1. Look at `CTA-100240` on your branch: it's on `watch`.
2. Fork your branch into an experiment branch, and time how long until it's `ACTIVE`.
3. On the fork, set `CTA-100240` to `frozen`. Read it back changed.
4. Switch to production and read `CTA-100240`, still on `watch`. The divergence lives only on
   the fork.
5. Discard the fork. Confirm it's gone and production is untouched.

Full copy-paste steps are in [`instructions.md`](instructions.md); the exact output and timings
to check against are in [`expected.md`](expected.md).

## Prerequisites

Finish [`../../00-setup/`](../../00-setup/) so you have a branch and can connect. Nothing else;
this journey stands on its own. If you want the SDK calls explained, keep
[`docs/lakebase-sdk.md`](../../docs/lakebase-sdk.md) open.

## Wrapping up

Once branching is this cheap, your instinct changes. You stop treating "make a copy of the
database" as a heavyweight operation you avoid, and start treating it as something you do per
experiment, per pull request, per what-if. The next journey takes that same copy-on-write
machinery and points it at the past: [Break it, then rewind](../break-and-rewind/) deletes live
data and recovers it by branching the database as it was seconds ago.
