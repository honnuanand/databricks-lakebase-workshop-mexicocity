# 3 · Provision a project

You need a Lakebase **project** to work in. A project is the container that holds branches
(including `production`) and their compute endpoints. See
[`docs/lakebase-sdk.md`](../docs/lakebase-sdk.md) for the object model.

There are two ways to do this step. Your instructor will tell you which applies.

## Path A: use a project your instructor already made

In a group workshop, the instructor usually provisions **one shared project** and everyone
branches off it (that's the whole point of per-user branches). If so, they'll give you a project
id. Just set it:

```bash
export LB_PROJECT=<project-id-you-were-given>
```

Confirm it's reachable:

```bash
python ../common/scripts/provision.py --project "$LB_PROJECT" --profile "$LB_PROFILE" --status
```

```text
project factory production endpoint ACTIVE in ~0.0s
  host: <something>.database.cloud.databricks.com
```

Then skip to [`grants.md`](grants.md).

## Path B: provision your own project

Running solo, or want your own? Create one. The project comes with a `production` branch and a
primary endpoint automatically.

```bash
python ../common/scripts/provision.py --project factory --profile "$LB_PROFILE"
```

```text
create_project API returned in ~800 ms
project factory production endpoint ACTIVE in ~3.7s
  host: <something>.database.cloud.databricks.com

Now run:  export LB_PROJECT=factory
```

Then set it and add it to your env file:

```bash
export LB_PROJECT=factory
```

> **From the field**
> The `create_project` API call returns in well under a second. The project then reaches a
> queryable ACTIVE state in about 3 to 4 seconds in our measurements. That is the honest
> "provision in seconds" number: fast, real, and not instantaneous. Branch creation (next steps)
> is faster still, because a branch adds no new storage.

> **Note**
> Creating a project may require permission on the Lakebase instance. If `create_project` fails
> with a permission error, use Path A with a project your instructor provisioned, or ask an admin
> to grant you access. The [`faq`](../journeys/branch-the-brain/faq.md) files cover permission
> errors per journey.

---

Next: [`grants.md`](grants.md) — grant the access the workshop needs.
