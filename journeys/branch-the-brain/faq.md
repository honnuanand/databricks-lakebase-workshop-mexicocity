# Branch the brain, FAQ

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

## The fork failed with a permission error

Creating a branch needs `CAN_MANAGE` on the **project** (not the instance). If you're on a
shared project your instructor provisioned, ask them to grant it (see
[`../../00-setup/grants.md`](../../00-setup/grants.md)). If you provisioned your own project,
you're the owner and this shouldn't happen; make sure `LB_PROJECT` points at *your* project.

## The fork's endpoint never reached ACTIVE

The script waits about 30 seconds. If it times out:

- Check the branch state directly: `python branch.py --status` (point `LB_BRANCH` at the fork,
  or use `--step list` in the journey script to see it exists).
- A cold project can be slower on the first branch of a session. Try the fork again.
- If it persistently fails to provision, the project may be scaled to zero or the instance may be
  stopped. Start it (see [Scale to zero](../scale-to-zero/)) and retry.

## Why is "production" my own branch here, not the real production?

In this journey, the thing you fork is *your* branch (`u-<name>`), and the fork is a short-lived
experiment branch off it. Your branch plays the role of "production" for the purpose of the
demo, so you never touch the shared `production` branch or anyone else's. The mechanics are
identical; only the source branch differs.

## Did the fork really not copy any data?

Correct. Lakebase branches are copy-on-write: the fork shares your branch's storage as of the
moment you forked, and only pages you *change* on the fork get written separately. That's why the
fork of a tiny factory and a fork of a multi-terabyte database cost about the same to create, and
why discarding the fork leaves nothing behind.

## I discarded the fork. Is anything left over?

No. `delete_branch` removes the branch and its endpoint. Because only changed pages were ever
written, there's no leftover storage. Confirm with `--step list`: the `-exp` branch is gone and
your branch remains.

## How is this different from point-in-time restore?

Same machinery, different source. Here you branch from the current state of your branch. In
[Break it, then rewind](../break-and-rewind/) you branch from a *past* point in time (an earlier
WAL position), which is how restore works. A branch is "the database as of an LSN"; restore is
branching at a past LSN.
