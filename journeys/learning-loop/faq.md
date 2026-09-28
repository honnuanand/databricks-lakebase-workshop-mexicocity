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

## The maintenance_log table doesn't exist

The table is part of the factory schema, loaded during setup. If it's missing:

1. Check that you're on the right branch: `echo $LB_BRANCH`.
2. Check the schema loaded: `python lakebase.py --sql "SELECT count(*) FROM factory.machine"`.
3. If factory.machine exists but maintenance_log doesn't, run the schema loader:
   ```bash
   python load_factory.py
   ```

## Claude's extraction parsed incorrectly

The script expects Claude to return valid JSON with keys: `system`, `defect`, `action`,
`confidence`. If the JSON parsing failed, you'll see "(parse failed)" in the output. Possible
causes:

1. **Model version changed**: If you're using a different model endpoint, Claude's response
   format may differ.
2. **System prompt misinterpreted**: The script sends a specific prompt asking for JSON. Try
   running a manual test:
   ```bash
   python lakebase.py --fm "Return JSON with keys: system, defect, action, confidence."
   ```
3. **Timeout**: If the FM API timed out, the response would be incomplete. Check your network
   and the endpoint status.

## All entries got auto-accepted (or all need review)

The confidence threshold is 0.75. If all extractions scored above that, it may be that Claude is
being overly confident, or the test write-ups are all clear. If all scored below, the write-ups
may be too vague. You can:

1. **Adjust the threshold**: Edit `learning_loop.py`:
   ```python
   CONF_THRESHOLD = 0.60  # changed from 0.75
   ```
2. **Add ambiguous write-ups**: Edit the WRITEUPS list to include more vague entries.
3. **Run with different write-ups**: The script uses defaults; you can modify it to accept
   custom write-ups from stdin or a file.

## A correction didn't stick (the status didn't change to 'corrected')

The script simulates a human correction on the lowest-confidence row. If you see the row unchanged, check:

1. **Is the row being updated at all?** Query the table before and after the correction step:
   ```bash
   python lakebase.py --sql "SELECT log_id, status FROM factory.maintenance_log WHERE status='corrected'"
   ```
   If no rows appear with status 'corrected', the UPDATE didn't run.

2. **Are you on the right branch?** If you're on a different branch than where the extraction
   happened, the data would be diverged. Confirm: `echo $LB_BRANCH`.

3. **Check the script logic**: The correction step uses:
   ```python
   cur.execute(f"UPDATE factory.maintenance_log SET system=%s, defect=%s, status=%s WHERE log_id=%s",
               [..., 'corrected', ...])
   ```
   If that's failing, check the log_id and column names.

## I want to run extraction on my own write-ups

The script hardcodes 5 write-ups. To use your own, edit `learning_loop.py`:

1. Find the WRITEUPS list (near the top).
2. Replace it with your own:
   ```python
   WRITEUPS = [
       ("entry-1", "Your first maintenance note..."),
       ("entry-2", "Your second maintenance note..."),
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
     "SELECT status, COUNT(*) FROM factory.maintenance_log GROUP BY status"
   ```
2. **Check for missing corrections**: The script simulates one correction on the lowest-confidence row. If
   you want to correct more entries, edit the script's `correct()` function.
3. **Check confidence values**: Accuracy is computed over high-confidence (>= 0.75) entries.
   If none were auto-accepted, accuracy will be undefined. This is expected if the write-ups
   are all vague.

## Why is confidence between 0 and 1?

Confidence is a probability (0 = certain it's wrong, 1 = certain it's right). Claude's
extraction includes this score as part of its reasoning. Real systems may use calibrated
confidence (e.g., comparing the model's top-2 hypotheses), but for this journey we use Claude's
self-scored confidence directly. You can also post-process it: `confidence = min(max(...),
1.0)` to clamp outliers.

## Why does the table have both `defect` and `action` columns?

The schema separates:
- **system**: which subsystem (hydraulic, CNC spindle, tool changer, robot arm, etc.)
- **defect**: the specific problem (leak, overheating, intermittent, slow response, etc.)
- **action**: what was done (isolated, replace, investigate, etc.)

This separates concerns: the operational team cares about the defect; the maintenance team cares
about the action; analytics wants to correlate system + defect to see failure patterns.

In a simpler schema, you might combine them into one `observation` field. The schema here mirrors
realistic maintenance systems where each concept is tracked separately for analytics.
