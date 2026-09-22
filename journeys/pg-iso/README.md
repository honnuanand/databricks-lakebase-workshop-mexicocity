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

You're managing factory maintenance slots. A machine has 10 slots available for maintenance work. Two independent schedulers are running, one in Detroit, one in Shanghai, and they both want to book a slot on the same machine, right now.

If Postgres is handling this, what happens?
- Session A (Detroit): BEGIN, UPDATE (book 1 slot), holds transaction open.
- Session B (Shanghai): UPDATE (book 5 slots), tries to apply... and **waits**, blocked on Session A's row lock.
- Session A: COMMIT. A's lock releases.
- Session B: instantly proceeds, applies its update.

Result: slots = 10 - 1 - 5 = 4. Both writes landed; neither was lost. No corruption, no conflict resolution code, no explicit locks in the application. Postgres's isolation handled it.

This journey demonstrates it live with two real connections.

## The wow moment

You open two connections to your branch. Connection A updates a row and holds the transaction open. You run an UPDATE on Connection B, and it blocks. A counter shows B waiting. Then you commit A, and B instantly proceeds. You watch the lock release trigger the blocked session. Concurrency you can trust.

## What you'll do

1. Create a demo row (machine with 10 maintenance slots).
2. Session A: BEGIN + UPDATE (book 1 slot), hold the transaction.
3. Session B: try to UPDATE (book 5 slots), it blocks.
4. Show the block (confirmed by the script waiting).
5. Session A: COMMIT. Session B proceeds immediately.
6. Show the final result: both updates landed, no loss.

Full copy-paste steps are in [`instructions.md`](instructions.md); the exact output is in [`expected.md`](expected.md).

## Prerequisites

Finish [`../../00-setup/`](../../00-setup/) so you have a branch and can connect. Nothing else; this journey is self-contained.

## Wrapping up

This is the foundation of why operational systems trust Postgres: ACID guarantees, row-level locking, snapshot isolation. No lost updates, no dirty reads. The next journey [`../pg-partition/`](../pg-partition/) scales the data: how does a single Postgres table stay fast as it grows to billions of rows? The journey after that explores [Multi-version concurrency control](../pg-mvcc/), the mechanism that makes all of this possible.
