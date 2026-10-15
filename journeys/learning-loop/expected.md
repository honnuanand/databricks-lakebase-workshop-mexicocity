# Human-in-the-loop, expected results

Use this to check your run. Claude's exact extractions will vary, but the *shape* is what matters:
high-confidence entries auto-accept, low-confidence route to review, and corrections are recorded
atomically with confidence and status fields.

## Step 1, table structure

```text
note_id | account_id | ts | writeup | category | finding | action | confidence
```

The raw input (first 4 columns) and the AI extraction (last 4 columns).

## Step 2, seed

```text
(_, 'CTA-100240', ..., 'Three card-not-present charges overnight to an overseas merchant the cardholder does not recognize, velocity spike. Froze the card and opened a reissue.')
(_, 'CTA-300421', ..., 'Large outbound wire to a brand-new beneficiary in a high-risk jurisdiction, just under the reporting threshold. Possible structuring, referred to AML.')
(_, 'CTA-200311', ..., 'Customer disputes a charge they say posted twice; merchant portal is ambiguous. Needs a closer look at the settlement records.')
(_, 'CTA-100235', ..., 'A few small foreign-currency charges followed by a larger one, same merchant. Could be card testing, or just travel. Hold for review.')
(_, 'CTA-100240', ..., 'Something looked off on the account this morning, maybe the login location? not sure, flagging it.')
```

Five messy, real-world analyst case notes. The `note_id` values are serial and depend on how many
notes already sat in the table, so they will not necessarily start at 1.

## Step 3, extract

```text
Running AI extraction (5 write-ups):
  - Note 25: category=fraud, confidence=0.92, status=auto_accepted
  - Note 26: category=AML, confidence=0.90, status=auto_accepted
  - Note 27: category=dispute, confidence=0.60, status=needs_review
  - Note 28: category=fraud, confidence=0.50, status=needs_review
  - Note 29: category=fraud, confidence=0.30, status=needs_review
```

The exact category/finding values and confidences will vary (Claude's extraction is probabilistic),
but the pattern is clear:
- The two clearest notes (card fraud, AML wire): high confidence (over 0.75), auto-accepted
- The ambiguous notes (dispute, FX charges, the vague login note): lower confidence, routed to review

## Step 4, after extraction

```text
(25, 'Three card-not-present...', 'fraud', 'card_compromise', 0.92, 'auto_accepted')
(26, 'Large outbound wire...', 'AML', 'possible_structuring', 0.90, 'auto_accepted')
(27, 'Customer disputes...', 'dispute', 'double_charge_claim', 0.60, 'needs_review')
(28, 'A few small foreign-currency...', 'fraud', 'possible_card_testing', 0.50, 'needs_review')
(29, 'Something looked off...', 'fraud', 'unclear', 0.30, 'needs_review')
```

## Step 5, after correction

The script picks the lowest-confidence needs_review row dynamically and corrects it:

```text
Before:  category=fraud, finding=unclear, confidence=0.30, status=needs_review
After:   category=fraud, finding=account_takeover_suspected, confidence=0.30, status=corrected
```

The row is atomically updated; no second table, no sync.

## Step 6, analytics

```text
Analytics:
  Total: 5
  Auto-accepted: 2
  Needs review: 2
  Corrected by human: 1
  Avg confidence (auto-accepted): 0.910
  Avg confidence (needs review): 0.550
  Accuracy of auto-accepted: 100% (no corrections needed)
```

The entire learning loop is one table with confidence, status, and audit fields.

## Full run

Running `python learning_loop.py` with no arguments prints the whole story:

```text
Seeding analyst case notes (5 entries):
  - CTA-100240: Three card-not-present charges overnight to an overseas merc...
  - CTA-300421: Large outbound wire to a brand-new beneficiary in a high-ris...
  - CTA-200311: Customer disputes a charge they say posted twice; merchant p...
  - CTA-100235: A few small foreign-currency charges followed by a larger on...
  - CTA-100240: Something looked off on the account this morning, maybe the ...

Running AI extraction (5 write-ups):
  - Note 25: category=fraud, confidence=0.92, status=auto_accepted
  - Note 26: category=AML, confidence=0.90, status=auto_accepted
  - Note 27: category=dispute, confidence=0.60, status=needs_review
  - Note 28: category=fraud, confidence=0.50, status=needs_review
  - Note 29: category=fraud, confidence=0.30, status=needs_review

Human correction (analyst reviews uncertain entries):
  - Note 29: analyst set category=fraud, finding=account_takeover_suspected (was uncertain)

Analytics:
  Total: 5
  Auto-accepted: 2
  Needs review: 2
  Corrected by human: 1
  Avg confidence (auto-accepted): 0.910
  Avg confidence (needs review): 0.550
  Accuracy of auto-accepted: 100% (no corrections needed)

Done. One table is the store, the review queue, the audit trail, and the analytics source.
```

## The numbers that matter

| What | Expected | Why it matters |
| ---- | -------- | -------------- |
| auto-accept threshold | 0.75 confidence | typical ML threshold (tunable) |
| extractions routed to review | ~40-60% in real data | depends on note clarity |
| FM API latency per extraction | 1-2 seconds | single model call, no round-trips |
| human correction latency | atomic UPDATE | one row, one transaction |
| accuracy tracking | stored in same table | no data movement, instant analytics |

> **From the field**
> Real learning loops batch extractions (call the model once per 100 case notes), cache model
> responses (avoid re-extracting the same note twice), and implement feedback loops where
> corrections automatically retrain the model. This journey shows the simplest pattern: one
> table, one model call per note, accuracy measured from SQL. Production systems add
> async jobs, model versioning, and A/B testing on the same schema.
