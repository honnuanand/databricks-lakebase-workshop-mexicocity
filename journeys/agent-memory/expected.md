# Agent memory, expected results

Use this to check your run. The exact responses will differ slightly (Claude varies), but the
*shape* and timing are what matter: the seed inserts cleanly, the agents append their turns,
and the table reads back with all four rows in order.

## Step 1, table check

```text
0
```

Or a small count if you ran this before. Either is fine; the script is idempotent.

## Step 2, seed

```text
(1, 'default', 'shift-001', 'maintenance_advisor', 'assistant', 'M-204: bearing replaced at 08:15. Cleared for 72 hours, then re-inspect.', ...)
```

One row inserted.

## Step 3, maintenance advisor

```text
Maintenance Advisor sees prior memory:
  - M-204: bearing replaced at 08:15. Cleared for 72 hours, then re-inspect.

Maintenance Advisor response:
M-204 is healthy and cleared for 72 hours of continuous operation. The bearing replacement at 08:15 was successful. No additional maintenance is required before the 72-hour window expires. Monitor the bearing temperature during the next run as a precaution.
```

The exact wording varies. The key is that:
1. The agent saw the seeded memory (the maintenance note).
2. It generated a response grounded in that note.
3. The response appeared in the output.

After this step, the memory table should have 3 rows: the seed, the user question, and the
assistant response.

## Step 4, MES assistant

```text
MES Assistant sees prior memory:
  - M-204: bearing replaced at 08:15. Cleared for 72 hours, then re-inspect.
  - maintenance_advisor (assistant): M-204 is healthy and cleared for 72 hours...

MES Assistant response:
M-204 is available and ready to schedule. Given the recent bearing replacement and the 72-hour clearance window, I can allocate it for the next production run. I recommend scheduling high-priority work orders first to maximize the healthy window before the 72-hour re-inspection.
```

Again, the wording varies. The key is:
1. The MES assistant read both the seeded note AND the maintenance advisor's prior response.
2. It responded based on that context.
3. The two agents never directly messaged; they only read/wrote the shared table.

After this step, the memory table should have 5 rows.

## Step 5, full memory table

```text
(1, 'default', 'shift-001', 'maintenance_advisor', 'assistant', 'M-204: bearing replaced at 08:15. Cleared for 72 hours, then re-inspect.', ...)
(2, 'default', 'shift-001', 'mes_assistant', 'user', 'Is M-204 cleared to run the next shift?', ...)
(3, 'default', 'shift-001', 'maintenance_advisor', 'assistant', 'M-204 is healthy and cleared for 72 hours...', ...)
(4, 'default', 'shift-001', 'mes_assistant', 'user', 'Is M-204 cleared to run the next shift?', ...)
(5, 'default', 'shift-001', 'mes_assistant', 'assistant', 'M-204 is available and ready to schedule...', ...)
```

All rows in order, with timestamps increasing. This is the agents' shared brain as plain SQL.

## Full run

Running `python agent_memory.py` with no arguments prints the whole story:

```text
Seeding shared memory with a maintenance note...
  Seed row: (1, 'default', 'shift-001', 'maintenance_advisor', 'assistant', 'M-204: bearing replaced at 08:15. Cleared for 72 hours, then re-inspect.')

1. Maintenance Advisor turn:
  Prior memory (1 row):
    - M-204: bearing replaced at 08:15. Cleared for 72 hours, then re-inspect.
  Question: Is M-204 cleared to run the next shift?
  Response: M-204 is healthy and cleared for 72 hours of continuous operation...
  Memory after: 3 rows

2. MES Assistant turn:
  Prior memory (3 rows):
    - M-204: bearing replaced at 08:15. Cleared for 72 hours, then re-inspect.
    - maintenance_advisor (assistant): M-204 is healthy and cleared for 72 hours...
    - mes_assistant (user): Is M-204 cleared to run the next shift?
  Response: M-204 is available and ready to schedule...
  Memory after: 5 rows

Done. Both agents wrote to and read from the same governed table.
```

## The numbers that matter

| What | Expected | Why it matters |
| ---- | -------- | -------------- |
| seed insert | 1 row | shared memory initialized with context |
| maintenance advisor appends | 2 rows (user + response) | agent writes are durable |
| MES assistant reads + sees all prior | 3 rows before its turn | agent reads are consistent |
| MES assistant appends | 2 rows (user + response) | second agent can also write |
| total rows after both agents | 5 rows | shared memory is a real table, not a cache |
| FM API latency per agent | 1-3 seconds | single-hop, no orchestration |

> **From the field**
> Real agent deployments vary the memory schema (add fields like `session_id`, `namespace`,
> error flags, metadata), but the pattern stays the same: one table is the read-write link
> between agents, governed as a first-class asset. No Redis, no vector store, no message
> queue. The database IS the agent memory system.
