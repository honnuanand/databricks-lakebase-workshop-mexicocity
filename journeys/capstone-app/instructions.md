# Capstone: build a manufacturing dashboard, instructions

This journey has several parts. Start at the beginning and work through each step.

If you haven't done [`../../00-setup/`](../../00-setup/), do that first; you need `LB_PROFILE`,
`LB_PROJECT`, `LB_BRANCH`, and `LB_SCHEMA` set.

## Overview

The capstone app lives in [`../../common/capstone-app/`](../../common/capstone-app/) and consists
of:

- `frontend/`, React dashboard (machine list, BOM search, maintenance logs)
- `backend/`, FastAPI service (queries Lakebase directly and via Data API)
- `app.yaml`, Databricks Apps configuration
- `deploy.sh`, one-command deploy script

## Step 1, set up the app's Service Principal permissions

Your app (once deployed) runs as a Service Principal on Databricks Apps. That SP needs to connect
to Lakebase. Run the grant script:

```bash
cd journeys/capstone-app
python capstone_grant_sp.py --app-name capstone-dashboard \
  --lakebase-profile <LB_PROFILE> \
  --lakebase-project <LB_PROJECT> \
  --lakebase-schema factory
```

Replace `<LB_PROFILE>`, `<LB_PROJECT>` with your values from 00-setup. This script:

1. Looks up the app's Service Principal (by app name).
2. Creates a PostgreSQL role for the SP.
3. Sets the databricks_auth security label (the key part: it tells Lakebase to auth as the SP).
4. Grants the SP project CAN_MANAGE permission (so it can list branches).
5. Creates a role on the production branch.

This is the same pattern as the pitch app's `grant_app_sp.py`, but parameterized.

If the app doesn't exist yet (first time), the script prints a note: the app will be created
automatically when you deploy. Re-run this script after deploying, with the app's new SP ID.

## Step 2, develop and test locally

Navigate to the app:

```bash
cd journeys/capstone-app
```

Install dependencies:

```bash
cd backend && pip install -r requirements.txt
cd ../frontend && npm install
```

Set environment variables for the backend:

```bash
export LB_PROFILE=<your-profile>
export LB_PROJECT=<project-id>
export LB_BRANCH=<branch-id>
export LB_SCHEMA=factory
```

Start the backend (from `backend/`):

```bash
python -m uvicorn main:app --reload --port 8000
```

In another terminal, start the frontend (from `frontend/`):

```bash
npm start
```

Open http://localhost:3000 in your browser. You should see the dashboard with:

- **Machines tab:** a list of all machines, fetched via direct SQL
- **BOM tab:** search for products and see their part trees
- **Maintenance tab:** view maintenance logs with full-text search

Test each feature locally before deploying.

## Step 3, verify the app connects to Lakebase

In the browser, click a machine to see its details. The backend makes a SQL query to Lakebase and
returns the data. If the query fails, check:

- Are your environment variables set correctly?
- Does your branch endpoint respond? Run `python ../../lakebase.py --check`
- Did the grant script succeed?

## Step 4, prepare for deployment

Update `app.yaml` with your app settings:

```yaml
name: capstone-dashboard
host: <workspace-host>  # e.g., my-workspace.cloud.databricks.com
```

Check that the `LAKEBASE_*` environment variables in `app.yaml` match your setup:

```yaml
env:
  LAKEBASE_PROFILE: <your-profile>
  LAKEBASE_PROJECT: <project-id>
  LAKEBASE_SCHEMA: factory
```

## Step 5, deploy to Databricks Apps

From the `capstone-app/` directory:

```bash
bash deploy.sh
```

Or manually:

```bash
cd backend && python deploy_to_databricks.py --app-name capstone-dashboard --skip-secrets
```

(Use `deploy_to_databricks.py` from the backend; it's the authoritative deploy script per
`CLAUDE.md`.)

The deploy script:

1. Builds the React frontend (npm run build).
2. Packages the FastAPI backend with the built frontend as static files.
3. Pushes to Databricks Apps.

Deployment takes 1-2 minutes. Watch the output for errors.

## Step 6, re-grant the app's SP (if needed)

If this is the first deploy, the app was just created and has a new Service Principal ID. Re-run
the grant script to update the grants:

```bash
python capstone_grant_sp.py --app-name capstone-dashboard \
  --lakebase-profile <LB_PROFILE> \
  --lakebase-project <LB_PROJECT> \
  --lakebase-schema factory
```

The script is idempotent; re-running is safe.

## Step 7, test the deployed app

Log into your Databricks workspace. Go to **Apps** and find `capstone-dashboard`. Click it to
open.

You should see the same dashboard as your local version. The backend is now running on Databricks
Apps, querying Lakebase directly.

Test each tab:

- Machines: fetch a list.
- BOM: search for a product and view its part tree.
- Maintenance: search for maintenance logs.

## Step 8, make a change and redeploy

Change something small in the React frontend or backend (e.g., add a new column, change a color).
Re-run the deploy script:

```bash
bash deploy.sh
```

The app updates live. Refresh the browser and see your change.

## Troubleshooting

### App won't start: `LB_PROFILE not set`

The backend environment variables aren't being passed to the app. Check `app.yaml` and ensure
the env block has `LAKEBASE_PROFILE`, `LAKEBASE_PROJECT`, and `LAKEBASE_SCHEMA`.

### Database connection fails: `permission denied`

The app's SP doesn't have the right grants. Re-run:

```bash
python capstone_grant_sp.py --app-name capstone-dashboard ...
```

Then redeploy:

```bash
bash deploy.sh
```

### Frontend renders but queries return empty

The backend is running but not connecting to Lakebase. Check:

- Are environment variables set in `app.yaml`?
- Does the app's SP have the right grants?
- Is your branch endpoint active? Check in the console.

For more troubleshooting, see [`faq.md`](faq.md).
