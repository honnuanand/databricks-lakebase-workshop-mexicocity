# Capstone: build a manufacturing dashboard app on Databricks Apps

> ## What you'll learn
>
> **Key takeaways**
>
> - A Databricks App is a full-stack web app (React frontend + FastAPI backend) deployed as a managed service on Databricks. You write code locally, push to Databricks, and it runs with built-in auth and scaling.
> - To connect to Lakebase from an app, the app's [Service Principal](../../docs/glossary.md) (SP) needs the full grant chain: a PostgreSQL role + databricks_auth security label + project CAN_MANAGE permission + a role on the production branch. This is the deepest grant story in the workshop.
> - You'll build a real manufacturing dashboard: machine status, BOM search, case notes. It uses both Direct SQL (for complex queries) and the Data API (for REST calls), showing when each is appropriate.
>
> **You'll be able to:** set up a Databricks App's [Service Principal](../../docs/glossary.md) to connect to Lakebase, deploy a working React + FastAPI dashboard on Databricks Apps, and understand the app authentication model.
>
> **Time:** about 45 minutes (setup + build + deploy)  ·  **Status:** live

## The scenario

You've learned Lakebase through journeys. Now you want to ship a real app: a manufacturing
dashboard where floor supervisors can check machine status, search the BOM, and view maintenance
logs. The app lives on Databricks Apps (the platform's managed hosting), so it scales with your
org and integrates with Databricks workspace auth.

The app's backend needs to query Lakebase. That means the app's [Service Principal](../../docs/glossary.md) (the identity
the app runs as) needs access to your Lakebase instance and project, and the PostgreSQL database.
This is the real-world version of the grant chain you learned in setup.

## What this journey includes

1. **Grant setup:** a Python script that grants your app's Service Principal access to the
   Lakebase project and database (reuses the pattern from 00-setup, but parameterized for your
   app).
2. **FastAPI backend:** a small service with endpoints for machines, BOM, and case notes.
   Uses direct SQL for complex queries and the Data API for REST calls.
3. **React frontend:** a dashboard showing machines, BOM search, and a case note viewer.
4. **Deploy script:** one command to deploy the whole stack to Databricks Apps.

You'll run the full journey locally first (so you understand each part), then deploy and see it
live in your workspace.

## The wow moment

You make a small change to the React component (say, add a new column to the machine list). Run
deploy. In seconds, your app is live in your workspace. Supervisors see the new column. No
manual server setup, no scaling configurations. That's the Databricks Apps magic.

## What you'll do

1. Set up: understand the app structure (React frontend, FastAPI backend, app.yaml config).
2. Grant access: run a script that gives the app's SP the full Lakebase grant chain.
3. Develop locally: run the app in dev mode, make sure it connects to Lakebase.
4. Deploy: push the app to Databricks Apps.
5. Test live: open the deployed app in your workspace and verify it works.

Full copy-paste steps are in [`instructions.md`](instructions.md); expected output is in
[`expected.md`](expected.md).

## Prerequisites

Finish [`../../00-setup/`](../../00-setup/) so you have a branch, can connect, and understand
the grant chain. You should also complete the main Lakebase journeys (at least
[Branch the brain](../branch-the-brain/) and [Build a knowledge graph](../kg-build/)) so you're
comfortable with the domain and Lakebase concepts.

For this journey you'll need:

- Node.js 18+ (for React development and the build toolchain)
- `uv` or `pip` for Python dependency management
- Basic familiarity with React and FastAPI (you can read and modify code, but don't need to write
  components from scratch)
- Workspace access to deploy Databricks Apps (ask your workspace admin if you're unsure)

## Wrapping up

This capstone brings it all together: Lakebase (data), Databricks Apps (platform), and SQL +
REST queries (client code). You've completed the workshop and built a production-grade app. From
here, the next step is to take your own data, your own manufacturing scenario, and apply these
same patterns: schema design, branching, querying, and app deployment.

The patterns you've learned scale from a single machine to a fleet of factories across the world,
from a sandbox branch to multi-environment deployments. Lakebase and Databricks Apps handle the
infrastructure; you focus on the business logic.
