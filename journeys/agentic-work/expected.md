# The agent does the work, expected results

Use this to check your run. The exact agent responses will vary slightly, but the *shape*
is what matters: the agent reads machine state, writes an assignment, remembers it, and
refuses to double-assign on the second call.

## Step 1, initial state

```text
('M-204', 'healthy', Decimal('91.00'))
('WO-1001', 'PRD-GEARBOX-X1', 50, 'released')
```

M-204 is healthy and available. WO-1001 is released and waiting to be assigned.

## Step 2, release the work order

```text
Agent reads prior memory:
  (empty or prior assignments from an earlier run)

Agent calls tools:
  tool_name: get_free_machines
  result: [('M-204', 'healthy', Decimal('91.00'))]

Agent calls tools:
  tool_name: assign_work_order
  args: wo_id='WO-1001', machine_id='M-204'
  result: ok, inserted 1 row

Agent response:
WO-1001 is now assigned to M-204. Starting a 2-hour production run at line Stamping-A.

Appended to memory:
  agent_id: mes_assistant
  role: assistant
  content: Assigned WO-1001 to M-204
```

The agent:
1. Read the free machines (M-204).
2. Called assign_work_order (INSERT operation row).
3. Logged its action to memory.

## Step 3, confirm the operation row

```text
('OP-<id>', 'WO-1001', 'M-204', 1, 'pending')
```

One row in the operation table with the work order assigned to the machine and status pending.

## Step 4, release again (memory prevents double-work)

```text
Agent reads prior memory:
  - Assigned WO-1001 to M-204

Agent response:
WO-1001 is already assigned to M-204. No duplicate assignment needed.
```

The agent reads its own prior turn and refuses to re-assign. No second INSERT, no double-work.

## Full run

Running `python agentic_work.py` with no arguments prints the whole story:

```text
Initial state:
  M-204: healthy, 91%
  WO-1001: released, awaiting assignment

1. Release WO-1001 to the shop floor:
  Agent reads prior memory:
    (empty)
  
  Agent calls tools:
    - get_free_machines: [('M-204', 'healthy', 91.0)]
    - assign_work_order('WO-1001', 'M-204'): ok
  
  Agent response: WO-1001 is now assigned to M-204.
  Memory: Assigned WO-1001 to M-204

2. Release WO-1001 again:
  Agent reads prior memory:
    - Assigned WO-1001 to M-204
  
  Agent response: WO-1001 is already assigned. No duplicate assignment.

Done. Agent read state, acted, remembered, and refused to double-assign.
```

## The numbers that matter

| What | Expected | Why it matters |
| ---- | -------- | -------------- |
| tool call result latency | 200-500ms per call | SQL on same DB, no network hop |
| operation row inserted | exactly 1 on first call | agent's write is durable |
| operation row inserted | still 1 on second call | agent's memory prevents double-work |
| agent memory rows | 1 (the assignment decision) | agent decision is persisted |
| total FM API latency | 2-4 seconds per call | function-calling loop overhead |

> **From the field**
> Real agents typically batch tool calls (call all reads, then decide, then call all writes),
> reduce round-trips, and use transactions to wrap multiple writes. This journey shows the
> simplest pattern: one tool call per decision step. The database constraints (unique keys,
> foreign keys) are the agent's guard rails, not code logic.
