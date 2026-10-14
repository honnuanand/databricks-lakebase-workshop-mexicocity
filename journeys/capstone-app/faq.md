# Capstone: bank dashboard, FAQ

The app is a FastAPI backend that serves a single static `index.html`. There is no Node, no npm,
and no separate frontend build; keep that in mind as you read the troubleshooting below.

## Setup and permissions questions

### The grant script says "App not found"

The app doesn't exist yet, which is normal on first run. The app is created when you deploy for
the first time. Re-run the grant script after deployment:

```bash
python capstone_grant_sp.py --app-name capstone-dashboard ...
```

The script will then find the app's SP and complete the grants.

### Grant script fails with "permission denied on project"

Your user doesn't have CAN_MANAGE permission on the Lakebase project. Check:

- Are you the project owner, or do you have a role that grants CAN_MANAGE?
- Is `LB_PROJECT` correct?
- Try running as the workspace admin if you have access.

### Can't find the Service Principal ID to grant

Run:

```bash
databricks service-principals list --profile <LB_PROFILE> --output json | grep capstone
```

This lists service principals matching "capstone". Find the one for your app and note its ID.

## Running the app locally

### `pip install -r requirements.txt` fails on a Databricks-managed laptop

The public PyPI is blocked. Use the internal proxy (see your workshop setup notes), then retry.

### The page loads but a tab shows an error

Check the browser console (F12 → Console tab) and the terminal where the app is running. Common
causes:

- The branch endpoint is not ACTIVE. Confirm with `python ../../common/scripts/lakebase.py --check`.
- A 404 on `/api/accounts` means the backend route is wrong; check `app/backend/main.py`.
- An env var is missing; the app reads `LB_*` via `run_local.sh`.

### Backend can't connect to Lakebase: `LAKEBASE_PROJECT is not set`

`run_local.sh` maps `LB_*` to `LAKEBASE_*`. Set the workshop vars before starting:

```bash
export LB_PROFILE=<your-profile>
export LB_PROJECT=<project-id>
export LB_BRANCH=<branch-id>
export LB_SCHEMA=bank
```

Then run `bash app/run_local.sh` again.

### Query returns empty: no accounts displayed

Possible causes:

1. The bank schema isn't loaded. Run `python ../../common/scripts/lakebase.py --sql "SELECT COUNT(*) FROM bank.account"` to check.
2. Your branch has RLS that hides all rows (see the pg-rls journey). Try as a different role or check the policies.
3. The backend query is wrong. Check `app/backend/main.py` for the accounts endpoint.

## Deployment issues

### Deploy script fails: `command not found: python`

The deploy script assumes Python is in your PATH. Install it or use a full path.

### Deploy script fails: `app.yaml not found`

You're in the wrong directory. Run the deploy from the app folder (the one holding `app.yaml`):

```bash
cd journeys/capstone-app/app
bash deploy.sh capstone-dashboard
```

### Deploy fails: `app.yaml validation error`

Check `app.yaml` syntax:

- Indentation must be 2 spaces (not tabs).
- `LAKEBASE_PROJECT`, `LAKEBASE_BRANCH`, `LAKEBASE_SCHEMA` must be in the `env` block.
- There is NO `LAKEBASE_PROFILE` on Databricks Apps; the runtime injects the SP credentials.

## Deployed app issues

### Deployed app shows a 500 error page

Check the app logs in the Databricks console:

1. Go to your workspace.
2. Click **Apps**.
3. Find `capstone-dashboard`.
4. Click the app name to see logs.

Common issues:

- Backend can't connect to Lakebase (check grants, environment variables in `app.yaml`).
- Backend port mismatch (Databricks Apps provides a PORT env var; the backend already reads it).

### Deployed app works but queries are slow

Network latency is higher deployed than local. Expected latency is 50-200 ms. If queries are
taking longer:

- Check Lakebase instance health and load.
- Optimize your SQL queries (add indexes; see the pg-index and pg-explain journeys).

### Can't access the deployed app from the workspace

Check:

- The app is deployed and running (visible in Apps list).
- You have workspace access.
- The app's URL is correct (Databricks provides it in the Apps list).

If the app icon is grayed out, it may still be starting. Wait a few seconds and refresh.

## Grant and security questions

### Do I need to run the grant script every time?

No, only once after the app is deployed. The grants are persistent. If you redeploy the app
(without deleting it), the grants stay in effect.

If you create a new app or change the app name, run the script again.

### What's the `databricks_auth` security label?

It tells PostgreSQL (Lakebase) that this SP should be authenticated via Databricks OAuth, not a
traditional password. Without it, the SP can't connect even if other permissions are correct.

See [`../../00-setup/grants.md`](../../00-setup/grants.md) for full details.

### Can the app's SP write to the bank schema?

By default, the grant script gives the [Service Principal](../../docs/glossary.md) (SP) SELECT (read-only) permissions. To grant write
permissions, you'd need to:

1. Run the grant script with a `--write-access` flag (if the script supports it), or
2. Manually grant INSERT/UPDATE/DELETE on tables:
   ```sql
   GRANT INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA bank TO "sp-client-id";
   ```

For the capstone, read-only is fine (the dashboard is read-heavy). Consider write access if you
add features that modify data (e.g., mark an account for review, create case notes).

## Architecture and design questions

### Why does the app query Lakebase directly with SQL?

Because the queries are naturally SQL: a direct `SELECT` for the accounts list, a recursive CTE for
the holdings look-through, and `to_tsvector`/`plainto_tsquery` full-text search for the case notes.
Running them as plain SQL on Lakebase means no extra services and no second datastore. For simple
REST-shaped reads you could instead use the Lakebase Data API (see the data-api journey); both are
valid, it depends on your architecture preferences.

### Could I use a different framework (Flask, Django, Express)?

Yes. The capstone uses FastAPI because it's small and Python-friendly. Any Python web framework
(Flask, Django) or Node framework (Express, Next.js) works on Databricks Apps. The key point is
that the backend connects to Lakebase using the Databricks SDK + psycopg.

### How do I add a new endpoint to the backend?

Add a new route to `app/backend/main.py`:

```python
@app.get("/api/counterparties")
def counterparties():
    return query("SELECT counterparty_id, name FROM counterparty ORDER BY counterparty_id")
```

Then add a tab (or a `fetch`) to `app/backend/static/index.html` to display it, and redeploy.

## Troubleshooting checklist

If something isn't working, check:

- [ ] Service Principal exists and has grants (re-run grant script)
- [ ] Environment variables set correctly (`LB_PROFILE`, `LB_PROJECT`, `LB_BRANCH`, `LB_SCHEMA`)
- [ ] Branch endpoint is ACTIVE (check Lakebase console or `lakebase.py --check`)
- [ ] Bank schema exists and has data (`python ../../common/scripts/lakebase.py --sql "SELECT COUNT(*) FROM bank.account"`)
- [ ] Backend started without errors (check terminal output)
- [ ] Deployed app logs don't show errors (check Databricks App logs)
- [ ] Browser developer console (F12) for JavaScript errors

If all those pass and something is still wrong, ask in the FAQ section specific to your error, or
contact your Databricks account team.
