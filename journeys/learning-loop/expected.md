# Human-in-the-loop, expected results

Use this to check your run. The extraction step calls a live model (`FM_ENDPOINT`, default
`databricks-claude-opus-4-8`), which sets its own confidence, so exact labels and scores vary.
What matters is the *shape*: clear notes auto-accept, vague ones route to review, and the
correction is written back to the same row. The examples below are from live runs on
2026-10-15; three runs gave the same 3 auto-accepted / 2 review split.

If the endpoint is unavailable, the notebook prints `(FM API unavailable: ...; using fallback)`
and uses fixed extractions instead (2 auto-accepted, 3 needs review).

## Step 1, seed

```text
Seeded 5 analyst case notes
```

The cell deletes every row in `bank.case_note` and seeds five notes. Reset your branch afterwards
if a later journey needs the original case notes.

## Step 2, show the case notes

```text
Analyst case notes (5 total):
  5 CTA-100240: Three card-not-present charges overnight to a foreign merchant the cus...
  6 CTA-300421: Four outbound SPEI transfers in two days to a CLABE registered yesterd...
  7 CTA-200311: Customer disputes a CoDi payment they say was charged twice at a Monte...
  8 CTA-100235: A few small USD charges followed by a larger one, same online merchant...
  9 CTA-100240: Something looked off on the account this morning, maybe a login from a...
```

The `note_id` values are serial and keep counting across runs, so they will not necessarily
start at 1.

## Step 3, extraction with confidence routing

```text
Extraction results:
  Auto-accepted (conf >= 0.75): 3
  Needs review   (conf <  0.75): 2

Auto-accepted entries:
  fraud/card_compromise: conf=0.90
  AML/possible_structuring: conf=0.90
  dispute/possible_duplicate_charge: conf=0.78

Needs review:
  fraud/possible_card_testing: conf=0.55
  other/possible_unusual_login: conf=0.30
```

Labels vary (another run returned `card_not_present_fraud` and `possible_suspicious_login`).
The pattern held in every run:
- The card-fraud and AML (PLD) notes: confidence 0.90–0.95, auto-accepted.
- The CoDi dispute: about 0.78, just over the threshold, auto-accepted.
- The USD-charges note (card testing or travel) and the vague login note: 0.30–0.55, sent to review.

## Step 4, human correction

```text
Analyst corrected note_id=9: category=fraud, finding=account_takeover_suspected, status=corrected
```

The analyst corrects the lowest-confidence `needs_review` row, the vague login note. The
correction lands in the same row; no second table, no sync.

## Step 5, analytics

```text
=== Learning Loop Analytics ===

Processed: 5
  Auto-accepted: 3
  Needs review:  1
  Corrected:     1

Avg confidence (auto-accepted): 0.877
Avg confidence (needs review):  0.550
```

## Full run

Running `python learning_loop.py` with no arguments prints the whole story (live run, 2026-10-15):

```text
Seeding analyst case notes (5 entries):
  - CTA-100240: Three card-not-present charges overnight to a foreign mercha...
  - CTA-300421: Four outbound SPEI transfers in two days to a CLABE register...
  - CTA-200311: Customer disputes a CoDi payment they say was charged twice ...
  - CTA-100235: A few small USD charges followed by a larger one, same onlin...
  - CTA-100240: Something looked off on the account this morning, maybe a lo...

Running AI extraction (5 write-ups):
  - Note 6: category=fraud, confidence=0.90, status=auto_accepted
  - Note 7: category=AML, confidence=0.93, status=auto_accepted
  - Note 8: category=dispute, confidence=0.78, status=auto_accepted
  - Note 9: category=fraud, confidence=0.55, status=needs_review
  - Note 10: category=other, confidence=0.40, status=needs_review

Human correction (analyst reviews uncertain entries):
  - Note 10: analyst set category=fraud, finding=account_takeover_suspected (was uncertain)

Analytics:
  Total: 5
  Auto-accepted: 3
  Needs review: 1
  Corrected by human: 1
  Avg confidence (auto-accepted): 0.870
  Avg confidence (needs review): 0.550
  Accuracy of auto-accepted: 100% (no corrections needed)

Done. One table is the store, the review queue, the audit trail, and the analytics source.
```

## The numbers that matter

| What | Expected | Why it matters |
| ---- | -------- | -------------- |
| auto-accept threshold | 0.75 confidence | typical ML threshold (tunable) |
| routed to review in this run | 2 of 5 | the vague notes go to a person |
| human correction | one UPDATE on the same row | AI output and correction live together |
| accuracy tracking | stored in same table | no data movement, instant analytics |

> **From the field**
> Real learning loops batch extractions (call the model once per 100 case notes), cache model
> responses (avoid re-extracting the same note twice), and implement feedback loops where
> corrections automatically retrain the model. This journey shows the simplest pattern: one
> table, one model call per note, accuracy measured from SQL. Production systems add
> async jobs, model versioning, and A/B testing on the same schema.
