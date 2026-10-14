# Capstone: run a bank dashboard on Lakebase, instructions

## How to run this journey

You do not write any application code here. The dashboard app is provided, complete, in the
[`app/`](app/) folder. Your job is to point it at your Lakebase branch, run it, and deploy it,
so you see an application read the bank you built. The Lakebase wiring is the lesson, not the
web framework.

If you haven't done [`../../00-setup/`](../../00-setup/), do that first; you need `LB_PROFILE`,
`LB_PROJECT`, `LB_BRANCH`, and `LB_SCHEMA` set.

## What the app is

A small dashboard with three views, each backed by a query you already met in earlier journeys:

- **Accounts**, a direct `SELECT` on the `account` table.
- **Holdings look-through**, the recursive-CTE holdings explosion from [SQL you already know](../pg-sql-parity/).
- **Case notes**, full-text search over `case_note`, from [Search, three ways](../pg-search/).

It is a FastAPI backend ([`app/backend/main.py`](app/backend/main.py)) that serves a single-page
UI ([`app/backend/static/index.html`](app/backend/static/index.html)). No Node, no build step. The
only interesting part is how it connects to Lakebase, and that is the same helper pattern every
journey uses: locally it authenticates with your profile; on Databricks Apps it authenticates as
the app's Service Principal. The same code, two identities.

## Step 1, run it locally against your branch

From this journey folder:

```bash
bash app/run_local.sh
```

That installs the backend's dependencies (first run only), then starts the app on
`http://localhost:8000`, serving your branch. Open that URL. You should see the Accounts list,
switch tabs to look through `FUND-GROWTH-A`'s holdings tree, and search the case notes.

The header shows which branch and identity it is serving, proof it is reading your live Lakebase
branch, not a mock. Stop it with Ctrl-C when you are done.

> **Tip**
> If the page loads but a tab shows an error, check that your branch endpoint is serving:
> `python ../../common/scripts/lakebase.py --check`. The app reads `LB_PROJECT` / `LB_BRANCH` /
> `LB_SCHEMA` from your environment via `run_local.sh`.

## Step 2, grant the app's Service Principal (before deploying)

When you deploy, the app runs as a Service Principal, not as you. That Service Principal needs its
own permission to reach Lakebase. Grant it:

```bash
python capstone_grant_sp.py --app-name capstone-dashboard \
  --lakebase-profile "$LB_PROFILE" \
  --lakebase-project "$LB_PROJECT" \
  --lakebase-schema bank
```

This looks up the app's Service Principal, creates a PostgreSQL role for it, stamps the
`databricks_auth` security label (the part that makes Lakebase authenticate it as that Service
Principal), grants project access, and adds a role on the production branch. It is the same
grant chain you would run for any app on Lakebase, parameterized. It is idempotent, so re-running
is safe.

> **Note**
> On a brand-new app the Service Principal does not exist until the first deploy. If the script
> says the app is not found, deploy first (Step 3), then run this grant, then redeploy. The
> troubleshooting section covers the "permission denied" case that means this step is needed.

## Step 3, point the app at your setup

Open [`app/app.yaml`](app/app.yaml) and set the `LAKEBASE_*` values to match your project and the
branch you want the deployed app to serve (usually `production` or a shared read-friendly branch,
not your personal `u-<name>`). There is no profile here on purpose: the deployed app uses its
Service Principal, not your login.

## Step 4, deploy to Databricks Apps

```bash
bash app/deploy.sh capstone-dashboard
```

This packages the provided app and pushes it to Databricks Apps. Deployment takes a minute or
two. When it finishes, open **Apps** in your workspace and click `capstone-dashboard`.

## Step 5, see it live, then change one value and redeploy

The deployed dashboard looks the same as your local run, but now the backend runs on Databricks
Apps and queries Lakebase as its Service Principal. Confirm each tab works.

Then make a small change you do not need code for: edit `LAKEBASE_BRANCH` in `app/app.yaml` to a
different branch, and redeploy with `bash app/deploy.sh`. The app now serves that branch. You just
repointed a live application at a different copy of the database by changing one line, which is the
branching story from the very first journey, seen from the application's side.

## What you did

You ran a real application against your Lakebase branch, granted an application identity access to
the database, and deployed it, without writing application code. The database you built across the
workshop is now backing an app, governed by Unity Catalog, reachable by its Service Principal. That
is Lakebase as the operational store and the app backend at once. The holdings look-through tab is
worth a second look: a recursive CTE walked the fund-of-funds tree and flattened it in one query,
the kind of operational question an app can answer directly on Lakebase.

For errors and the OBO-versus-Service-Principal auth detail, see [`faq.md`](faq.md).
