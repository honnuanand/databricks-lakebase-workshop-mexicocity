# 3 · Provision a project

You need a Lakebase **project** to work in. A project is the container that holds branches
(including `production`) and their compute endpoints. See
[`docs/lakebase-sdk.md`](../docs/lakebase-sdk.md) for the object model.

Lakebase provisioning is just an API, so you can reach it three ways: the **UI**, the
**Databricks CLI**, or the **workshop script** (which calls the SDK). Pick whichever fits how
you work. They all create the same thing. **However you provision, you verify the result in one
single way** (the last section), so success looks identical no matter which door you came in.

> **Note**
> In a group workshop the instructor usually provisions **one shared project** and everyone
> branches off it. If you were given a project id, you can skip provisioning: set
> `export LB_PROJECT=<id-you-were-given>` and go straight to **Verify** below.

## Option 1 — the UI

1. In your Databricks workspace, open **Compute** and find the **Lakebase / Postgres** section
   (labeled Lakebase Postgres, Beta).
2. Click **Create**, choose a **project** (Autoscaling), name it `factory`, and pick Postgres 17.
3. Create it. The project appears with a `production` branch and a primary compute endpoint, and
   moves to a running state in a few seconds.

Good when you want to *see* the object model on screen. When it's running, set the id:

```bash
export LB_PROJECT=factory
```

## Option 2 — the Databricks CLI

The CLI's `postgres` command group manages Autoscaling projects, branches, and endpoints
directly:

```bash
databricks postgres create-project \
  --profile "$LB_PROFILE" \
  --json '{"project_id": "factory", "spec": {"display_name": "factory", "pg_version": 17}}'
```

Then set the id:

```bash
export LB_PROJECT=factory
```

> **Tip**
> Explore the surface with `databricks postgres --help`. The same verbs the workshop scripts call
> (`create-project`, `create-branch`, `list-endpoints`, `generate-database-credential`) are all
> here, which is a nice way to see that the SDK and CLI are the same API.

## Option 3 — the workshop script

The script calls the SDK and polls until the project is ACTIVE, printing honest timings:

```bash
python ../common/scripts/provision.py --project factory --profile "$LB_PROFILE"
```

```text
create_project API returned in ~800 ms
project factory production endpoint ACTIVE in ~3.7s
  host: <something>.database.cloud.databricks.com

Now run:  export LB_PROJECT=factory
```

```bash
export LB_PROJECT=factory
```

> **From the field**
> The `create_project` API call returns in well under a second. The project reaches a queryable
> ACTIVE state in about 3 to 4 seconds in our measurements. That is the honest "provision in
> seconds" number: fast, real, and not instantaneous. Branch creation (next step) is faster
> still, because a branch adds no new storage.

## Verify (one way, whichever option you used)

No matter how you provisioned, confirm the project the same way. This is the single source of
truth that the project exists and its production endpoint is ACTIVE and queryable:

```bash
python ../common/scripts/provision.py --project "$LB_PROJECT" --profile "$LB_PROFILE" --status
```

```text
project factory production endpoint ACTIVE in ~0.0s
  host: <something>.database.cloud.databricks.com
```

An `ACTIVE` state with a host means the project is ready, regardless of whether you clicked, ran
the CLI, or ran the script. If instead you see `PROVISIONING`, `NO_ENDPOINT`, or a permission
error, the project isn't ready yet, wait a few seconds and re-run, or see the note below.

> **Note**
> Creating a project may require permission on the Lakebase instance. If provisioning fails with
> a permission error, use a project your instructor provisioned (set `LB_PROJECT` and verify
> above), or ask an admin for access.

---

Next: [`grants.md`](grants.md) — grant the access the workshop needs.
