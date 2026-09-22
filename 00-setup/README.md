# 00 · Setup — get connected

This is the on-ramp. About 20 minutes, done once, and it unblocks every journey. By the end you
have a live Lakebase project, the access it needs, and **your own zero-copy branch** to work on.

Work through these in order:

| Step | File | What it does |
| ---- | ---- | ------------ |
| 1 | [`prereqs.md`](prereqs.md) | Tools you need: Databricks workspace access, the CLI, Python, and two libraries. |
| 2 | [`auth.md`](auth.md) | Log in to your Databricks workspace so the CLI and SDK can act as you. |
| 3 | [`provision.md`](provision.md) | Create the workshop's Lakebase project (or point at a shared one), so you never touch the live demo. |
| 4 | [`grants.md`](grants.md) | Grant the access the workshop needs: a Postgres role, schema grants, and the project permission that lets you branch. |
| 5 | [`your-branch.md`](your-branch.md) | Create your personal zero-copy branch `u-<name>` and load the factory schema onto it. |
| 6 | [`verify.md`](verify.md) | Connect, run `SELECT 1`, and confirm your branch is live and serving. |

## Why a branch per person

Everyone in the workshop shares one factory database, but you each get your **own branch** of
it. A branch is a full, isolated copy of the data that is free to create because Lakebase
branches are copy-on-write: nothing is duplicated until you change it. So a whole room can run
the workshop at the same time, each person breaking and rebuilding their own copy, without
touching anyone else's, and without touching the shared production data underneath.

That is the first real Lakebase idea in this workshop, and you use it before you even start:
your branch is where every journey runs. When you are done, dropping your branch leaves nothing
behind.

## The object model you're about to build in

Lakebase organizes storage and compute like this:

```mermaid
flowchart LR
  P["Project<br/>(provisioning container)"] --> B["Branch<br/>(zero-copy, copy-on-write)"]
  B --> E["Endpoint<br/>(connectable compute, host:5432)"]
  E --> D["Database<br/>(databricks_postgres)"]
  D --> S["Schema<br/>(factory)"]
  S --> T["Tables<br/>(machine, sensor_reading, work_order, ...)"]
```

A **project** holds everything. Inside it, **branches** are the git-style copies (production is
the default; yours is `u-<name>`). Each branch exposes an **endpoint**, the compute you actually
connect to over the Postgres wire. Behind the endpoint is a normal Postgres **database** with a
**schema** and your factory **tables**.

## When you're done

You'll have connected to your own branch and seen `SELECT 1` return. Then head to
[`../journeys/`](../journeys/) and start with **Branch the brain** — the same branching you just
used, turned into a hands-on journey.

> **Note**
> If any CLI or script step fails with an authentication or "refresh token" error, your login
> has expired. Re-run the login from [`auth.md`](auth.md) and try again. Each journey's `faq.md`
> lists the specific errors for that journey.
