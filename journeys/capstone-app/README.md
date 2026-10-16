# Capstone: build a bank dashboard app on Databricks Apps

> ## What you'll learn
>
> **Key takeaways**
>
> - A Databricks App is a web app (a FastAPI backend serving a single-page UI) deployed as a managed service on Databricks. You deploy it from a workspace notebook (or a laptop), and it runs with built-in auth and scaling.
> - To connect to Lakebase from an app, the app's [Service Principal](../../docs/glossary.md) (SP) needs two layers of access: `CAN_USE` on the Lakebase project (to find the branch and get credentials) and a Postgres role on the branch, created with `databricks_create_role()`, with read access to the `bank` schema. This is the deepest grant story in the workshop.
> - You'll run a real bank dashboard: account status, holdings look-through, case-note search. It uses direct SQL on Lakebase, including a recursive CTE and full-text search, showing an app reading operational data with no extra services.
>
> **You'll be able to:** set up a Databricks App's [Service Principal](../../docs/glossary.md) to connect to Lakebase, deploy a working FastAPI dashboard on Databricks Apps, and understand the app authentication model.
>
> **Time:** about 45 minutes (setup + run + deploy)  ·  **Status:** live

## The scenario

You've learned Lakebase through journeys. Now you want to ship a real app: a bank operations
dashboard where an analyst can check account status, look through a fund's holdings, and search
case notes. The app lives on Databricks Apps (the platform's managed hosting), so it scales with
your org and integrates with Databricks workspace auth.

The app's backend needs to query Lakebase. That means the app's [Service Principal](../../docs/glossary.md) (the identity
the app runs as) needs access to your Lakebase instance and project, and the PostgreSQL database.
This is the real-world version of the grant chain you learned in setup.

## What this journey includes

1. **Grant setup:** a Python script that grants your app's Service Principal access to the
   Lakebase project and database (reuses the pattern from 00-setup, but parameterized for your
   app).
2. **FastAPI backend:** a small service with endpoints for accounts, holdings look-through, and
   case notes. It uses direct SQL on Lakebase, a recursive CTE for the holdings tree and full-text
   search for the case notes.
3. **Single-page UI:** a static `index.html` the backend serves directly, with three tabs:
   Accounts, Holdings look-through, Case notes. No Node, no npm, no build step.
4. **Deploy script:** one command to deploy the whole thing to Databricks Apps.

You'll run the full journey locally first (so you understand each part), then deploy and see it
live in your workspace.

## The wow moment

You enter a fund id on the Holdings look-through tab, and the app returns the fund's instruments
*and* the ones held through a sleeve one level down, flattened by a recursive CTE, in one query
against the same database that serves the operational writes. Then you make a small change (add a
column, add an endpoint), run deploy, and in seconds your app is live in your workspace. No manual
server setup, no scaling configuration. That's the Databricks Apps magic.

## What you'll do

**In Databricks (the workshop path):** open
[`capstone_app_databricks`](capstone_app_databricks.py) and run it top to bottom. It:

1. Names your app after your branch and finds its source, the `app/` folder.
2. Creates the app, which also creates its service principal.
3. Grants the service principal `CAN_USE` on the project and a Postgres role on your branch.
4. Deploys the app, passing your project and branch as environment variables.
5. Prints the links to open the dashboard and its API in your browser.

No laptop, CLI or local Python is needed.

**From a laptop (optional):** the same steps with `capstone_grant_sp.py`, `run_local.sh` and
`app/deploy.sh`. Copy-paste steps are in [`instructions.md`](instructions.md); expected output is in
[`expected.md`](expected.md).

## Prerequisites

Finish [`../../00-setup/`](../../00-setup/) so you have a branch, can connect, and understand
the grant chain. You should also complete the main Lakebase journeys (at least
[Branch the brain](../branch-the-brain/) and [Build a knowledge graph](../kg-build/)) so you're
comfortable with the domain and Lakebase concepts.

For this journey you'll need:

- Permission to create Databricks Apps in the workspace (ask your workspace admin if you're unsure)
- `CAN_MANAGE` on the Lakebase project, so you can grant the app `CAN_USE`
- For the laptop path only: `uv` or `pip` for the backend's Python dependencies
- Optional: basic familiarity with FastAPI, if you want to change an endpoint

There is no Node/React toolchain to install: the UI is a single static HTML file the backend
serves.

## Wrapping up

This capstone brings it all together: Lakebase (data), Databricks Apps (platform), and SQL (client
code). You've completed the workshop and run a production-grade app. From here, the next step is to
take your own data, your own banking scenario, and apply these same patterns: schema design,
branching, querying, and app deployment.

The patterns you've learned scale from a single account to a book of business across the world,
from a sandbox branch to multi-environment deployments. Lakebase and Databricks Apps handle the
infrastructure; you focus on the business logic.
