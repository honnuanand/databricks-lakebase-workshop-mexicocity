# The agent does the work, expected results

Use this to check your run. The exact agent responses will vary slightly, but the *shape*
is what matters: the agent reads account risk, writes a hold, remembers it, and refuses to
double-hold on the second call.

## Step 1, initial state

```text
('CTA-100240', 'Credit', 'retail', 'watch', Decimal('91.00'))
8.70
```

CTA-100240 is a retail Credit account on `watch`. Its riskiest transaction carries an anomaly
score of 8.7.

## Step 2, review the account

```text
Agent reads prior memory:
  (empty or prior turns from an earlier run)

Agent calls tools:
  - get_account_risk('CTA-100240'): ('watch', 8.70)
  - place_hold('CTA-100240'): froze account, wrote case_note flag

Agent response:
Hold placed on CTA-100240 due to an anomaly score of 8.7 on a card-not-present charge. The account is frozen pending cardholder verification.

Appended to memory:
  agent_id: fraud_advisor
  role: assistant
  content: placed hold on CTA-100240
```

The agent:
1. Read the account risk (status `watch`, top anomaly 8.7).
2. Called place_hold (froze the account + wrote a case_note flag).
3. Logged its action to memory.

## Step 3, confirm the hold

```text
('CTA-100240', 'frozen')

('CTA-100240', 'fraud', 'card_not_present_anomaly_8.70', 'hold_placed')
```

The account status is now `frozen`, and there is one case_note row with `action='hold_placed'`.

## Step 4, review again (memory prevents double-work)

```text
Agent reads prior memory:
  - placed hold on CTA-100240

Agent response:
CTA-100240 is already on hold. No duplicate action needed.
```

The agent reads its own prior turn and refuses to re-hold. No second case_note flag, no
double-work.

## Full run

Running `python agentic_work.py` with no arguments prints the whole story:

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

  Agent response: Hold placed on CTA-100240 due to anomaly score 8.7...
  Memory: placed hold on CTA-100240

2. Review CTA-100240 and act on the fraud signal:
  Agent reads prior memory:
    - placed hold on CTA-100240

  Agent response: CTA-100240 is already on hold. No duplicate action.

Done. Agent read state, acted, remembered, and refused to double-hold.
```

## The numbers that matter

| What | Expected | Why it matters |
| ---- | -------- | -------------- |
| tool call result latency | 200-500ms per call | SQL on same DB, no network hop |
| account status after hold | frozen | agent's write is durable |
| case_note hold rows | exactly 1 on first call | the action is recorded once |
| case_note hold rows | still 1 on second call | agent's memory prevents double-work |
| agent memory rows | the hold decision persisted | agent decision is durable |
| total FM API latency | 2-4 seconds per call | model narration of the loop |

> **From the field**
> Real agents typically batch tool calls (call all reads, then decide, then call all writes),
> reduce round-trips, and wrap multiple writes in a transaction. This journey shows the
> simplest pattern: one tool call per decision step. The database constraints (unique keys,
> foreign keys, a status column) are the agent's guard rails, not code logic.
