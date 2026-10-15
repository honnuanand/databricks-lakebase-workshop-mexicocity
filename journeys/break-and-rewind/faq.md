# Break it, then rewind, FAQ

## It failed with a "refresh token" or authentication error

Your Databricks login expired (they last about an hour). Re-run the login from
[`../../00-setup/auth.md`](../../00-setup/auth.md):

```bash
databricks auth login --host https://<your-workspace>.cloud.databricks.com --profile workshop
```

Then re-run the step.

## "Missing required env var LB_PROJECT / LB_BRANCH"

You're in a terminal that didn't load your environment. Re-source it:

```bash
source workshop.env    # the file you built in 00-setup
```

Or re-export `LB_PROFILE`, `LB_PROJECT`, `LB_BRANCH`, `LB_SCHEMA` by hand.

## The delete failed with a foreign-key error

Settlements reference trades by a foreign key, so you cannot delete a trade while a settlement
still points at it. Delete the children first:

```sql
DELETE FROM bank.settlement;   -- children first
DELETE FROM bank.trade;        -- then the parents
```

The journey script already does this in the right order. If you ran a raw `DELETE FROM bank.trade`
by hand and hit the error, delete `bank.settlement` first and retry.

## The recovery branch never reached ACTIVE

The script waits about 30 seconds. If it times out:

- Check the branch state directly: `python branch.py --status` (point `LB_BRANCH` at the recovery branch).
- A cold project can be slower on the first branch of a session. Try the recovery again.
- If it persistently fails to provision, the project may be scaled to zero or the instance may be stopped. Start it (see [Scale to zero](../scale-to-zero/)) and retry.

## Can I recover data from weeks ago?

Only within the project's history window: 7 days by default, set in the project's settings. You can branch to any LSN within that window. The journey only demonstrates seconds, but the capability spans the entire retention window. If you delete the trade book on Monday and remember on Friday, PITR still works.

## Why is "production" my own branch here, not the real production?

In this journey, the thing you delete from is *your* branch (`u-<name>`), not the shared `production` branch. Your branch plays the role of "production" for the purpose of the demo, so you never risk anyone else's data. The mechanics are identical; only the source branch differs.

## Did the recovery really not leave storage behind?

Correct. The PITR branch is a zero-copy branch from a past LSN. The branch shares the page server's storage (only changed pages are written separately), and once you delete it, those changed pages are freed. The recovered data lived in the branch's copy-on-write storage while it existed; discarding the branch removes it.

## How is this different from Aurora Backtrack or similar?

Lakebase uses the same copy-on-write mechanism as branching, so PITR is *not* a separate feature, it's branching at a past LSN. An Aurora Backtrack moves the production database back in time in place. A Lakebase PITR branch creates an isolated, read-only copy at that past time, leaving production unchanged and letting you read the old data while production keeps running. You get the best of both: recovery speed (seconds) and isolation (the recovery branch is independent).

## I see "source_branch_lsn" in the SDK docs. Is that what the script uses?

Yes. The script queries the current LSN before the delete, stores it, then calls `create_branch()` with `source_branch_lsn=<that LSN>` to create the recovery branch. The same call works for branching from now (omit `source_branch_lsn`) or from the past (include it). The mechanism is identical.
