# Agent memory, instructions

Run these on your own branch. If you haven't done [`../../00-setup/`](../../00-setup/), do that
first; you need `LB_PROFILE`, `LB_PROJECT`, `LB_BRANCH`, and `LB_SCHEMA` set, and the factory
loaded.

Everything here is a single script you can read: [`./agent_memory.py`](./agent_memory.py).
You can run it end to end, or follow the steps by hand to see each piece.

## Run it end to end

```bash
cd journeys/agent-memory
python agent_memory.py
```

This walks the whole story and shows agent responses. Read on for what each step does; the exact
output to expect is in [`expected.md`](expected.md).

## Or step through it by hand

### Step 1, check the agent_memory table structure

The factory schema includes the `agent_memory` table (see `common/scripts/factory_schema.sql`).
Check it exists and is empty to start:

```bash
python ../../common/scripts/lakebase.py --sql \
  "SELECT count(*) FROM factory.agent_memory"
```

You should see `0` or a small count from a prior run. The table has columns:
`id`, `namespace`, `session_id`, `agent_id`, `role`, `content`, `created_at`.

### Step 2, seed the memory with a prior maintenance note

In a real system, agents read back *all* their prior memory on session startup. To show this,
seed the table with one row: a maintenance note from the morning shift that sets context:

```bash
python agent_memory.py --step seed
```

The script inserts a note like:

```sql
INSERT INTO factory.agent_memory (namespace, session_id, agent_id, role, content)
VALUES ('default', 'shift-001', 'maintenance_advisor', 'assistant',
        'M-204: bearing replaced at 08:15. Cleared for 72 hours, then re-inspect.');
```

Read it back:

```bash
python ../../common/scripts/lakebase.py --sql \
  "SELECT agent_id, role, content FROM factory.agent_memory ORDER BY created_at"
```

### Step 3, ask the maintenance advisor a question

The maintenance advisor is a small agent (or a simulated agent) that reads the shared memory
and answers about machine health. Call it:

```bash
python agent_memory.py --step maintenance
```

The script:
1. Reads all prior memory from the table.
2. Calls the Foundation Model API (Claude) with the question and prior context.
3. Appends the user question and the assistant response to the memory table.

You should see output like:

```text
Maintenance Advisor sees prior memory:
  - M-204: bearing replaced at 08:15. Cleared for 72 hours, then re-inspect.
Maintenance Advisor response:
  M-204 is cleared for 72 hours of operation. No maintenance needed before then.
```

Check the memory table:

```bash
python ../../common/scripts/lakebase.py --sql \
  "SELECT agent_id, role, content FROM factory.agent_memory ORDER BY created_at"
```

You should now see the user question and assistant response as two new rows.

### Step 4, ask the MES assistant the same question

The MES assistant is another agent that allocates machines to work orders. Call it with the
same question:

```bash
python agent_memory.py --step mes
```

The script:
1. Reads all prior memory (including the maintenance advisor's response).
2. Calls Claude with the question and context.
3. Appends the user question and response to the memory.

You should see output like:

```text
MES Assistant sees prior memory:
  - M-204: bearing replaced at 08:15. Cleared for 72 hours, then re-inspect.
  - Maintenance Advisor: M-204 is cleared for 72 hours...
MES Assistant response:
  M-204 is ready. I can schedule it for the 10 AM run.
```

### Step 5, query the shared memory directly

Now read the whole memory table as SQL:

```bash
python ../../common/scripts/lakebase.py --sql \
  "SELECT agent_id, role, content FROM factory.agent_memory ORDER BY created_at"
```

You should see all four turns: the seed, the maintenance advisor's question and response, and
the MES assistant's question and response. This is plain Postgres, governed by Unity Catalog.
Open the Lakebase console: the table shows up with full lineage.

## What you just did

You set up agent memory as a single governed table that two independent agents can read and
append to. No message queue, no cache invalidation, no separate memory service. The database
that runs the factory also runs the agents' brain, and Unity Catalog governs both. Compare
the output you saw against [`expected.md`](expected.md), and if anything went sideways,
[`faq.md`](faq.md) has the common causes.
