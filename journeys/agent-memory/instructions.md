# Agent memory, instructions

## How to run this journey

There are a few ways to work through the steps. Pick one:

- **Notebook, step by step (recommended for learning):** open [`agent_memory.ipynb`](agent_memory.ipynb) and run one cell at a time. Reading each result before the next step is where the learning happens.
- **In a Databricks workspace:** import [`agent_memory_databricks.py`](agent_memory_databricks.py) and run it cell by cell there.
- **By hand:** follow the numbered steps below, copying each command yourself.
- **Just see it work:** run `python agent_memory.py` from this folder to execute the whole thing at once. Fast, but you learn the most from the notebook.

Run these on your own branch. If you haven't done [`../../00-setup/`](../../00-setup/), do that
first; you need `LB_PROFILE`, `LB_PROJECT`, `LB_BRANCH`, and `LB_SCHEMA` set, and the bank
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

The bank schema includes the `agent_memory` table (see `common/scripts/finance_schema.sql`).
Check it exists and is empty to start:

```bash
python ../../common/scripts/lakebase.py --sql \
  "SELECT count(*) FROM bank.agent_memory"
```

You should see `0` or a small count from a prior run. The table has columns:
`id`, `namespace`, `session_id`, `agent_id`, `role`, `content`, `created_at`.

### Step 2, seed the memory with a prior fraud note

In a real system, agents read back *all* their prior memory on session startup. To show this,
seed the table with one row: a fraud note from the overnight alert queue that sets context:

```bash
python agent_memory.py --step seed
```

The script inserts a note like:

```sql
INSERT INTO bank.agent_memory (namespace, session_id, agent_id, role, content)
VALUES ('default', 'sess-01', 'fraud_advisor', 'assistant',
        'ACCT-100240: card-not-present spike overnight, anomaly score 8.7. Keep on watch, do not release the hold until cardholder is reached.');
```

Read it back:

```bash
python ../../common/scripts/lakebase.py --sql \
  "SELECT agent_id, role, content FROM bank.agent_memory ORDER BY created_at"
```

### Step 3, ask the fraud advisor a question

The fraud advisor is a small agent (or a simulated agent) that reads the shared memory and
answers about account risk. Call it:

```bash
python agent_memory.py --step fraud
```

The script:
1. Reads all prior memory from the table.
2. Calls the Foundation Model API (Claude) with the question and prior context.
3. Appends the user question and the assistant response to the memory table.

You should see output like:

```text
Fraud Advisor sees prior memory:
  - ACCT-100240: card-not-present spike overnight, anomaly score 8.7. Keep on watch...
Fraud Advisor response:
  ACCT-100240 is not cleared. The 8.7 anomaly score on an overnight card-not-present spike warrants keeping the hold until the cardholder confirms the charges.
```

Check the memory table:

```bash
python ../../common/scripts/lakebase.py --sql \
  "SELECT agent_id, role, content FROM bank.agent_memory ORDER BY created_at"
```

You should now see the user question and assistant response as two new rows.

### Step 4, ask the ops assistant the same question

The ops assistant is another agent that services accounts at the branch. Call it with the same
question:

```bash
python agent_memory.py --step ops
```

The script:
1. Reads all prior memory (including the fraud advisor's response).
2. Calls Claude with the question and context.
3. Appends the user question and response to the memory.

You should see output like:

```text
Ops Assistant sees prior memory:
  - ACCT-100240: card-not-present spike overnight, anomaly score 8.7. Keep on watch...
  - fraud_advisor (assistant): ACCT-100240 is not cleared...
Ops Assistant response:
  I will keep the hold on ACCT-100240 in place and will not release funds, per the fraud advisor's note. I will reach out to the cardholder to verify.
```

### Step 5, query the shared memory directly

Now read the whole memory table as SQL:

```bash
python ../../common/scripts/lakebase.py --sql \
  "SELECT agent_id, role, content FROM bank.agent_memory ORDER BY created_at"
```

You should see all the turns: the seed, the fraud advisor's question and response, and the
ops assistant's question and response. This is plain Postgres, governed by Unity Catalog.
Open the Lakebase console: the table shows up with full lineage.

## What you just did

You set up agent memory as a single governed table that two independent agents can read and
append to. No message queue, no cache invalidation, no separate memory service. The database
that runs the bank also runs the agents' shared brain, and Unity Catalog governs both. Compare
the output you saw against [`expected.md`](expected.md), and if anything went sideways,
[`faq.md`](faq.md) has the common causes.
