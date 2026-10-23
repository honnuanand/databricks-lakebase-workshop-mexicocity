# Isolation & locking

> ## What you'll learn
>
> **Key takeaways**
>
> - When two sessions update the same row, Postgres serializes them: the second waits on a row lock held by the first.
> - You can watch this live: Session A holds a lock; Session B's update blocks, visible in `pg_stat_activity` with `wait_event_type=Lock`.
> - When A commits, B proceeds. Both writes land in order; no lost update, no dirty read. Isolation you can trust.
>
> **You'll be able to:** open two real connections to your branch, demonstrate row-level locking and blocking, and watch a lock release trigger the blocked session.
>
> **Time:** about 8 minutes  ·  **Status:** live

## The scenario

Two tellers at different branches are processing concurrent transactions on the same account's available credit at the exact same time. The account has 10,000 units of available credit. Teller A (at BR-CDMX) processes a debit reducing available credit; Teller B (at BR-MTY) processes another debit on the same account.

If Postgres is handling this, what happens?
- Session A (Teller at BR-CDMX): BEGIN, UPDATE (reduce available credit by 500), holds transaction open.
- Session B (Teller at BR-MTY): UPDATE (reduce available credit by 2,500), tries to apply... and **waits**, blocked on Session A's row lock.
- Session A: COMMIT. A's lock releases.
- Session B: instantly proceeds, applies its update.

Result: available_credit = 10,000 - 500 - 2,500 = 7,000. Both writes landed; neither was lost. No corruption, no conflict resolution code, no explicit locks in the application. Postgres's isolation handled it.

This journey demonstrates it live with two real connections.

## The wow moment

You open two connections to your branch. Connection A updates a row and holds the transaction open. You run an UPDATE on Connection B, and it blocks. A counter shows B waiting. Then you commit A, and B instantly proceeds. You watch the lock release trigger the blocked session. Concurrency you can trust.

## What you'll do

1. Create a demo row (account with 10,000 available credit).
2. Session A: BEGIN + UPDATE (reduce by 500), hold the transaction.
3. Session B: try to UPDATE (reduce by 2,500), it blocks.
4. Show the block (confirmed by the script waiting).
5. Session A: COMMIT. Session B proceeds immediately.
6. Show the final result: both updates landed, no loss.

Full copy-paste steps are in [`instructions.md`](instructions.md); the exact output is in [`expected.md`](expected.md).

## Prerequisites

Finish [`../../00-setup/`](../../00-setup/) so you have a branch and can connect. Nothing else; this journey is self-contained.

## Wrapping up

This is the foundation of why operational systems trust Postgres: ACID guarantees, row-level locking, snapshot isolation. No lost updates, no dirty reads. The next journey [`../pg-partition/`](../pg-partition/) scales the data: how does a single Postgres table stay fast as it grows to billions of rows? The journey after that explores [Multi-version concurrency control](../pg-mvcc/), the mechanism that makes all of this possible.
