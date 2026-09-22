# Capstone: manufacturing dashboard, FAQ

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

## Development (local) issues

### `npm install` fails: command not found

Node.js isn't installed. Install it from https://nodejs.org/ (version 18 or later).

### `pip install -r requirements.txt` fails on a Databricks-managed laptop

The public PyPI is blocked. Use the internal proxy:

```bash
pip install -r requirements.txt
```

### Backend starts but frontend is blank

Check the browser console (F12 → Console tab) for errors. Common issues:

- CORS error: backend isn't serving the frontend correctly. Restart both.
- 404 on /api/machines: backend API path is wrong. Check main.py endpoints.
- Network error: check that `localhost:8000` is reachable from localhost:3000.

### Frontend starts but can't connect to backend

The frontend is trying to reach the backend at the wrong URL. Check `frontend/.env`:

```
REACT_APP_API_URL=http://localhost:8000
```

Should point to your backend. If you moved the backend to a different port, update this.

### Backend can't connect to Lakebase: `env var LB_PROFILE not set`

Set environment variables before starting the backend:

```bash
export LB_PROFILE=<your-profile>
export LB_PROJECT=<project-id>
export LB_BRANCH=<branch-id>
export LB_SCHEMA=factory
```

Then start the backend again.

### Database query returns empty: no machines displayed

Possible causes:

1. The factory schema isn't loaded. Run `python ../../lakebase.py --sql "SELECT COUNT(*) FROM factory.machine"` to check.
2. Your branch has RLS that hides all rows. Try as a different user or check RLS policies.
3. The backend query is wrong. Check `backend/main.py` for the machines endpoint.

## Deployment issues

### Deploy script fails: `command not found: python` or `node`

The deploy script assumes Python and Node are in your PATH. Install them or use full paths:

```bash
/usr/local/bin/python3 deploy_to_databricks.py ...
```

### Deploy script fails: `app.yaml not found`

You're in the wrong directory. The deploy script must run from `common/capstone-app/`:

```bash
cd common/capstone-app
python ../scripts/deploy_to_databricks.py --app-name capstone-dashboard --skip-secrets
```

(Or use the provided `deploy.sh` which handles the path.)

### Deploy fails: `app.yaml validation error`

Check `app.yaml` syntax:

- Indentation must be 2 spaces (not tabs).
- `LAKEBASE_PROFILE`, `LAKEBASE_PROJECT`, `LAKEBASE_SCHEMA` must be in the `env` block.
- No hard-coded secrets; use environment variables or `--skip-secrets`.

### Deployment says "app is up to date, no changes"

The deployed code hasn't changed. If you made changes locally, ensure you committed or saved
them, and that the build picked them up:

```bash
npm run build  # rebuild frontend
python deploy_to_databricks.py ...  # redeploy
```

## Deployed app issues

### Deployed app shows a 500 error page

Check the app logs in the Databricks console:

1. Go to your workspace.
2. Click **Apps**.
3. Find `capstone-dashboard`.
4. Click the app name to see logs.

Common issues:

- Backend can't connect to Lakebase (check grants, environment variables).
- Frontend static files not bundled (check that `npm build` succeeded before deploying).
- Backend port mismatch (Databricks Apps provides a PORT env var; backend must use it).

### Deployed app works but queries are slow

Network latency is higher deployed than local. Expected latency is 50-200 ms. If queries are
taking longer:

- Check Lakebase instance health and load.
- Check network latency to your Lakebase instance.
- Optimize your SQL queries (add indexes, denormalize if needed).

### Can't access the deployed app from the workspace

Check:

- The app is deployed and running (visible in Apps list).
- You have workspace access (you should if you're running other Databricks features).
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

### Can the app's SP write to the factory schema?

By default, the grant script gives the SP SELECT (read-only) permissions. To grant write
permissions, you'd need to:

1. Run the grant script with a `--write-access` flag (if the script supports it), or
2. Manually grant INSERT/UPDATE/DELETE on tables:
   ```sql
   GRANT INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA factory TO "sp-client-id";
   ```

For the capstone, read-only is fine (the dashboard is read-heavy). Consider write access if you
add features that modify data (e.g., mark machine as maintenance, create maintenance logs).

## Architecture and design questions

### Why does the app query Lakebase directly instead of using the Data API?

The app uses both:

- **Direct SQL (backend):** for complex queries (BOM traversal, multi-table joins, aggregations)
  where SQL is cleaner and faster.
- **Data API (frontend or backend):** for simple REST queries where JSON is natural (fetch a
  single machine, list suppliers).

For the capstone, the backend uses direct SQL for all queries because they're complex. If you
wanted to, you could use the Data API for simple queries like "fetch all machines" and reserve
direct SQL for complex ones. Both are valid; it depends on your performance and architecture
preferences.

### Could I use a different framework (Django, Express, React Native)?

Yes. The capstone uses FastAPI and React because they're Python-friendly and Databricks-native.
Any Python web framework (Flask, Django) or Node framework (Express, Next.js) works on Databricks
Apps. The key point is that the backend must connect to Lakebase using the Databricks SDK +
psycopg (for SQL) or HTTP client (for Data API).

### How do I add a new endpoint to the backend?

Add a new route to `backend/main.py`:

```python
@app.get("/api/suppliers")
def get_suppliers():
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT supplier_id, name FROM factory.supplier")
            return cur.fetchall()
```

Then add a React component to call it in the frontend, rebuild, and redeploy.

## Troubleshooting checklist

If something isn't working, check:

- [ ] Service Principal exists and has grants (re-run grant script)
- [ ] Environment variables set correctly (`LB_PROFILE`, `LB_PROJECT`, `LB_BRANCH`, `LB_SCHEMA`)
- [ ] Branch endpoint is ACTIVE (check Lakebase console)
- [ ] Factory schema exists and has data (run `python ../../lakebase.py --check`)
- [ ] Backend started without errors (check terminal output)
- [ ] Frontend built successfully (`npm run build`)
- [ ] Deployed app logs don't show errors (check Databricks App logs)
- [ ] Browser developer console (F12) for JavaScript errors

If all those pass and something is still wrong, ask in the FAQ section specific to your error, or
contact your Databricks account team.
