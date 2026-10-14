# Human-in-the-loop, FAQ

## It failed with a "refresh token" or authentication error

Your Databricks login expired. Re-run the login from [`../../00-setup/auth.md`](../../00-setup/auth.md):

```bash
databricks auth login --host https://<your-workspace>.cloud.databricks.com --profile workshop
```

Then re-run the script.

## "Missing required env var LB_PROJECT / LB_BRANCH"

Re-source your environment:

```bash
source workshop.env
```

Or re-export `LB_PROFILE`, `LB_PROJECT`, `LB_BRANCH`, `LB_SCHEMA` by hand.

## The case_note table doesn't exist

The table is part of the bank schema, loaded during setup. If it's missing:

1. Check that you're on the right branch: `echo $LB_BRANCH`.
2. Check the schema loaded: `python lakebase.py --sql "SELECT count(*) FROM bank.account"`.
3. If bank.account exists but case_note doesn't, run the schema loader:
   ```bash
   python ../../common/scripts/load_bank.py
   ```

## Claude's extraction parsed incorrectly

The script expects Claude to return valid JSON with keys: `category`, `finding`, `action`,
`confidence`. If the JSON parsing failed, you'll see "(parse failed)" in the output. Possible
causes:

1. **Model version changed**: If you're using a different model endpoint, Claude's response
   format may differ.
2. **System prompt misinterpreted**: The script sends a specific prompt asking for JSON. Try
   running a manual test:
   ```bash
   python lakebase.py --fm "Return JSON with keys: category, finding, action, confidence."
   ```
3. **Timeout**: If the FM API timed out, the response would be incomplete. Check your network
   and the endpoint status. The script falls back to a crude keyword guess if the endpoint is
   unavailable, so the routing still demonstrates even without the model.

## All entries got auto-accepted (or all need review)

The confidence threshold is 0.75. If all extractions scored above that, it may be that Claude is
being overly confident, or the test case notes are all clear. If all scored below, the notes
may be too vague. You can:

1. **Adjust the threshold**: Edit `learning_loop.py`:
   ```python
   CONF_THRESHOLD = 0.60  # changed from 0.75
   ```
2. **Add ambiguous notes**: Edit the WRITEUPS list to include more vague entries.
3. **Run with different notes**: The script uses defaults; you can modify it to accept
   custom notes from stdin or a file.

## A correction didn't stick (the status didn't change to 'corrected')

The script simulates a human correction on the lowest-confidence row. If you see the row unchanged, check:

1. **Is the row being updated at all?** Query the table before and after the correction step:
   ```bash
   python lakebase.py --sql "SELECT note_id, status FROM bank.case_note WHERE status='corrected'"
   ```
   If no rows appear with status 'corrected', the UPDATE didn't run.

2. **Are you on the right branch?** If you're on a different branch than where the extraction
   happened, the data would be diverged. Confirm: `echo $LB_BRANCH`.

3. **Check the script logic**: The correction step uses:
   ```python
   cur.execute(f"UPDATE bank.case_note SET category=%s, finding=%s, status=%s WHERE note_id=%s",
               [..., 'corrected', ...])
   ```
   If that's failing, check the note_id and column names.

## I want to run extraction on my own case notes

The script hardcodes 5 case notes. To use your own, edit `learning_loop.py`:

1. Find the WRITEUPS list (near the top).
2. Replace it with your own (each entry is `(note_id, account_id, writeup)`):
   ```python
   WRITEUPS = [
       ("WU-001", "ACCT-100240", "Your first analyst case note..."),
       ("WU-002", "ACCT-200311", "Your second analyst case note..."),
   ]
   ```
3. Re-run the script.

Or modify the script to read from a CSV or file (not currently supported; you'd need to edit the
code).

## The analytics output looks wrong

The analytics step counts by status and computes accuracy. If the numbers don't make sense:

1. **Check the row counts**: Query the table manually:
   ```bash
   python lakebase.py --sql \
     "SELECT status, COUNT(*) FROM bank.case_note GROUP BY status"
   ```
2. **Check for missing corrections**: The script simulates one correction on the lowest-confidence row. If
   you want to correct more entries, edit the script's `correct()` function.
3. **Check confidence values**: Accuracy is computed over high-confidence (>= 0.75) entries.
   If none were auto-accepted, accuracy will be undefined. This is expected if the notes
   are all vague.

## Why is confidence between 0 and 1?

Confidence is a probability (0 = certain it's wrong, 1 = certain it's right). Claude's
extraction includes this score as part of its reasoning. Real systems may use calibrated
confidence (e.g., comparing the model's top-2 hypotheses), but for this journey we use Claude's
self-scored confidence directly. You can also post-process it: `confidence = min(max(...),
1.0)` to clamp outliers.

## Why does the table have both `finding` and `action` columns?

The schema separates:
- **category**: the kind of case (fraud, AML, dispute, other)
- **finding**: the specific issue (card_compromise, possible_structuring, double_charge_claim, etc.)
- **action**: what was done (froze_and_reissued, referred_to_aml, hold_for_review, etc.)

This separates concerns: the fraud ops team cares about the finding; case management cares about
the action; analytics wants to correlate category + finding to see fraud patterns.

In a simpler schema, you might combine them into one `observation` field. The schema here mirrors
realistic investigations systems where each concept is tracked separately for analytics.
