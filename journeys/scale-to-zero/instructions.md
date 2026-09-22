# Scale to zero, instructions

Run these on your own branch. If you haven't done [`../../00-setup/`](../../00-setup/), do that first; you need `LB_PROFILE`, `LB_PROJECT`, `LB_BRANCH`, and `LB_SCHEMA` set.

Everything here is a single script you can read: [`./scale_to_zero.py`](./scale_to_zero.py).
You can run it end to end, or follow the steps by hand to see each piece.

> **Warning**
> This journey stops database compute on the **project level**. If you're on a shared project, other journeys will pause until you restart. If you're unsure you're on your own project, ask your instructor before proceeding.

## Run it end to end

```bash
cd journeys/scale-to-zero
python scale_to_zero.py
```

This walks the whole story: checks the compute state, stops it, verifies the stop, restarts it, and prints timings. Read on for what each step does; the exact output to expect is in [`expected.md`](expected.md).

## Or step through it by hand

### Step 1, check the current state

Query the project's compute endpoint to see its current state:

```bash
python scale_to_zero.py --step status
```

You'll see output like:

```text
  endpoint_id: primary
  state: ACTIVE
  nodes: 1
  cu: 1
```

The endpoint is `ACTIVE`, which means compute is running.

### Step 2, stop the compute

```bash
python scale_to_zero.py --step stop
```

This calls the Lakebase API to stop the compute on your project:

```python
w.postgres.update_database_instance(name=..., database_instance=DatabaseInstance(stopped=True))
```

The script waits for the state to transition to `STOPPED` and prints:

```text
  stopping compute ...
  stopped in ~4.2s; nodes: 0; effective_stopped: true
```

The compute is now stopped and costs nothing.

### Step 3, verify the stop

```bash
python scale_to_zero.py --step status
```

You'll see:

```text
  endpoint_id: primary
  state: STOPPED
  nodes: 0
  effective_stopped: true
```

### Step 4, restart the compute

```bash
python scale_to_zero.py --step start
```

This calls:

```python
w.postgres.update_database_instance(name=..., database_instance=DatabaseInstance(stopped=False))
```

The script waits for the state to transition to `ACTIVE` and prints:

```text
  starting compute ...
  started in ~7.1s; state: ACTIVE; nodes: 1
```

### Step 5, verify data is untouched

```bash
python ../../common/scripts/lakebase.py --sql \
  "SELECT count(*) FROM factory.machine"
```

The machine table is still intact. Stopping compute does not touch the data.

## What you just did

You stopped database compute to $0/hr, restarted it, and confirmed the data was untouched. Compare the timings you saw against [`expected.md`](expected.md), and if anything went sideways, [`faq.md`](faq.md) has the common causes.
