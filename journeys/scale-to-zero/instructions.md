# Scale to zero, instructions

## How to run this journey

There are a few ways to work through the steps. Pick one:

- **Notebook, step by step (recommended for learning):** open [`scale_to_zero.ipynb`](scale_to_zero.ipynb) and run one cell at a time. Reading each result before the next step is where the learning happens.
- **In a Databricks workspace:** import [`scale_to_zero_databricks.py`](scale_to_zero_databricks.py) and run it cell by cell there.
- **By hand:** follow the numbered steps below, copying each command yourself.
- **Just see it work:** run `python scale_to_zero.py` from this folder to execute the whole thing at once. Fast, but you learn the most from the notebook.

Run these on your own branch. If you haven't done [`../../00-setup/`](../../00-setup/), do that first; you need `LB_PROFILE`, `LB_PROJECT`, `LB_BRANCH`, and `LB_SCHEMA` set.

> **Note**
> This journey does not press a stop button. On a Lakebase Autoscaling endpoint, idle compute suspends to zero on its own, and the next query wakes it. There is nothing destructive here: watching the state and waking it with a `SELECT 1` is safe to run on a shared project.

## Run it end to end

```bash
cd journeys/scale-to-zero
python scale_to_zero.py
```

This walks the whole story: reads the endpoint state, explains that idle suspends to zero automatically, wakes it with one query, times the wake, and confirms the data is untouched. Read on for what each step does; the exact output to expect is in [`expected.md`](expected.md).

## Or step through it by hand

### Step 1, check the current state

Read the branch's compute endpoint state. This is a control-plane read (the SDK), not SQL:

```bash
python scale_to_zero.py --step status
```

You'll see output like:

```text
  branch u-arao: endpoint primary is ACTIVE
  -> serving: compute is up and metering.
```

`ACTIVE` means compute is up and metering. `IDLE` means it auto-suspended to zero: no compute nodes, no compute cost. A branch you just used is usually `ACTIVE`; one you have not queried for a few minutes is `IDLE`.

### Step 2, idle compute suspends to zero on its own

There is no command to run here. With no queries, an Autoscaling endpoint auto-suspends to `IDLE` after its suspend timeout, and the compute nodes are released. You pay nothing for compute while it sits idle. To watch a clear cold wake, point at a branch that has actually been idle (for example the `production` branch if you have not touched it):

```bash
python scale_to_zero.py --step status --branch production
```

### Step 3, wake it on demand with one query

A single `SELECT 1` wakes the endpoint. Waking is about the compute, not any table, so this works on any branch:

```bash
python scale_to_zero.py --step wake --branch production
```

You'll see the wake timed:

```text
  endpoint is IDLE; a single query will wake it. timing...
  woke IDLE -> ACTIVE; first query answered in ~1700 ms
```

If the endpoint was already warm, you'll instead see it stay `ACTIVE` and the query return in around a second (that is the network round trip, not a cold wake).

### Step 4, verify data is untouched

Suspending compute never touches your data. Confirm the account table is still intact:

```bash
python ../../common/scripts/lakebase.py --sql \
  "SELECT count(*) FROM bank.account"
```

The account table is still there with all its rows. Only the compute suspended and woke; the storage stayed.

## What you just did

You saw idle Lakebase compute cost nothing automatically, woke it on demand with a single query in about two seconds, and confirmed the data was untouched. Compare the timings you saw against [`expected.md`](expected.md), and if anything went sideways, [`faq.md`](faq.md) has the common causes.
