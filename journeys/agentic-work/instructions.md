# The agent does the work, instructions

## How to run this journey

There are a few ways to work through the steps. Pick one:

- **Notebook, step by step (recommended for learning):** open [`agentic_work.ipynb`](agentic_work.ipynb) and run one cell at a time. Reading each result before the next step is where the learning happens.
- **In a Databricks workspace:** import [`agentic_work_databricks.py`](agentic_work_databricks.py) and run it cell by cell there.
- **By hand:** follow the numbered steps below, copying each command yourself.
- **Just see it work:** run `python agentic_work.py` from this folder to execute the whole thing at once. Fast, but you learn the most from the notebook.

Run these on your own branch. If you haven't done [`../../00-setup/`](../../00-setup/), do that
first; you need `LB_PROFILE`, `LB_PROJECT`, `LB_BRANCH`, and `LB_SCHEMA` set, and the factory
loaded.

Everything here is a single script you can read: [`./agentic_work.py`](./agentic_work.py).
You can run it end to end, or follow the steps by hand to see each piece.

## Run it end to end

```bash
cd journeys/agentic-work
python agentic_work.py
```

This walks the whole story with tool calls and state changes. Read on for what each step does;
the exact output to expect is in [`expected.md`](expected.md).

## Or step through it by hand

### Step 1, check the current state

Before the agent acts, see what machines are available and what work orders are pending:

```bash
python ../../common/scripts/lakebase.py --sql \
  "SELECT machine_id, status, health_pct FROM factory.machine WHERE machine_id='M-204'"

python ../../common/scripts/lakebase.py --sql \
  "SELECT wo_id, product_id, qty, status FROM factory.work_order WHERE wo_id='WO-1001'"
```

You should see M-204 is `healthy` and WO-1001 is `released` (waiting to be assigned to a
machine).

### Step 2, ask the agent to release a work order

The agent is an MES assistant deployed on Model Serving that can read machine status and write
work assignments. Call it:

```bash
python agentic_work.py --step release
```

The script:
1. Reads the agent's memory from the `agent_memory` table (to avoid double-work).
2. Builds a tool-calling prompt: "Release WO-1001 to the shop floor."
3. The agent calls a tool: `get_free_machines()` → SQL SELECT returns available machines.
4. The agent decides: "Assign WO-1001 to M-204."
5. The agent calls another tool: `assign_work_order(wo_id, machine_id)` → SQL INSERT adds a
   row to the `operation` table.
6. The agent remembers: appends "I assigned WO-1001 to M-204" to its memory.

You should see output like:

```text
Agent tool calls:
  - get_free_machines: returns [('M-204', 'healthy', 91.0)]
  - assign_work_order('WO-1001', 'M-204'): inserted row
Agent decision: Assign WO-1001 to M-204 for a 2-hour production run.
Memory after: assigned WO-1001 to M-204
```

### Step 3, confirm the assignment was written

Query the operation table to see the assignment:

```bash
python ../../common/scripts/lakebase.py --sql \
  "SELECT op_id, wo_id, machine_id, status FROM factory.operation WHERE wo_id='WO-1001'"
```

You should see a row with `wo_id='WO-1001'` and `machine_id='M-204'` and `status='pending'`
(waiting to start).

### Step 4, ask the agent the same question again

Now ask the agent to release the *same* work order:

```bash
python agentic_work.py --step release-again
```

The script:
1. Reads the agent's memory.
2. Sees "I already assigned WO-1001 to M-204".
3. Refuses the request: "WO-1001 is already assigned."

You should see output like:

```text
Agent reads its memory:
  - I assigned WO-1001 to M-204
Agent decision: WO-1001 is already assigned to M-204. No double-assignment.
```

### Step 5, inspect the shared state

The agent's tools read and write the same tables the warehouse operation does. Query the
operation table one more time to confirm:

```bash
python ../../common/scripts/lakebase.py --sql \
  "SELECT wo_id, machine_id, status FROM factory.operation WHERE wo_id='WO-1001'"
```

Still one row (no double-assignment). The agent's decision to not re-assign is backed by SQL
consistency, not just logic.

## What you just did

You watched an agent read live data with a tool, decide to take action, and write a state
change back to the database, all in one turn, with memory that prevents double-work. The
agent changed the factory's operational state, and the database tracks it. Compare the output
you saw against [`expected.md`](expected.md), and if anything went sideways, [`faq.md`](faq.md)
has the common causes.
