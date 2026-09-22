# Scale to zero, FAQ

## I got a permission error when trying to stop compute

Stopping compute requires `CAN_ADMIN_COMPUTE` on the project. If you're on a shared project your instructor provisioned, ask them to grant this permission. If you provisioned your own project, you're the owner and should have it; make sure `LB_PROJECT` points at *your* project and you're authenticated as the right user.

## "I don't want to stop all compute; I just want my branch to be cheaper"

Compute stopping happens at the project level, which affects all branches. The cost you see is per-compute-unit per hour. If you want cheaper idle compute, options include:
- Use a smaller compute size (CU_0.5 instead of CU_1) when provisioning your project.
- Stop the compute when you're not using it (this journey).
- On a shared project, coordinate stop/start times with your team.

There's no per-branch cost control; all branches on the project share the compute cost.

## If I stop compute, does my branch disappear?

No. Stopping compute stops the *nodes* (the running processes). The branch, the data, the schema, all untouched. Restart, and your branch is still there. The branch is a logical entity; compute is the resources to query it.

## Will stopping break my connections?

Yes. Any active connection to the database will drop when compute stops. Clients will see a network error. Re-connecting after restart will work.

## Can I stop and start on a schedule?

Yes. You can automate this with a job runner (e.g. a cron job or a cloud scheduler) that calls the Lakebase API to stop/start at specific times. The example script can be wrapped in a scheduler.

## What about backups while compute is stopped?

Lakebase backups happen at the storage layer, not at compute, so backups continue while compute is stopped. Your data is protected even though compute is off.

## Compared to my current database, how much does this save?

That depends on your workload. If your database is idle 16 hours a day (off-shift), you save 67% of compute cost. If it's 8 hours idle, you save 33%. The savings are proportional to idle time. The script doesn't calculate actual spend (that requires your workspace's cost model), but you can multiply your Lakebase CU rate by the hours saved.

## Is this different from Aurora "pause database"?

Aurora's pause feature pauses the database instance but usually keeps reserve capacity for fast restart. Lakebase's stop truly releases the nodes (effective_stopped=true, nodes=0), so there's no reserved cost. Restart is still fast (seconds) because of the stateless compute architecture.

## Why does restart take 7 seconds, not instant?

Compute is stateless, so restart is a simple provisioning step: allocate nodes, start processes, bind to the database storage. Seven seconds is the real provisioning time. It's not loading cache or running recovery; it's just starting fresh nodes. That's fast compared to traditional databases, which might need minutes to warm up or recover.
