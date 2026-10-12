# Human-in-the-loop, expected results

Use this to check your run. Claude's exact extractions will vary, but the *shape* is what matters:
high-confidence entries auto-accept, low-confidence route to review, and corrections are recorded
atomically with confidence and status fields.

## Step 1, table structure

```text
note_id | account_id | ts | writeup | system | defect | action | confidence
```

The raw input (first 4 columns) and the AI extraction (last 4 columns).

## Step 2, seed

```text
(1, 'ACCT-100240', ..., 'Hydraulic line to the bearing housing leaking on the press downstroke, isolated the line, monitor pressure.')
(2, 'ACCT-300421', ..., 'CNC spindle running hot, thermal alarm at 71C, coolant flow low, replace pump at next PM.')
(3, 'ACCT-200311', ..., 'Tool changer intermittent on the CNC, last 3 cycles hung; swap the actuator?')
(4, 'ACCT-100235', ..., 'Robot arm slow to home, ~40s hesitation on startup x2, investigate the drive.')
(5, 'ACCT-100240', ..., 'Something off with the thing on the right side of the press, maybe hydraulics? not sure')
```

Five messy, real-world maintenance write-ups from the factory floor.

## Step 3, extract

```text
Extracted 5 maintenance write-ups:
  1. system=hydraulic line to bearing housing, defect=leak, confidence~0.90, status=auto_accepted
  2. system=CNC spindle cooling, defect=overheating, confidence~0.85, status=auto_accepted
  3. system=CNC tool changer, defect=intermittent, confidence~0.60, status=needs_review
  4. system=robot arm drive, defect=slow response, confidence~0.60, status=needs_review
  5. system=hydraulics (uncertain), defect=vague, confidence~0.20-0.30, status=needs_review
```

The exact field values will vary (Claude's extraction is probabilistic), but the pattern is clear:
- Entries 1-2: high confidence (over 0.75), auto-accepted
- Entries 3-5: lower confidence, routed to review

## Step 4, after extraction

```text
(1, 'Hydraulic line...', 'hydraulic line to bearing housing', 'leak', 0.90, 'auto_accepted')
(2, 'CNC spindle...', 'CNC spindle cooling', 'overheating', 0.85, 'auto_accepted')
(3, 'Tool changer...', 'CNC tool changer', 'intermittent', 0.60, 'needs_review')
(4, 'Robot arm...', 'robot arm drive', 'slow response', 0.60, 'needs_review')
(5, 'Something off...', 'hydraulics (uncertain)', 'vague', 0.25, 'needs_review')
```

## Step 5, after correction

The script picks the lowest-confidence needs_review row dynamically and corrects it:

```text
Before:  system=hydraulics (uncertain), defect=vague, confidence=0.25, status=needs_review
After:   system=hydraulics, defect=press_ram_seal_leak, confidence=0.25, status=corrected
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
  avg confidence: about 0.87
  all were correct: yes

Confidence < 0.75 (needs_review):
  count: 3
  avg confidence: about 0.5
  human corrected: 1 out of 3

Accuracy: 2 auto-accepted, 0 errors → 100%
```

The entire learning loop is one table with confidence, status, and audit fields.

## Full run

Running `python learning_loop.py` with no arguments prints the whole story:

```text
1. Seeding maintenance write-ups (5 entries):
  - ACCT-100240: Hydraulic line to the bearing housing leaking...
  - ACCT-300421: CNC spindle running hot...
  - ACCT-200311: Tool changer intermittent on the CNC...
  - ACCT-100235: Robot arm slow to home...
  - ACCT-100240: Something off with the thing on the right side...

2. Running AI extraction (Claude reads each write-up):
  - Entry 1: system=hydraulic line to bearing housing, confidence~0.90, status=auto_accepted
  - Entry 2: system=CNC spindle cooling, confidence~0.85, status=auto_accepted
  - Entry 3: system=CNC tool changer, confidence~0.60, status=needs_review
  - Entry 4: system=robot arm drive, confidence~0.60, status=needs_review
  - Entry 5: system=hydraulics (uncertain), confidence~0.25, status=needs_review

3. Human correction (engineer reviews uncertain entries):
  - Entry 5 (lowest confidence): press_ram_seal_leak (corrected from vague)
  - Status updated to 'corrected'

4. Analytics (accuracy measurement):
  Total: 5
  Auto-accepted: 2 (confidence >= 0.75)
  Needs review: 3 (then 2 after correction)
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
