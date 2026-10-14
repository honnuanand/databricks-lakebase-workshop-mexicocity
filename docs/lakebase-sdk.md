# The Lakebase part of the Databricks SDK

A short reference for the SDK calls this workshop uses. Read it once; the setup steps and
journeys link back here instead of re-explaining. It covers the object model, the handful of
calls you'll actually make, how authentication works, and two gotchas that will save you time.

> **Note**
> This is a workshop-maintained summary, written against `databricks-sdk==0.120.0`. For the
> current, authoritative reference always go to the source:
>
> - **Lakebase Postgres (docs home):** <https://docs.databricks.com/aws/en/oltp/projects>
> - **Get started (create your first project):** <https://docs.databricks.com/aws/en/oltp/projects/get-started>
> - **Manage projects:** <https://docs.databricks.com/aws/en/oltp/projects/manage-projects>
> - **Manage computes (endpoints):** <https://docs.databricks.com/aws/en/oltp/projects/manage-computes>
> - **Create Postgres roles (used in grants):** <https://docs.databricks.com/aws/en/oltp/projects/postgres-roles>
> - **Lakebase API guide (REST, mirrors the SDK):** <https://docs.databricks.com/aws/en/oltp/projects/api-usage>
> - **Databricks Python SDK source:** <https://github.com/databricks/databricks-sdk-py>
>
> (Azure users: swap `/aws/` for `/azure/` in the paths above.) If a call here behaves
> differently than described, trust the docs above and tell us so we can update this page.

## The object model

Everything in Lakebase Autoscaling nests like this:

```text
Project  ⊃  Branch  ⊃  Endpoint  ⊃  Database  ⊃  Schema  ⊃  Tables
```

- **Project**, the provisioning container. Create one and it comes with a `production` branch
  and a primary endpoint.
- **Branch**, a zero-copy, copy-on-write copy of the data. `production` is the default; your
  workshop branch is `u-<name>`. Creating a branch copies no data; it diverges only as you write.
- **Endpoint**, the connectable compute for a branch, reachable on `host:5432` over the
  standard Postgres wire.
- **Database / Schema / Tables**, a normal Postgres database (`databricks_postgres` by default)
  with your schema and tables inside it.

In the SDK, resources are addressed by a path name built from those parts:

```python
f"projects/{project_id}"                                  # a project
f"projects/{project_id}/branches/{branch}"                # a branch
f"projects/{project_id}/branches/{branch}/endpoints/primary"  # an endpoint
```

## The one gotcha that trips everyone: two Postgres surfaces

The SDK has **two different Postgres-related surfaces, and they are not interchangeable:**

| Surface | What it manages | This workshop |
| ------- | --------------- | ------------- |
| `w.postgres.*` | **Autoscaling**: projects, branches, endpoints (the model above) | **This is the one we use.** |
| `w.database.*` | Managed database instances (a different object model) | Not used here. |

If you find yourself calling `w.database.create_database_instance`, you're on the wrong surface
for this workshop. Everything below is `w.postgres`.

## The calls you'll actually make

All of these hang off a `WorkspaceClient`:

```python
from databricks.sdk import WorkspaceClient
from databricks.sdk.service.postgres import Project, ProjectSpec, Branch, BranchSpec

w = WorkspaceClient(profile="your-profile")   # see Authentication below
```

**Create a project** (returns fast; the endpoint reaches `ACTIVE` within about a minute):

```python
w.postgres.create_project(
    project=Project(spec=ProjectSpec(display_name="bank", pg_version=17)),
    project_id="bank",
)
```

**Create a zero-copy branch** off another branch (the hero move; branch endpoint reaches
`ACTIVE` in about two seconds):

```python
w.postgres.create_branch(
    parent="projects/bank",
    branch=Branch(spec=BranchSpec(
        source_branch="projects/bank/branches/production",
        no_expiry=True,
    )),
    branch_id="u-alex",
    replace_existing=False,   # True to overwrite an existing branch of that name
)
```

**List a branch's endpoints** (to find the host and check readiness):

```python
eps = list(w.postgres.list_endpoints(parent="projects/bank/branches/u-alex"))
ep = eps[0]
host = ep.status.hosts.host                 # the host:5432 you connect to
state = ep.status.current_state.value       # "ACTIVE" when ready  ← see gotcha below
```

**Generate a short-lived credential** to connect (an OAuth token, valid about an hour):

```python
cred = w.postgres.generate_database_credential(
    endpoint="projects/bank/branches/u-alex/endpoints/primary")
token = cred.token
```

**Other calls used in the workshop:** `get_project`, `list_projects`, `delete_project`,
`get_branch`, `list_branches`, `delete_branch`, `update_branch` (to unprotect before delete),
`create_role` (registers a Postgres role on a branch, used in grants).

## Gotcha: readiness is `status.current_state`, not `status.state`

To check whether an endpoint is live, read `endpoint.status.current_state` and compare to
`"ACTIVE"`. There is no `status.state` attribute; reading it returns nothing and your polling
loop silently never becomes ready. Always:

```python
ready = (ep.status.current_state.value == "ACTIVE") and bool(ep.status.hosts)
```

## Connecting with the token

The credential token is used as the **Postgres password**, with your Databricks username as the
user. Any Postgres driver works; this workshop uses `psycopg`:

```python
import psycopg

conn = psycopg.connect(
    host=host, port=5432, dbname="databricks_postgres",
    user=w.current_user.me().user_name,   # your Databricks identity
    password=token,                       # the OAuth token from generate_database_credential
    sslmode="require", autocommit=True,
)
with conn.cursor() as cur:
    cur.execute("SELECT 1;")
    print(cur.fetchone())   # (1,)
```

> **Tip**
> Tokens last about an hour. The workshop's shared helper in
> [`../common/scripts/`](../common/scripts/) caches and refreshes them for you, so you rarely
> call `generate_database_credential` directly.

## Authentication

The SDK uses the Databricks credential chain. Locally you pass a **profile** (a named login in
your `~/.databrickscfg`), which you create in [`../00-setup/auth.md`](../00-setup/auth.md):

```python
w = WorkspaceClient(profile="your-profile")   # the profile name you set up in auth.md
```

On Databricks Apps the runtime injects the credentials, so you construct `WorkspaceClient()`
with no profile. Either way, the OAuth login expires (roughly hourly). If a call fails with a
"refresh token" or authentication error, re-run `databricks auth login` from
[`../00-setup/auth.md`](../00-setup/auth.md).

---

*Grounded in the pitch app's `backend/lakebase_service.py`, which drives these same calls live.
For anything not covered here, the authoritative sources are linked at the top.*
