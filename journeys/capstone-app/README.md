# Capstone: build a bank dashboard app on Databricks Apps

> ## What you'll learn
>
> **Key takeaways**
>
> - A Databricks App is a web app (a FastAPI backend serving a single-page UI) deployed as a managed service on Databricks. You write code locally, push to Databricks, and it runs with built-in auth and scaling.
> - To connect to Lakebase from an app, the app's [Service Principal](../../docs/glossary.md) (SP) needs the full grant chain: a PostgreSQL role + databricks_auth security label + project CAN_MANAGE permission + a role on the production branch. This is the deepest grant story in the workshop.
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

1. Set up: understand the app structure (FastAPI backend + static index.html + app.yaml config).
2. Grant access: run a script that gives the app's SP the full Lakebase grant chain.
3. Run locally: start the app with `run_local.sh`, make sure it connects to Lakebase.
4. Deploy: push the app to Databricks Apps with `deploy.sh`.
5. Test live: open the deployed app in your workspace and verify it works.

Full copy-paste steps are in [`instructions.md`](instructions.md); expected output is in
[`expected.md`](expected.md).

## Prerequisites

Finish [`../../00-setup/`](../../00-setup/) so you have a branch, can connect, and understand
the grant chain. You should also complete the main Lakebase journeys (at least
[Branch the brain](../branch-the-brain/) and [Build a knowledge graph](../kg-build/)) so you're
comfortable with the domain and Lakebase concepts.

For this journey you'll need:

- `uv` or `pip` for Python dependency management (the backend's only dependencies)
- Basic familiarity with FastAPI (you can read and modify an endpoint, but don't need to write a
  service from scratch)
- Workspace access to deploy Databricks Apps (ask your workspace admin if you're unsure)

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
