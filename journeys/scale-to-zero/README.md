# Scale to zero

> ## What you'll learn
>
> **Key takeaways**
>
> - Stop the database compute on demand: the instance releases its nodes in about 4 seconds and the cost meter freezes at $0.
> - Restart it in about 7 seconds. The compute spins back up and the meter runs again.
> - This is stop/start on demand, not auto-idle-with-millisecond-wake. Idle compute costs nothing; you only pay when you're serving.
>
> **You'll be able to:** stop and start database compute on demand, watch the cost meter tick to zero, and restart in seconds.
>
> **Time:** about 10 minutes  ·  **Status:** live

## The scenario

It's 17:00 on Friday. The stamping plant shifts end. Production stopped for the day, the [manufacturing execution system](../../docs/glossary.md) (MES) is idle, and the factory runs on skeleton crew until Monday morning. But the database still runs. The database compute, the memory, the reserved capacity, all humming along at full price for two days of nobody querying it.

On most databases, you pay for always-on. Maybe you've got reserved instances for the peak hours, but the idle hours bleed money. On Lakebase, you stop the compute.

## How it works

Unlike some databases, where "stopping" means downtime or a backup to slow rollback, stopping Lakebase compute is surgical. The database storage stays. The schema, the data, the backups, all untouched. Only the compute (the nodes, the memory, the cache) shuts down and releases back to the cloud. Restart it when production starts Monday, and you're serving again in seconds.

> **Note**
> This journey demonstrates stop/start on demand. Some databases claim "auto-idle" with millisecond wake times, but that usually means you keep paying for reserved capacity standing by. On Lakebase, "scale to zero" means the compute truly stops, the meter reads $0/hr, and restart is genuinely a cycle, not a warm standby. The honest scope: you stop/start by hand (or with a scheduled job); it's not automatic millisecond-granularity idle wake.

## The wow moment

The beat worth watching: you stop the compute, the cost meter freezes at $0, and the state indicator goes dark. Nothing is running. Then you restart, and the database is serving again in about seven seconds. The moment matters because it breaks the mental model of "database = always-on cost center." This one has a switch.

> **From the field**
> The honest number: stopping takes about 4 seconds (the instance transitions to `STOPPED`, nodes release). Restarting takes about 7 seconds (the instance transitions to `AVAILABLE`, nodes provision). These are real measurements; cold starts (first start of a very-long-idle instance) can be slightly slower. Compare that to a RDS "pause database" (which isn't truly zero compute on many instance types) or a Snowflake warehouse start (typically 30–60 seconds of warmup). This is genuine stop/start.

## What you'll do

1. Check your branch's compute state and cost rate (running).
2. Stop the compute and watch the cost meter freeze.
3. Confirm the instance is stopped and the cost is $0.
4. Restart the compute and time how long until it's serving again.
5. Confirm the data is untouched and the meter is running again.

Full copy-paste steps are in [`instructions.md`](instructions.md); the exact output and timings to check against are in [`expected.md`](expected.md).

## Prerequisites

Finish [`../../00-setup/`](../../00-setup/) so you have a branch and can connect. Nothing else; this journey stands on its own. Be aware that if you're on a shared project, stopping compute affects *all* other journeys on the same project until you restart. If you're unsure, ask your instructor.

> **Warning**
> Stopping compute on a shared project will pause other journeys running on the same project. Only run this if you're sure you're on your own project or have coordinated with others on the team.

## Wrapping up

Once you can reliably stop compute to $0 and restart in seconds, the mental model of the database as an always-on cost center changes. The next journey shows how to connect the database to the lakehouse: [Write to analytics](../write-to-analytics/) demonstrates live data flow in both directions without a pipeline.
