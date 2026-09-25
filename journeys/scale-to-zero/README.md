# Scale to zero

> ## What you'll learn
>
> **Key takeaways**
>
> - A Lakebase Autoscaling endpoint auto-suspends its compute to zero when it sits idle: state
>   goes to `IDLE`, the compute nodes are released, and you pay nothing for compute. No stop
>   button, it happens on its own.
> - The next query wakes it. A cold wake from `IDLE` to serving measured about 1.7 seconds on a
>   live run; a warm query is faster.
> - Suspending compute never touches your data. Only the compute goes away and comes back; the
>   storage, schema, and history stay.
>
> **You'll be able to:** see an endpoint's state (ACTIVE vs IDLE), watch idle compute cost
> nothing, and wake it on demand with one query, timing the wake.
>
> **Time:** about 10 minutes  ·  **Status:** live

## The scenario

It's 17:00 on Friday. The stamping plant's shift ends. Production stops for the weekend, the
[manufacturing execution system](../../docs/glossary.md) (MES) goes quiet, and nobody queries the
database until Monday. On a always-on database you pay full price for those idle hours anyway.

On Lakebase Autoscaling, you do not have to do anything. When the queries stop, the endpoint's
compute auto-suspends to zero. Over the weekend it costs nothing for compute. Monday morning, the
first query wakes it in about two seconds and it is serving again.

## How it works

An Autoscaling endpoint has a suspend timeout. After that long with no queries, the endpoint
transitions to `IDLE`: the compute nodes are released back to the cloud, so there is no compute
cost while it sits idle. The storage is separate and stays, so nothing is lost. The next
connection wakes the compute (`IDLE` to `ACTIVE`) and answers the query.

> **Note**
> This is genuinely automatic, not a manual stop button. You do not run a "stop" command; idle
> suspension is the default behavior. (There is a way to force an endpoint off,
> `EndpointSpec.disabled`, but the cost story is the automatic suspend, so that is what this
> journey shows.) On a warm endpoint you will not see a cold wake; point the journey at a branch
> that has been idle for a few minutes, such as `production`, to watch the wake clearly.

## The wow moment

The beat worth watching: you look at an endpoint that has gone `IDLE` on its own (costing
nothing), then run a single query and watch it wake to `ACTIVE` and answer, in about two seconds.
It breaks the mental model of "database = always-on cost center." Idle is free, and waking is a
query away.

> **From the field**
> The honest numbers, measured live: a cold wake from `IDLE` to serving took about 1.7 seconds
> (a `SELECT 1` that had to bring the compute back). A warm query, where the endpoint was already
> `ACTIVE`, was around a second (that is mostly the network round trip to the region plus minting
> a fresh credential, not a wake). Compare a Snowflake warehouse cold start, typically tens of
> seconds. Waking Lakebase compute is a couple of seconds, and the idle time before it was free.

## What you'll do

1. Look at your branch's endpoint state (`ACTIVE` = serving, `IDLE` = suspended to zero).
2. Understand that idle compute suspends to zero on its own, no action needed.
3. Wake the endpoint with a single query and time the `IDLE` to `ACTIVE` wake.
4. Confirm the endpoint is serving again and your data is exactly as it was.

Full copy-paste steps are in [`instructions.md`](instructions.md); the exact output and timings
to check against are in [`expected.md`](expected.md).

## Prerequisites

Finish [`../../00-setup/`](../../00-setup/) so you have a branch and can connect. Nothing else;
this journey stands on its own. To see a clear cold wake, use a branch you have not queried for a
few minutes (your own branch may still be warm from a previous journey); the `production` branch
is often idle and makes the wake obvious.

## Wrapping up

Once idle compute costs nothing and waking is a two-second query, the database stops being an
always-on cost center. The next journey connects the database to the lakehouse:
[One copy, both directions](../write-to-analytics/) shows operational and analytical work on one
copy, with no pipeline.
