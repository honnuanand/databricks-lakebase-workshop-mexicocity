# Capstone: manufacturing dashboard, expected results

Use this to check your work. The exact data in the dashboard depends on your factory schema, but
the UI structure and capabilities should match.

## Step 1, grant setup

Running the grant script should output:

```text
Granting Lakebase access to app Service Principal...
  App: capstone-dashboard
  SP Client ID: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
  Project: <your-project>
  Schema: factory

  Created PostgreSQL role: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
  Set security label: databricks_auth
  Granted project CAN_MANAGE permission
  Created role on production branch
  Granted USAGE on schema factory
  Granted SELECT on all tables in factory

Done. App SP has access to Lakebase.
```

## Step 2, local development (http://localhost:3000)

The app should display three tabs:

### Machines Tab

You should see a table:

```text
Machine ID | Line        | Type   | Status    | Health
-----------|-------------|--------|-----------|----------
ACCT-100240      | Stamping-A  | press  | healthy   | 91.0%
ACCT-100241      | Stamping-A  | press  | derated   | 70.0%
ACCT-200311      | Assembly-B  | robot  | down      | 45.0%
...
```

Click a machine row to see details (plant, type, recent sensor readings, maintenance history).

### BOM Tab

Search for a product:

```text
Search: FUND-GROWTH-A
Results:
  Product: FUND-GROWTH-A
  Parts contained:
    PT-BEARING-6204 (qty 1)
    PT-GEAR-420 (qty 2)
    PT-SHAFT-110 (qty 1)
    PT-HOUSING-08 (qty 1)
```

### Maintenance Tab

Search case notes:

```text
Search: bearing
Results (5 matching logs):
  Date: 2025-09-22 14:30
  Machine: ACCT-100240
  Defect: bearing noise detected
  Action: inspected bearing, no damage
  Confidence: 0.85

  ... (more logs)
```

## Step 3, verify connection

Click on a machine and see its detailed view load. If the backend is connected to Lakebase, you'll
see:

- Current sensor readings (temp, vibration, RPM)
- Status (healthy / derated / down)
- Maintenance history (past month)

If you see errors, check the browser console (F12) for error messages.

## Step 5, deploy output

Running the deploy script should output:

```text
Building frontend...
  (npm build output)
  Build complete.

Deploying to Databricks Apps...
  (deploy_to_databricks.py output)
  Deployment succeeded.
  App URL: https://capstone-dashboard-<workspace-id>.aws.databricksapps.com
```

Note the App URL. Use it to access the deployed app.

## Step 7, deployed app

Open the deployed URL (from Databricks workspace → Apps → capstone-dashboard). You should see
the same dashboard as your local version. Verify:

- Machines tab loads and shows data.
- BOM search works.
- Maintenance log search works.

Response times may be slightly higher than local (50-200 ms instead of <50 ms) due to network
latency between Databricks Apps and Lakebase, but should still feel instant.

## Step 8, after making a change

If you change a React component (e.g., add a new column to the account table) and redeploy:

```text
Building frontend...
Build complete.

Deploying to Databricks Apps...
Deployment succeeded.
```

Refresh the deployed app in your browser (or wait for automatic reload) and verify your change
appears.

## Full deployment checklist

After completing all steps, you should have:

- [ ] Service Principal granted Lakebase access
- [ ] App running locally and connecting to Lakebase
- [ ] App deployed to Databricks Apps
- [ ] Deployed app visible in workspace → Apps
- [ ] Machines tab shows account data
- [ ] BOM tab searches and displays part trees
- [ ] Maintenance tab searches and displays logs
- [ ] Successful edit and redeploy cycle

## The numbers that matter

| What | Expected | Why it matters |
| ------ | -------- | -------------- |
| Local dev server startup | 5-10 seconds | React + backend initialization |
| Deployment time | 1-2 minutes | build + push to Databricks Apps |
| Query latency (local) | <50 ms | fast local iteration |
| Query latency (deployed) | 50-200 ms | network + Lakebase |
| App startup time | <3 seconds | page loads quickly in workspace |

## Debugging help

If something isn't working:

- **Backend won't start:** check `pip install -r requirements.txt` succeeded, and Python 3.9+ is installed.
- **Frontend won't build:** check `npm install` succeeded, and Node 18+ is installed.
- **App won't connect to Lakebase:** re-run grant script, check environment variables in `app.yaml`.
- **Deployed app shows 500 error:** check the Databricks App logs in the workspace console.

For more detailed troubleshooting, see [`faq.md`](faq.md).
