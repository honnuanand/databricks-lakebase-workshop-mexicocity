# Agent memory, expected results

Use this to check your run. The exact responses will differ slightly (Claude varies), but the
*shape* and timing are what matter: the seed inserts cleanly, the agents append their turns,
and the table reads back with all the rows in order.

## Step 1, table check

```text
0
```

Or a small count if you ran this before. Either is fine; the script is idempotent.

## Step 2, seed

```text
(1, 'default', 'sess-01', 'fraud_advisor', 'assistant', 'ACCT-100240: card-not-present spike overnight, anomaly score 8.7. Keep on watch, do not release the hold until cardholder is reached.', ...)
```

One row inserted.

## Step 3, fraud advisor

```text
Fraud Advisor sees prior memory:
  - ACCT-100240: card-not-present spike overnight, anomaly score 8.7. Keep on watch, do not release the hold until cardholder is reached.

Fraud Advisor response:
ACCT-100240 is not cleared. An anomaly score of 8.7 on an overnight card-not-present spike is a strong fraud signal. Keep the hold in place and verify the recent charges with the cardholder before releasing any funds.
```

The exact wording varies. The key is that:
1. The agent saw the seeded memory (the fraud note).
2. It generated a response grounded in that note.
3. The response appeared in the output.

After this step, the memory table should have 3 rows: the seed, the user question, and the
assistant response.

## Step 4, ops assistant

```text
Ops Assistant sees prior memory:
  - ACCT-100240: card-not-present spike overnight, anomaly score 8.7. Keep on watch, do not release the hold until cardholder is reached.
  - fraud_advisor (assistant): ACCT-100240 is not cleared. An anomaly score of 8.7...

Ops Assistant response:
I will keep the hold on ACCT-100240 in place and not release funds, in line with the fraud advisor's determination. I will contact the cardholder to confirm the overnight charges before any further action.
```

Again, the wording varies. The key is:
1. The ops assistant read both the seeded note AND the fraud advisor's prior response.
2. It responded based on that context.
3. The two agents never directly messaged; they only read/wrote the shared table.

After this step, the memory table should have 5 rows.

## Step 5, full memory table

```text
(1, 'default', 'sess-01', 'fraud_advisor', 'assistant', 'ACCT-100240: card-not-present spike overnight, anomaly score 8.7. Keep on watch...', ...)
(2, 'default', 'sess-01', 'ops_assistant', 'user', 'Can we release the hold on ACCT-100240, or does it stay frozen?', ...)
(3, 'default', 'sess-01', 'fraud_advisor', 'assistant', 'ACCT-100240 is not cleared. An anomaly score of 8.7...', ...)
(4, 'default', 'sess-01', 'ops_assistant', 'user', 'Can we release the hold on ACCT-100240, or does it stay frozen?', ...)
(5, 'default', 'sess-01', 'ops_assistant', 'assistant', 'I will keep the hold on ACCT-100240 in place...', ...)
```

All rows in order, with timestamps increasing. This is the agents' shared brain as plain SQL.

## Full run

Running `python agent_memory.py` with no arguments prints the whole story:

```text
Seeding shared memory with a fraud note...
  Seed row: (1, 'default', 'sess-01', 'fraud_advisor', 'assistant', 'ACCT-100240: card-not-present spike overnight, anomaly score 8.7. Keep on watch, do not release the hold until cardholder is reached.')

1. Fraud Advisor turn:
  Prior memory (1 row):
    - ACCT-100240: card-not-present spike overnight, anomaly score 8.7. Keep on watch...
  Question: Is ACCT-100240 cleared, or do we freeze it for suspected fraud?
  Response: ACCT-100240 is not cleared. An anomaly score of 8.7 on an overnight spike...
  Memory after: 3 rows

2. Ops Assistant turn:
  Prior memory (3 rows):
    - ACCT-100240: card-not-present spike overnight, anomaly score 8.7. Keep on watch...
    - fraud_advisor (assistant): ACCT-100240 is not cleared. An anomaly score of 8.7...
    - ops_assistant (user): Is ACCT-100240 cleared, or do we freeze it for suspected fraud?
  Response: I will keep the hold on ACCT-100240 in place and not release funds...
  Memory after: 5 rows

Done. Both agents wrote to and read from the same governed table.
```

## The numbers that matter

| What | Expected | Why it matters |
| ---- | -------- | -------------- |
| seed insert | 1 row | shared memory initialized with context |
| fraud advisor appends | 2 rows (user + response) | agent writes are durable |
| ops assistant reads + sees all prior | 3 rows before its turn | agent reads are consistent |
| ops assistant appends | 2 rows (user + response) | second agent can also write |
| total rows after both agents | 5 rows | shared memory is a real table, not a cache |
| FM API latency per agent | 1-3 seconds | single-hop, no orchestration |

> **From the field**
> Real agent deployments vary the memory schema (add fields like `session_id`, `namespace`,
> error flags, metadata), but the pattern stays the same: one table is the read-write link
> between agents, governed as a first-class asset. No Redis, no vector store, no message
> queue. The database IS the agent memory system.
