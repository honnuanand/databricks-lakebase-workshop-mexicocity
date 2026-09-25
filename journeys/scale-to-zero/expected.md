# Scale to zero, expected results

Use this to check your run. Endpoint states and timings are from a live run; yours will be
close. The shape is what matters: idle costs nothing, waking is a couple of seconds.

## Step 1, the endpoint state

If you have queried this branch recently:

```text
  branch u-arao: endpoint primary is ACTIVE
  -> serving: compute is up and metering.
```

If it has been idle for a few minutes (try `--branch production`):

```text
  branch production: endpoint primary is IDLE
  -> suspended to zero: no compute nodes, no compute cost right now.
```

## Step 3, wake it on demand

Waking a genuinely idle endpoint (the interesting case):

```text
  endpoint is IDLE; a single query will wake it. timing...
  woke IDLE -> ACTIVE; first query answered in ~1700 ms
```

If the endpoint was already warm, you will instead see it stay `ACTIVE` and the query return in
around a second (that is the network round trip, not a wake):

```text
  endpoint is ACTIVE; running a query (already warm, so this is not a cold wake)
  ACTIVE; first query answered in ~1000 ms
```

## Full run

```text
1. The endpoint's current state:
  branch production: endpoint primary is IDLE
  -> suspended to zero: no compute nodes, no compute cost right now.

2. Idle compute scales to zero on its own.
   ...

3. Wake it on demand with a single query:
  endpoint is IDLE; a single query will wake it. timing...
  woke IDLE -> ACTIVE; first query answered in ~1700 ms

4. Back to serving, and the data is exactly as it was:
  branch production: endpoint primary is ACTIVE
  -> serving: compute is up and metering.

Done. Idle costs nothing; waking on demand took ~1.7s. You only pay when you serve.
```

## The numbers that matter

| What | Expected | Why it matters |
| ---- | -------- | -------------- |
| idle endpoint state | `IDLE`, no nodes | compute released, no compute cost |
| cold wake (IDLE to serving) | about 1.7s (measured) | "start on demand" is seconds, not minutes |
| warm query | about 1s | already active; this is round trip, not a wake |
| data after wake | unchanged | suspend touches compute only, never storage |

> **From the field**
> To see a cold wake you need an endpoint that has actually gone `IDLE`, which takes a few
> minutes of no queries. If everything shows `ACTIVE`, you have been querying it; wait a few
> minutes, or point `--branch` at one you have not touched. The auto-suspend is real, it just is
> not instant.
