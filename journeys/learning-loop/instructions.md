# Human-in-the-loop, instructions

## How to run this journey

There are a few ways to work through the steps. Pick one:

- **Notebook, step by step (recommended for learning):** open [`learning_loop.ipynb`](learning_loop.ipynb) and run one cell at a time. Reading each result before the next step is where the learning happens.
- **In a Databricks workspace:** import [`learning_loop_databricks.py`](learning_loop_databricks.py) and run it cell by cell there.
- **By hand:** follow the numbered steps below, copying each command yourself.
- **Just see it work:** run `python learning_loop.py` from this folder to execute the whole thing at once. Fast, but you learn the most from the notebook.

Run these on your own branch. If you haven't done [`../../00-setup/`](../../00-setup/), do that
first; you need `LB_PROFILE`, `LB_PROJECT`, `LB_BRANCH`, and `LB_SCHEMA` set, and the factory
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

### Step 1, check the maintenance_log table

The factory schema includes the `maintenance_log` table (see `common/scripts/factory_schema.sql`).
This is where free-text maintenance write-ups live, and where the AI extraction lands. Check the
structure:

```bash
python ../../common/scripts/lakebase.py --sql \
  "SELECT column_name, data_type FROM information_schema.columns \
   WHERE table_name='maintenance_log' ORDER BY ordinal_position"
```

You should see columns: `log_id`, `machine_id`, `ts`, `writeup`, `system`, `defect`, `action`,
`confidence`. The first three are the raw input; the last four are where the AI extraction
lands.

### Step 2, seed with free-text maintenance write-ups

These are real-world messy write-ups. Some are clear and unambiguous; others are vague. The AI
should score its confidence accordingly:

```bash
python learning_loop.py --step seed
```

The script inserts 5 write-ups:
1. "Hydraulic line to the bearing housing leaking...", clear and specific.
2. "CNC spindle running hot...", clear, standard maintenance pattern.
3. "Tool changer intermittent...", somewhat unclear with a question mark.
4. "Robot arm slow to home...", clear problem, unclear root cause.
5. "Something off with the thing on the right side...", very vague and uncertain.

Read them back:

```bash
python ../../common/scripts/lakebase.py --sql \
  "SELECT log_id, machine_id, writeup FROM factory.maintenance_log ORDER BY log_id"
```

### Step 3, run AI extraction

Claude reads each write-up and extracts system/defect/action + a confidence score:

```bash
python learning_loop.py --step extract
```

The script:
1. For each write-up, calls Claude with a prompt: "Extract system, defect, action from this
   maintenance note. Respond with JSON."
2. Claude returns the extraction + a confidence score (0-1).
3. The script updates each maintenance_log row with the AI extraction.
4. Extractions with confidence > 0.75 get `status = 'auto_accepted'`; others get
   `status = 'needs_review'`.

You should see output like:

```text
Extracted 5 maintenance write-ups:
  1. system=hydraulic line to bearing housing, confidence~0.90, status=auto_accepted
  2. system=CNC spindle cooling, confidence~0.85, status=auto_accepted
  3. system=CNC tool changer, confidence~0.60, status=needs_review
  4. system=robot arm drive, confidence~0.60, status=needs_review
  5. system=hydraulics (uncertain), confidence~0.25, status=needs_review
```

### Step 4, see the auto-accept/review split

Query the maintenance_log to see which extracted cleanly and which need human review:

```bash
python ../../common/scripts/lakebase.py --sql \
  "SELECT log_id, writeup, system, defect, ROUND(confidence::numeric, 2), status \
   FROM factory.maintenance_log ORDER BY log_id"
```

The first two should show `status = 'auto_accepted'` with high confidence (> 0.75). The last
three should show `status = 'needs_review'` with lower confidence.

### Step 5, simulate a human correction

An engineer reviews the uncertain entries and corrects the lowest-confidence one. Run:

```bash
python learning_loop.py --step correct
```

The script identifies the lowest-confidence needs_review row and corrects it:
- AI said: system=hydraulics (uncertain), defect=vague
- Human clarifies: system=hydraulics, defect=press_ram_seal_leak (more specific)
- Updates the row with `status = 'corrected'` and a timestamp.

Check the update:

```bash
python ../../common/scripts/lakebase.py --sql \
  "SELECT log_id, system, defect, status FROM factory.maintenance_log WHERE status='corrected'"
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
  Total: 5 extractions
  Auto-accepted: 2 (confidence >= 0.75)
  Needs review: 3 initially, 2 after correction
  Corrected by human: 1
  Accuracy of auto-accepted: 100% (2 out of 2 were correct)
  Confidence >= 0.75: average about 0.87
  Confidence < 0.75: average about 0.5
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
