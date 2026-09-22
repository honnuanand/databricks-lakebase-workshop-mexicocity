# Row-level security, instructions

## How to run this journey

There are a few ways to work through the steps. Pick one:

- **Notebook, step by step (recommended for learning):** open [`pg_rls.ipynb`](pg_rls.ipynb) and run one cell at a time. Reading each result before the next step is where the learning happens.
- **In a Databricks workspace:** import [`pg_rls_databricks.py`](pg_rls_databricks.py) and run it cell by cell there.
- **By hand:** follow the numbered steps below, copying each command yourself.
- **Just see it work:** run `python pg_rls.py` from this folder to execute the whole thing at once. Fast, but you learn the most from the notebook.

Run these on your own branch. If you haven't done [`../../00-setup/`](../../00-setup/), do that first; you need `LB_PROFILE`, `LB_PROJECT`, `LB_BRANCH`, and `LB_SCHEMA` set, and the factory loaded.

Everything here is a single script you can read: [`./pg_rls.py`](./pg_rls.py). You can run it end to end, or follow the steps by hand to see each piece.

## Run it end to end

```bash
cd journeys/pg-rls
python pg_rls.py
```

This walks through the entire journey and prints results. Read on for what each step does; the exact output to expect is in [`expected.md`](expected.md).

## Or step through it by hand

### Step 1, create roles for each plant operator

Create Postgres roles (one per plant, or per operator):

```bash
python pg_rls.py --step roles
```

The script runs:

```sql
CREATE ROLE IF NOT EXISTS operator_detroit;
CREATE ROLE IF NOT EXISTS operator_chicago;
CREATE ROLE IF NOT EXISTS operator_toronto;
GRANT USAGE ON SCHEMA factory TO operator_detroit, operator_chicago, operator_toronto;
GRANT SELECT ON ALL TABLES IN SCHEMA factory TO operator_detroit, operator_chicago, operator_toronto;
```

These roles are internal to Postgres; they're not Databricks users, just database identities.

### Step 2, create and enable the row-level security policy

Define a policy: "a machine row is visible to a user only if the machine's plant matches the user's operator plant":

```bash
python pg_rls.py --step policy
```

The script runs:

```sql
ALTER TABLE factory.machine ENABLE ROW LEVEL SECURITY;
CREATE POLICY machine_operator_isolation ON factory.machine
  FOR SELECT
  USING (plant_id = current_setting('app.current_operator_plant', true));
```

The `USING` clause is the filter applied to every query. `current_setting('app.current_operator_plant')` reads a session variable (set by the app on connect).

### Step 3, set session variables and query

Connect as different operators and query the same table. The [row-level security](../../docs/glossary.md) (RLS) policy filters rows based on the session variable:

```bash
python pg_rls.py --step query
```

The script connects, sets `app.current_operator_plant` to a plant ID, and runs `SELECT * FROM machine`. Different plant IDs return different rows. Same query, different results, enforced by Postgres.

### Step 4, verify EXPLAIN shows the policy

Check the query plan to confirm RLS is applied:

```bash
python pg_rls.py --step explain
```

The plan includes `Filter: (plant_id = <value>)`, showing the policy is being enforced.

## What you just did

You created roles for each plant operator, defined a row-level security policy on the machine table, enabled RLS, and verified that the same query returns different rows depending on the operator's identity. The boundary is enforced at the database layer, no app code can bypass it.
