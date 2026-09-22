# Scale to zero, expected results

Use this to check your run. Timings are from our measurements on a warm project; yours will be close but not identical. The *shape* is what matters: sub-5-second stop, sub-10-second start, nodes dropping to zero and cost meter freezing.

## Step 1, initial state

```text
  endpoint_id: primary
  state: ACTIVE
  nodes: 1
  cu: 1
```

The compute is running, serving.

## Step 2, stop

```text
  stopping compute ...
  stopped in ~4.2s; nodes: 0; effective_stopped: true
```

The API call returns fast; the instance transitions to `STOPPED` and nodes drop to zero in about 4 seconds. The effective_stopped flag confirms compute is truly released.

## Step 3, status after stop

```text
  endpoint_id: primary
  state: STOPPED
  nodes: 0
  effective_stopped: true
```

No nodes. No compute. Cost meter is at $0/hr.

## Step 4, restart

```text
  starting compute ...
  started in ~7.1s; state: ACTIVE; nodes: 1
```

Restarting takes about 7 seconds. The instance transitions from STOPPED to ACTIVE and nodes come back up.

## Step 5, status after restart

```text
  endpoint_id: primary
  state: ACTIVE
  nodes: 1
  cu: 1
```

Back to where we started. The compute is serving again.

## Full run

Running `python scale_to_zero.py` with no arguments prints the whole story:

```text
1. Check current state:
  endpoint_id: primary
  state: ACTIVE
  nodes: 1
  cu: 1
2. Stop the compute:
  stopping compute ...
  stopped in ~4.2s; nodes: 0; effective_stopped: true
3. Verify the stop (no compute, cost = $0):
  endpoint_id: primary
  state: STOPPED
  nodes: 0
  effective_stopped: true
4. Restart the compute:
  starting compute ...
  started in ~7.1s; state: ACTIVE; nodes: 1
5. Verify data is untouched:
  machine count: 8
Done. Compute stopped and restarted; data intact.
```

## The numbers that matter

| What | Expected | Why it matters |
| ---- | -------- | -------------- |
| stop time | about 4s | compute releases; cost meter freezes at $0 |
| restart time | about 7s | the compute cycle from zero to serving |
| nodes while stopped | 0 | no reserved standby capacity; truly zero cost |
| data after restart | identical | stopping compute does not touch the database |

> **From the field**
> The honest numbers: stopping takes about 4 seconds and truly releases the nodes (effective_stopped=true, nodes=0). Restarting takes about 7 seconds. These are real measurements on warm instances. A cold start (if the project is very idle) can be slower. Compare that to some databases' "pause" operations, which may keep reserved capacity around, or to Snowflake warehouse start times (typically 30–60 seconds of warmup). This stop/start is genuine and fast.
