# The agent does the work, instructions

## How to run this journey

There are a few ways to work through the steps. Pick one:

- **Notebook, step by step (recommended for learning):** open [`agentic_work.ipynb`](agentic_work.ipynb) and run one cell at a time. Reading each result before the next step is where the learning happens.
- **In a Databricks workspace:** import [`agentic_work_databricks.py`](agentic_work_databricks.py) and run it cell by cell there.
- **By hand:** follow the numbered steps below, copying each command yourself.
- **Just see it work:** run `python agentic_work.py` from this folder to execute the whole thing at once. Fast, but you learn the most from the notebook.

Run these on your own branch. If you haven't done [`../../00-setup/`](../../00-setup/), do that
first; you need `LB_PROFILE`, `LB_PROJECT`, `LB_BRANCH`, and `LB_SCHEMA` set, and the bank
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

Before the agent acts, see the account status and its recent transactions:

```bash
python ../../common/scripts/lakebase.py --sql \
  "SELECT account_id, line, type, status, health_pct FROM bank.account WHERE account_id='CTA-100240'"

python ../../common/scripts/lakebase.py --sql \
  "SELECT txn_id, amount, anomaly_score, mcc FROM bank.txn WHERE account_id='CTA-100240' ORDER BY anomaly_score DESC LIMIT 3"
```

You should see CTA-100240 is a `watch` Credit account, and its top transaction carries an
`anomaly_score` of 8.7 (the fraud signal).

### Step 2, ask the agent to review and act

The agent is a fraud-ops assistant deployed on Model Serving that can read account risk and
write a hold. Call it:

```bash
python agentic_work.py --step review
```

The script:
1. Reads the agent's memory from the `agent_memory` table (to avoid double-work).
2. Builds a tool-calling prompt: "Review CTA-100240 and act on the fraud signal."
3. The agent calls a tool: `get_account_risk()` -> SQL SELECT returns status + top anomaly score.
4. The agent decides: "Place a hold on CTA-100240."
5. The agent calls another tool: `place_hold(account_id)` -> SQL UPDATE sets the account status
   to `frozen` and INSERTs a flag row into the `case_note` table.
6. The agent remembers: appends "I placed a hold on CTA-100240" to its memory.

You should see output like:

```text
Agent tool calls:
  - get_account_risk('CTA-100240'): returns ('watch', 8.7)
  - place_hold('CTA-100240'): froze account, wrote case_note flag
Agent decision: Hold placed on CTA-100240 due to anomaly score 8.7 on a card-not-present charge.
Memory after: placed hold on CTA-100240
```

### Step 3, confirm the hold was written

Query the account and case_note tables to see the action:

```bash
python ../../common/scripts/lakebase.py --sql \
  "SELECT account_id, status FROM bank.account WHERE account_id='CTA-100240'"

python ../../common/scripts/lakebase.py --sql \
  "SELECT account_id, category, finding, action FROM bank.case_note WHERE account_id='CTA-100240' AND action='hold_placed'"
```

You should see the account `status='frozen'` and one case_note row with `action='hold_placed'`.

### Step 4, ask the agent the same question again

Now ask the agent to review the *same* account:

```bash
python agentic_work.py --step review-again
```

The script:
1. Reads the agent's memory.
2. Sees "I already placed a hold on CTA-100240".
3. Refuses the request: "CTA-100240 is already on hold."

You should see output like:

```text
Agent reads its memory:
  - placed hold on CTA-100240
Agent decision: CTA-100240 is already on hold. No duplicate action needed.
```

### Step 5, inspect the shared state

The agent's tools read and write the same tables the bank's operations do. Query the case_note
table one more time to confirm:

```bash
python ../../common/scripts/lakebase.py --sql \
  "SELECT account_id, action FROM bank.case_note WHERE account_id='CTA-100240' AND action='hold_placed'"
```

Still one hold row (no double-action). The agent's decision to not re-hold is backed by SQL
consistency, not just logic.

## What you just did

You watched an agent read live data with a tool, decide to take action, and write a state
change back to the database, all in one turn, with memory that prevents double-work. The
agent changed the account's operational state, and the database tracks it. Compare the output
you saw against [`expected.md`](expected.md), and if anything went sideways, [`faq.md`](faq.md)
has the common causes.
