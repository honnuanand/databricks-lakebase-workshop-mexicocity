# The agent does the work, expected results

Use this to check your run. The tool calls (the SQL reads and writes) are fixed code, so their
output is the same every run. The agent's explanations come from a live model (`FM_ENDPOINT`,
default `databricks-claude-opus-4-8`), so their wording varies. What matters is the *shape*: the
agent reads account risk, places a hold, remembers it, and refuses to double-hold on the second
call. The examples below are from a live run on 2026-10-15.

If the endpoint is unavailable, the cell prints `(FM API unavailable: ...; using fallback)` and
a fixed line instead.

## Step 0, reset the flagged account

```text
Prepared: CTA-100240 reset to 'watch', ready for review
```

## Step 1, initial state

```text
Initial state:
  CTA-100240: Credit (retail), status=watch, health=91.00%
  top transaction anomaly_score: 8.70
```

CTA-100240 is a retail Credit account on `watch`. Its riskiest transaction, a late-night SPEI
transfer of MXN 38,500 to a new beneficiary, carries an anomaly score of 8.7.

## Step 2, read account risk

```text
Account risk: status=watch, top anomaly_score=8.70
  High fraud signal. The agent will place a hold.
```

## Step 3, place the hold

```text
Placed hold on CTA-100240: account frozen, case_note flag written

Agent response:
  Placed a hold on account CTA-100240, which was already flagged as 'watch' and showed a high top anomaly score of 8.70, indicating elevated fraud risk warranting the freeze pending review.
```

The account is now `frozen`, and `case_note` has one row for it with `category='fraud'`,
`finding='spei_new_beneficiary_anomaly_8.70'`, `action='hold_placed'`.

## Step 4, remember the hold

```text
Remembered the hold in agent_memory
```

## Step 5, called again: refuses

```text
Agent reads memory: "placed hold on CTA-100240"
REFUSE: CTA-100240 is already on hold. No double-action.

Agent response:
  A hold is already in place on CTA-100240, so no further action is needed from me at this time.
```

No second hold, no second `case_note` flag.

## Full run

Running `python agentic_work.py` with no arguments prints the whole story (live run, 2026-10-15):

```text
Initial state:
  CTA-100240: Credit (retail), status=watch, health=91.00%
  top transaction anomaly_score: 8.70

1. Review CTA-100240 and act on the fraud signal:
Agent reads prior memory:
  (empty)

Agent calls tools:
  - get_account_risk('CTA-100240'): ('watch', 8.70)
  - place_hold('CTA-100240'): froze account, wrote case_note flag

Agent response:
Placed a hold on account CTA-100240, which was already flagged as 'watch' and showed a high top anomaly score of 8.70, indicating elevated fraud risk that warranted suspending activity pending review.


2. Review CTA-100240 and act on the fraud signal:
Agent reads prior memory:
  - fraud_advisor (user): Review CTA-100240 and act on the fraud signal
  - fraud_advisor (assistant): placed hold on CTA-100240

Agent reads its memory and decides: A hold is already placed on CTA-100240, so no further action is needed from me.

Done. Agent read state, acted, remembered, and refused to double-hold.
```

## The numbers that matter

| What | Expected | Why it matters |
| ---- | -------- | -------------- |
| account status after hold | frozen | agent's write is durable |
| case_note hold rows | exactly 1 on first call | the action is recorded once |
| case_note hold rows | still 1 on second call | agent's memory prevents double-work |
| agent memory rows | the hold decision persisted | agent decision is durable |

> **From the field**
> Real agents typically batch tool calls (call all reads, then decide, then call all writes),
> reduce round-trips, and wrap multiple writes in a transaction. This journey shows the
> simplest pattern: one tool call per decision step. The database constraints (unique keys,
> foreign keys, a status column) are the agent's guard rails, not code logic.
