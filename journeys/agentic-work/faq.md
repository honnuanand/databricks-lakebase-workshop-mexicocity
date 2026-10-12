# The agent does the work, FAQ

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

## The account was already frozen (from a prior run)

The script is idempotent: `--step review` (and a full run) first calls `_setup()`, which puts
ACCT-100240 back on `watch` and clears any prior hold flag and memory. If you ran only
`--step review-again` and see unexpected state, run a full `python agentic_work.py` to reset
and replay the whole story. To reset by hand:

```bash
python lakebase.py --sql "UPDATE bank.account SET status='watch' WHERE account_id='ACCT-100240'"
python lakebase.py --sql "DELETE FROM bank.case_note WHERE account_id='ACCT-100240' AND action='hold_placed'"
python lakebase.py --sql "DELETE FROM bank.agent_memory WHERE namespace='default' AND content LIKE '%ACCT-100240%'"
```

## The agent didn't call any tools

The script drives the tool calls directly (the SQL reads and writes), and uses the Foundation
Model API only to *narrate* the decision. If the FM API is unavailable, you'll see a
`(FM API unavailable: ...; using fallback)` line and a canned narration, and the tool calls
(the real work) still run. To check the endpoint:

```bash
databricks serving-endpoints list --profile workshop | grep claude
```

Set `FM_ENDPOINT=<name>` if your model endpoint is named differently.

## The tool call succeeded but the state didn't change

If you see "place_hold ... froze account" but the account still shows `watch`, check:

1. **Are you querying the right table/branch?** Run:
   ```bash
   python lakebase.py --sql "SELECT account_id, status FROM bank.account WHERE account_id='ACCT-100240'"
   ```
   If the status is still `watch`, the UPDATE did not commit on this branch.

2. **Check the case_note flag**: the hold writes both an account UPDATE and a case_note INSERT:
   ```sql
   INSERT INTO bank.case_note (account_id, writeup, category, finding, action, confidence)
   VALUES ('ACCT-100240', '...', 'fraud', '...', 'hold_placed', 0.95)
   ```
   If that failed (for example a foreign-key violation on account_id), the case_note table
   would be unchanged. Look for an error in the script output.

3. **Branch isolation**: if you're on a different branch than when the agent ran, you'd see
   different data. Confirm your branch: `echo $LB_BRANCH`.

## The second review didn't refuse; it placed another hold

If you called the script twice and both times saw "hold placed", the memory table might not be
keeping the agent's log. Check:

```bash
python lakebase.py --sql \
  "SELECT agent_id, content FROM bank.agent_memory WHERE namespace='default' AND content LIKE '%ACCT-100240%'"
```

You should see the "placed hold on ACCT-100240" row from the first call. If not, the agent's
memory is on a different schema or branch. Confirm `$LB_SCHEMA` (default: `bank`).

## I want to use a different account

The script hardcodes `ACCT-100240` (the seeded fraud signal). To use a different account, edit
the script:

1. Open `agentic_work.py`.
2. Change this line:
   ```python
   ACCOUNT_ID = "ACCT-100240"
   ```
3. Re-run. Pick an account that has transactions with a meaningful anomaly score, otherwise
   the hold decision has nothing to act on.

Or run the tool calls by hand:

```bash
python lakebase.py --sql \
  "SELECT account_id, status FROM bank.account WHERE status='watch' LIMIT 5"

python lakebase.py --sql \
  "UPDATE bank.account SET status='frozen' WHERE account_id='ACCT-XXXXXX'"
```

## Can I test this with my own agent?

Yes, if your agent supports a tool-calling pattern:

1. Deploy an agent that accepts a `get_account_risk` tool and a `place_hold` tool.
2. Have `get_account_risk` read `bank.account` and `bank.txn`.
3. Have `place_hold` UPDATE the account status and INSERT a `case_note` flag row.
4. Point the script at your Model Serving endpoint by setting `FM_ENDPOINT=<name>`.

The journey script is a minimal example; production agents would add error handling, retries,
and transaction isolation.

## Why write to both account.status and case_note?

The hold is one logical action with two durable effects:

- **`account.status = 'frozen'`** is the live operational state: downstream systems that read
  the account see the hold immediately.
- **`case_note` with `action='hold_placed'`** is the audit trail: who/what acted, why (the
  anomaly score), and when. It is also the stable marker that makes a re-run idempotent.

Keeping both in one Lakebase database means the operational change and its audit record are a
single transaction, not a sync between two systems.
