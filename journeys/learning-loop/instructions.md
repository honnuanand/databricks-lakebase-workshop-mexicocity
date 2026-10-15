# Human-in-the-loop, instructions

## How to run this journey

There are a few ways to work through the steps. Pick one:

- **Notebook, step by step (recommended for learning):** open [`learning_loop.ipynb`](learning_loop.ipynb) and run one cell at a time. Reading each result before the next step is where the learning happens.
- **In a Databricks workspace:** import [`learning_loop_databricks.py`](learning_loop_databricks.py) and run it cell by cell there.
- **By hand:** follow the numbered steps below, copying each command yourself.
- **Just see it work:** run `python learning_loop.py` from this folder to execute the whole thing at once. Fast, but you learn the most from the notebook.

Run these on your own branch. If you haven't done [`../../00-setup/`](../../00-setup/), do that
first; you need `LB_PROFILE`, `LB_PROJECT`, `LB_BRANCH`, and `LB_SCHEMA` set, and the bank
loaded.

Everything here is a single script you can read: [`./learning_loop.py`](./learning_loop.py).
You can run it end to end, or follow the steps by hand to see each piece.

## Run it end to end

```bash
cd journeys/learning-loop
python learning_loop.py
```

This walks the whole learning loop: extract, route, correct, analyze. Read on for what each step
does; the exact output to expect is in [`expected.md`](expected.md).

## Or step through it by hand

### Step 1, check the case_note table

The bank schema includes the `case_note` table (see `common/scripts/finance_schema.sql`).
This is where free-text analyst case notes live, and where the AI extraction lands. Check the
structure:

```bash
python ../../common/scripts/lakebase.py --sql \
  "SELECT column_name, data_type FROM information_schema.columns \
   WHERE table_name='case_note' ORDER BY ordinal_position"
```

You should see columns: `note_id`, `account_id`, `ts`, `writeup`, `category`, `finding`,
`action`, `confidence`. The first four are the raw input; the last four are where the AI
extraction lands.

### Step 2, seed with free-text case notes

These are real-world messy analyst notes. Some are clear and unambiguous; others are vague. The
AI should score its confidence accordingly:

```bash
python learning_loop.py --step seed
```

The script inserts 5 case notes:
1. CTA-100240: "Three card-not-present charges overnight... froze the card", clear fraud.
2. CTA-300421: "Large outbound wire... just under the reporting threshold", clear AML pattern.
3. CTA-200311: "Customer disputes a charge they say posted twice", somewhat unclear.
4. CTA-100235: "A few small foreign-currency charges then a larger one", card testing or travel.
5. CTA-100240: "Something looked off... maybe the login location? not sure", very vague.

Read them back:

```bash
python ../../common/scripts/lakebase.py --sql \
  "SELECT note_id, account_id, writeup FROM bank.case_note ORDER BY note_id"
```

### Step 3, run AI extraction

Claude reads each case note and extracts category/finding/action + a confidence score:

```bash
python learning_loop.py --step extract
```

The script:
1. For each case note, calls Claude with a prompt: "Extract category, finding, action from this
   fraud/AML note. Respond with JSON."
2. Claude returns the extraction + a confidence score (0-1).
3. The script updates each `case_note` row with the AI extraction.
4. Extractions with confidence > 0.75 get `status = 'auto_accepted'`; others get
   `status = 'needs_review'`.

You should see output like:

```text
Running AI extraction (5 write-ups):
  - Note 25: category=fraud, confidence=0.92, status=auto_accepted
  - Note 26: category=AML, confidence=0.90, status=auto_accepted
  - Note 27: category=dispute, confidence=0.60, status=needs_review
  - Note 28: category=fraud, confidence=0.50, status=needs_review
  - Note 29: category=fraud, confidence=0.30, status=needs_review
```

The note IDs and the exact confidences depend on the model and on how many case notes already
sat in the table; what matters is the split: clear notes auto-accept, ambiguous ones route.

### Step 4, see the auto-accept/review split

Query the case notes to see which extracted cleanly and which need human review:

```bash
python ../../common/scripts/lakebase.py --sql \
  "SELECT note_id, writeup, category, finding, ROUND(confidence::numeric, 2), status \
   FROM bank.case_note WHERE status IS NOT NULL ORDER BY note_id"
```

The two clearest notes should show `status = 'auto_accepted'` with high confidence (> 0.75). The
others should show `status = 'needs_review'` with lower confidence.

### Step 5, simulate a human correction

An analyst reviews the uncertain entries and corrects the lowest-confidence one. Run:

```bash
python learning_loop.py --step correct
```

The script identifies the lowest-confidence needs_review row and corrects it:
- AI said: category=fraud (uncertain), finding vague
- Analyst clarifies: category=fraud, finding=account_takeover_suspected (more specific)
- Updates the row with `status = 'corrected'` and a timestamp.

Check the update:

```bash
python ../../common/scripts/lakebase.py --sql \
  "SELECT note_id, category, finding, status FROM bank.case_note WHERE status='corrected'"
```

### Step 6, run analytics

Query the table as analytics would, measuring accuracy and drift:

```bash
python learning_loop.py --step analytics
```

The script:
1. Counts extractions by status.
2. Computes accuracy: how many auto-accepted entries were *also* correct (vs. which ones got
   corrected)?
3. Shows confidence distribution.

You should see a summary like:

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

## What you just did

You ran the full human-in-the-loop learning loop:
1. Extracted insights from free text with confidence scores.
2. Routed by threshold: high-confidence auto-accept, uncertain to human review.
3. Recorded corrections atomically in the same table.
4. Analyzed accuracy and drift from SQL.

The entire flow lives on one governed table, no separate ML pipeline, no sync between systems.
Compare the output you saw against [`expected.md`](expected.md), and if anything went sideways,
[`faq.md`](faq.md) has the common causes.
