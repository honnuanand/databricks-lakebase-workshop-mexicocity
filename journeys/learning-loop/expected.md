# Human-in-the-loop, expected results

Use this to check your run. Claude's exact extractions will vary, but the *shape* is what matters:
high-confidence entries auto-accept, low-confidence route to review, and corrections are recorded
atomically with confidence and status fields.

## Step 1, table structure

```text
log_id | machine_id | ts | writeup | system | defect | action | confidence
```

The raw input (first 4 columns) and the AI extraction (last 4 columns).

## Step 2, seed

```text
(1, 'M-204', ..., 'Hydraulic line on leg B leaking, found ice on exterior, isolated line, monitor pressure.')
(2, 'M-405', ..., 'L MLG tire worn to indicator, replace at next A-check.')
(3, 'M-301', ..., 'Cabin ka-band intermittent, pax complaints on last 3 legs; swap modem?')
(4, 'M-108', ..., 'APU slow to start, ~40s hung start x2, investigate.')
(5, 'M-204', ..., 'Something off with the thing on the right side, maybe hydraulics? not sure')
```

Five messy, real-world maintenance write-ups.

## Step 3, extract

```text
Extracted 5 maintenance write-ups:
  1. system=hydraulic, defect=line_leak, action=isolated_line, confidence=0.92, status=auto_accepted
  2. system=landing_gear, defect=tire_worn, action=replace_at_check, confidence=0.89, status=auto_accepted
  3. system=communications, defect=intermittent_reception, action=swap_modem, confidence=0.68, status=needs_review
  4. system=apu, defect=slow_start, action=investigate, confidence=0.71, status=needs_review
  5. system=?, defect=vague, action=investigate, confidence=0.38, status=needs_review
```

The exact field values will vary (Claude's extraction is probabilistic), but the pattern is clear:
- Entries 1-2: high confidence (> 0.75), auto-accepted
- Entries 3-5: low confidence, needs review

## Step 4, after extraction

```text
(1, 'Hydraulic line...', 'hydraulic', 'line_leak', 0.92, 'auto_accepted')
(2, 'L MLG tire...', 'landing_gear', 'tire_worn', 0.89, 'auto_accepted')
(3, 'Cabin ka-band...', 'communications', 'intermittent', 0.68, 'needs_review')
(4, 'APU slow...', 'apu', 'slow_start', 0.71, 'needs_review')
(5, 'Something off...', 'unknown', 'unknown', 0.38, 'needs_review')
```

## Step 5, after correction

Entry 3 is updated:

```text
Before:  system=communications, defect=intermittent, status=needs_review
After:   system=communications, defect=modem_failure, status=corrected
```

The row is atomically updated; no second table, no sync.

## Step 6, analytics

```text
Total extractions: 5
  auto_accepted: 2 (confidence >= 0.75)
  needs_review: 3
  corrected: 1

Confidence >= 0.75 (auto-accepted):
  count: 2
  avg confidence: 0.905
  all were correct: yes

Confidence < 0.75 (needs_review):
  count: 3
  avg confidence: 0.59
  human corrected: 1 out of 3

Accuracy: 2 auto-accepted, 0 errors → 100%
```

The entire learning loop is one table with confidence, status, and audit fields.

## Full run

Running `python learning_loop.py` with no arguments prints the whole story:

```text
1. Seeding maintenance write-ups (5 entries):
  - M-204: Hydraulic line on leg B leaking...
  - M-405: L MLG tire worn to indicator...
  - M-301: Cabin ka-band intermittent...
  - M-108: APU slow to start...
  - M-204: Something off with the thing on the right side...

2. Running AI extraction (Claude reads each write-up):
  - Entry 1: system=hydraulic, confidence=0.92, status=auto_accepted
  - Entry 2: system=landing_gear, confidence=0.89, status=auto_accepted
  - Entry 3: system=communications, confidence=0.68, status=needs_review
  - Entry 4: system=apu, confidence=0.71, status=needs_review
  - Entry 5: system=unknown, confidence=0.38, status=needs_review

3. Human correction (engineer reviews uncertain entries):
  - Entry 3: modem_failure (corrected from intermittent)
  - Status updated to 'corrected'

4. Analytics (accuracy measurement):
  Total: 5
  Auto-accepted: 2 (conf >= 0.75)
  Needs review: 3
  Corrected: 1
  Accuracy of auto-accepted: 100%

Done. One table is the store, the review queue, the audit trail, and the analytics source.
```

## The numbers that matter

| What | Expected | Why it matters |
| ---- | -------- | -------------- |
| auto-accept threshold | 0.75 confidence | typical ML threshold (tunable) |
| extractions routed to review | ~40-60% in real data | depends on write-up clarity |
| FM API latency per extraction | 1-2 seconds | single model call, no round-trips |
| human correction latency | atomic UPDATE | one row, one transaction |
| accuracy tracking | stored in same table | no data movement, instant analytics |

> **From the field**
> Real learning loops batch extractions (call the model once per 100 write-ups), cache model
> responses (avoid re-extracting the same note twice), and implement feedback loops where
> corrections automatically retrain the model. This journey shows the simplest pattern: one
> table, one model call per write-up, accuracy measured from SQL. Production systems add
> async jobs, model versioning, and A/B testing on the same schema.
