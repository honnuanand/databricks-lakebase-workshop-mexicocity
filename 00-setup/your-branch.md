# 5 · Your branch

This is where the workshop actually begins. You'll create your own zero-copy branch off the
shared `production`, and load the factory onto it. Every journey runs here.

## Name your branch

Pick a unique branch id, `u-` followed by your name or initials, so you don't collide with
anyone else on a shared project:

```bash
export LB_BRANCH=u-alex        # use YOUR name
```

Add that line to your `workshop.env` alongside `LB_PROFILE`, `LB_PROJECT`, and `LB_SCHEMA`. Your
full environment is now:

```bash
export LB_PROFILE=workshop
export LB_PROJECT=factory
export LB_BRANCH=u-alex
export LB_SCHEMA=factory
```

## Create it

```bash
python ../common/scripts/branch.py --create
```

```text
create_branch API returned in ~700 ms
branch u-alex is ACTIVE in ~2.4s  (host <something>.database.cloud.databricks.com)
```

That's the zero-copy branch. It forked `production` copy-on-write, so it copied no data, and its
compute endpoint reached `ACTIVE` in about two seconds.

> **From the field**
> Notice the two numbers. The `create_branch` API call comes back in under a second: that's the
> copy-on-write metadata being accepted. The branch then becomes connectable (endpoint `ACTIVE`)
> in about two seconds. When you hear "branch in seconds," this is the honest shape of it: the
> data is ready almost immediately, and attaching compute you can connect to takes the couple of
> seconds. No full-database copy is ever made.

## Load the factory

Put the schema and seed data onto your branch:

```bash
python ../common/scripts/load_factory.py
```

```text
Loading schema ...
Seeding data ...
Done. Row counts:
  plant                 3 rows
  machine               8 rows
  sensor_reading        5 rows
  product               2 rows
  part                  5 rows
  bom_edge              5 rows
  work_order            2 rows
  operation             3 rows
  supplier              3 rows
  warehouse             2 rows
  inventory             5 rows
  part_supplier         3 rows
  maintenance_log       4 rows
  agent_memory          0 rows
```

Your factory is live on your branch.

## If you ever want a clean slate

Any journey can leave your branch in whatever state you like, because it's yours. To start over,
reset drops your branch and rebuilds it fresh from production, then reloads the factory:

```bash
python ../common/scripts/branch.py --reset
```

> **Tip**
> `--reset` is your safety net. Throughout the workshop you'll delete data, break things, and run
> destructive SQL on purpose. None of it touches anyone else, and reset always brings you back to
> a known-good factory in seconds.

---

Next: [`verify.md`](verify.md), confirm it's all working.
