# Capstone: bank dashboard, expected results

Use this to check your work. The exact data in the dashboard depends on your bank schema and which
journeys you have run, but the UI structure and capabilities should match.

## Step 1, grant setup

Running the grant script should output something like:

```text
Granting Lakebase access to app Service Principal...
  App: capstone-dashboard
  SP Client ID: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
  Project: <your-project>
  Schema: bank

  Created PostgreSQL role: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
  Set security label: databricks_auth
  Granted project CAN_MANAGE permission
  Created role on production branch
  Granted USAGE on schema bank
  Granted SELECT on all tables in bank

Done. App SP has access to Lakebase.
```

## Step 1 (local), the app serves on http://localhost:8000

The backend serves both the UI and the `/api/*` endpoints from one process. The header shows which
branch and identity it is serving, proof it is reading your live Lakebase branch, not a mock.

### Accounts tab

A direct `SELECT` on `account`:

```text
Account       | Branch  | Line     | Type   | Status         | Health
--------------|---------|----------|--------|----------------|-------
CTA-100234   | BR-CDMX  | Checking | retail | good_standing  | 98.5%
CTA-100235   | BR-CDMX  | Savings  | retail | good_standing  | 96.2%
CTA-100240   | BR-CDMX  | Credit   | retail | watch          | 91.0%
...
```

The matching API call, if you want to see the raw JSON: `curl http://localhost:8000/api/accounts`.

### Holdings look-through tab

Enter `FUND-GROWTH-A` and press Look through. A recursive CTE walks the holdings tree:

```text
Depth | Instrument    | Name            | Qty
------|---------------|-----------------|----
1     | INS-CASH-MXN  | Mexican Peso Cash  | 1
1     | INS-ZAFR      | Zafiro Software  | 8
1     | INS-SLEEVE-EQ | Equity Sleeve   | 2
2     | INS-QTZL      | Quetzal Tecnologia       | 1
2     | INS-MBONO-10Y   | Bono M 10Y (Mexico) | 2
```

The depth-2 rows (INS-QTZL, INS-MBONO-10Y) are held *through* the equity sleeve, not directly by the
fund. One query flattened the whole tree. (`curl http://localhost:8000/api/holdings/FUND-GROWTH-A`.)

### Case notes tab

Search `wire`:

```text
Note | Account      | Write-up
-----|--------------|-------------------------------------------------------------
31   | CTA-300421  | Large outbound wire to a brand-new beneficiary in a high-risk
     |              | jurisdiction, just under the reporting threshold...
```

Full-text search over `case_note`. With an empty query it shows the most recent notes.
(`curl "http://localhost:8000/api/casenotes?q=wire"`.)

## Step 2, verify connection

`curl http://localhost:8000/api/health` returns the identity, project, branch, and schema it is
serving:

```json
{"ok": true, "identity": "you@example.com", "project": "<your-project>", "branch": "u-<name>", "schema": "bank"}
```

If a tab shows an error, check that your branch endpoint is ACTIVE and the env vars are set.

## Step 4, deploy output

Running the deploy script should output something like:

```text
Deploying to Databricks Apps...
  (deploy output)
  Deployment succeeded.
  App URL: https://capstone-dashboard-<workspace-id>.aws.databricksapps.com
```

There is no frontend build step; the static UI ships with the backend. Note the App URL to access
the deployed app.

## Step 5, deployed app

Open the deployed URL (Databricks workspace → Apps → capstone-dashboard). You should see
the same dashboard as your local version. Verify:

- Accounts tab loads and shows data.
- Holdings look-through works and shows depth-2 rows for a fund with a sleeve.
- Case-note search works.

Response times may be slightly higher than local (50-200 ms instead of <50 ms) due to network
latency between Databricks Apps and Lakebase, but should still feel instant.

## Full deployment checklist

After completing all steps, you should have:

- [ ] Service Principal granted Lakebase access
- [ ] App running locally and connecting to Lakebase
- [ ] App deployed to Databricks Apps
- [ ] Deployed app visible in workspace → Apps
- [ ] Accounts tab shows account data
- [ ] Holdings look-through tab shows the recursive tree
- [ ] Case notes tab searches and displays notes
- [ ] Successful edit and redeploy cycle

## The numbers that matter

| What | Expected | Why it matters |
| ------ | -------- | -------------- |
| Local server startup | 5-10 seconds | backend initialization + first branch connect |
| Deployment time | 1-2 minutes | push to Databricks Apps (no frontend build) |
| Query latency (local) | <50 ms | fast local iteration |
| Query latency (deployed) | 50-200 ms | network + Lakebase |
| App startup time | <3 seconds | page loads quickly in workspace |

## Debugging help

If something isn't working:

- **Backend won't start:** check `pip install -r requirements.txt` succeeded, and Python 3.9+ is installed.
- **App won't connect to Lakebase:** re-run the grant script, check environment variables in `app.yaml`.
- **Deployed app shows 500 error:** check the Databricks App logs in the workspace console.

For more detailed troubleshooting, see [`faq.md`](faq.md).
