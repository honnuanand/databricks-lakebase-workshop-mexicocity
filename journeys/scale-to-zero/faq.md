# Scale to zero, FAQ

## I never see the endpoint go IDLE; it is always ACTIVE

You have been querying it. An Autoscaling endpoint only suspends after its suspend timeout with no queries. If every journey you run touches the same branch, it stays warm. To watch a real cold wake, point at a branch you have not touched for a few minutes:

```bash
python scale_to_zero.py --step status --branch production
```

The `production` branch is often idle because nobody runs the workshop journeys against it directly.

## Do I have to press a stop button to save money?

No. That is the whole point. Idle suspension is automatic: when the queries stop, the compute goes to `IDLE` on its own and costs nothing. You do not run a stop command. (There is a way to force an endpoint off, `EndpointSpec.disabled=true`, but the cost story that matters is the automatic suspend, so that is what this journey shows.)

## If the endpoint suspends, does my branch or data disappear?

No. Suspending releases the compute *nodes* only. The branch, the account and transaction data, the schema, the history, all untouched. The next query wakes the compute and your branch is exactly as it was. The storage layer is separate from compute and always stays.

## Will an idle endpoint drop my open connections?

Yes. When the endpoint suspends, any open connection to it drops. A client holding a connection will see a network error. Opening a new connection after it has suspended will wake the compute and succeed. In practice, pooled clients reconnect transparently on the next query.

## Why does the cold wake take about 1.7 seconds, not instant?

Waking from `IDLE` means the control plane allocates fresh compute nodes, starts the Postgres process, and binds it to the branch's storage. On a live run that measured about 1.7 seconds for a `SELECT 1` that had to bring compute back. It is not loading a cache or running recovery; it is starting stateless compute. That is fast compared to a Snowflake warehouse cold start, which is typically tens of seconds.

## What about settlement batches or backups while compute is suspended?

Lakebase backups and WAL retention live at the storage layer, not at compute, so they are unaffected while the endpoint is idle. If you need a scheduled job (for example an end-of-day settlement batch) to run on a schedule, that job's query will wake the endpoint when it connects. There is no window where your data is unprotected because compute suspended.

## How much does this actually save for a bank workload?

It depends on your usage pattern. A trading-desk database that is quiet 16 hours a day (overnight plus weekends amortized) saves roughly 67% of compute cost versus always-on; one quiet 8 hours a day saves about 33%. The savings are proportional to idle time. The script does not compute dollar spend (that needs your workspace's CU rate), but you can multiply your Lakebase CU rate by the idle hours.

## Is this different from Aurora "pause database"?

Aurora's pause usually keeps reserve capacity for a fast restart, so you still pay something while paused. A Lakebase Autoscaling endpoint truly releases the nodes when it goes `IDLE` (no compute cost at all), and the next query brings them back in seconds because compute is stateless. You get both: zero compute cost while idle, and a seconds-scale wake.

## It failed with an authentication error

Your Databricks login expired (they last about an hour). Re-run the login from [`../../00-setup/auth.md`](../../00-setup/auth.md), then re-run the step:

```bash
databricks auth login --host https://<your-workspace>.cloud.databricks.com --profile workshop
```
