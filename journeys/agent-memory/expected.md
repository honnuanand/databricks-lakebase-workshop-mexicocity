# Agent memory, expected results

Use this to check your run. Both agents call a live model (`FM_ENDPOINT`, default
`databricks-claude-opus-4-8`), so their exact words differ on every run. What matters is the
*shape*: the seed inserts cleanly, each agent's answer is grounded in the shared notes, and the
table reads back with all the rows in order. The examples below are from a live run on
2026-10-15.

If the endpoint is unavailable, each agent cell prints
`(FM API unavailable: ...; using fallback simulation)` and uses a fixed reply instead.

## Step 1, seed shared memory

```text
Seeded agent_memory with prior fraud note
```

One row inserted. The cell deletes this session's earlier rows first, so a rerun starts clean.

## Step 2, read prior memory

```text
Prior memory (1 rows):
  fraud_advisor: CTA-100240: late-night SPEI transfer of MXN 38,500 to a new beneficiary, anomaly...
```

## Step 3, fraud advisor

```text
fraud_advisor appended:
  Keep CTA-100240 on hold — per prior notes, the late-night MXN 38,500 SPEI transfer to a new beneficiary (anomaly score 8.7) warrants holding until the customer is reached and verifies the transaction.
```

The wording varies. Check that:
1. The answer is "keep the hold" (not "clear").
2. It cites the note: the SPEI transfer, the 8.7 score, or reaching the customer.

After this step the table has 3 rows: the seed, the question, and the answer.

## Step 4, ops assistant

```text
Full memory for ops assistant (3 rows):
  fraud_advisor: CTA-100240: late-night SPEI transfer of MXN 38,500 to a new beneficiar...
  fraud_advisor: Is CTA-100240 cleared, or do we freeze it for suspected fraud?
  fraud_advisor: Keep CTA-100240 on hold — per prior notes, the late-night MXN 38,500 S...

ops_assistant appended:
  The hold on CTA-100240 stays in place per the fraud advisor's determination — the late-night MXN 38,500 SPEI transfer to a new beneficiary (anomaly score 8.7) must remain held until the customer is reached and verifies the transaction.
```

The ops assistant read both the seed note and the fraud advisor's answer, and defers to it. The
two agents never messaged each other; they only read and wrote the shared table.

## Step 5, final memory

```text
Final memory (5 total rows):
  [fraud_advisor] CTA-100240: late-night SPEI transfer of MXN 38,500 to a new beneficiary, anomaly score 8.7. Keep on watch, do not release the hold until the customer is reached.
  [fraud_advisor] Is CTA-100240 cleared, or do we freeze it for suspected fraud?
  [fraud_advisor] Keep CTA-100240 on hold — ...
  [ops_assistant] Is CTA-100240 cleared, or do we freeze it for suspected fraud?
  [ops_assistant] The hold on CTA-100240 stays in place per the fraud advisor's determination — ...
```

Five rows, in the order they were written.

## Full run

Running `python agent_memory.py` with no arguments prints the whole story (live run, 2026-10-15):

```text
Seeding shared memory with a fraud note...
  Seed row: (1, 'default', 'sess-01', 'fraud_advisor', 'assistant', 'CTA-100240: late-night SPEI transfer of MXN 38,500 to a new beneficiary, anomaly score 8.7. Keep on watch, do not release the hold until the customer is reached.', datetime.datetime(...))

1. Fraud Advisor turn:
Prior memory (1 row):
  - fraud_advisor (assistant): CTA-100240: late-night SPEI transfer of MXN 38,500 to a new beneficiary, anomaly score 8.7. Keep on
Response:
  Keep CTA-100240 frozen/on hold — per prior notes, the late-night MXN 38,500 SPEI transfer to a new beneficiary scored 8.7, and the hold should not be released until the customer is reached.

Memory now: 3 total rows

2. Ops Assistant turn:
Prior memory (3 rows):
  - fraud_advisor (assistant): CTA-100240: late-night SPEI transfer of MXN 38,500 to a new beneficiary, anomaly score 8.7. Keep on
  - fraud_advisor (user): Is CTA-100240 cleared, or do we freeze it for suspected fraud?
  - fraud_advisor (assistant): Keep CTA-100240 frozen/on hold — per prior notes, the late-night MXN 38,500 SPEI transfer to a new b
Response:
  CTA-100240 is not cleared — the hold stays in place per the fraud advisor's determination, and should not be released until the customer is reached and verifies the late-night MXN 38,500 SPEI transfer to the new beneficiary.

Memory now: 5 total rows

Done. Both agents wrote to and read from the same governed table.
```

The script does not delete earlier rows, so the seed row id and the row counts grow if you run it
more than once on the same branch.

## The numbers that matter

| What | Expected | Why it matters |
| ---- | -------- | -------------- |
| seed insert | 1 row | shared memory initialized with context |
| fraud advisor appends | 2 rows (question + answer) | agent writes are durable |
| ops assistant reads before its turn | 3 rows | it sees the other agent's answer |
| ops assistant appends | 2 rows (question + answer) | a second agent can also write |
| total rows after both agents | 5 rows | shared memory is a real table, not a cache |

> **From the field**
> Real agent deployments vary the memory schema (add fields like `session_id`, `namespace`,
> error flags, metadata), but the pattern stays the same: one table is the read-write link
> between agents, governed as a first-class asset. No Redis, no vector store, no message
> queue. The database IS the agent memory system.
