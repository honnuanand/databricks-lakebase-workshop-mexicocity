# Feature store, served online, FAQ

## My latencies are much higher than expected, 20+ ms

A few possible causes:

1. The project is cold, first query of the session. Warm it up by running a few queries first.
2. Network latency to the instance. Check with `python lakebase.py --check`, should be about 100 ms for a simple SELECT 1.
3. The table isn't indexed. The script uses PRIMARY KEY, which creates an index. Verify: `\d account_features_online` in psql.

If latencies are consistently high, check if the instance is under load or scaled down.

## How often should I refresh the features?

It depends on your use case:

- **Real-time fraud scoring**: refresh every minute or on-demand.
- **Batch risk models**: refresh hourly or daily.
- **Account health scores**: refresh weekly.

The `computed_at` timestamp lets the model decide whether to trust the freshness. Stale features mean stale predictions.

## Can I materialize features in more than one table?

Yes, and it's common. You might have:

- `account_features_online` (one row per account, keyed by account_id)
- `branch_features_online` (one row per branch, keyed by branch_id)
- `counterparty_features_online` (one row per counterparty, keyed by counterparty_id)

Each table serves a different entity at inference time. The pattern is the same: PRIMARY KEY plus single lookups.

## What if I need features on demand, not pre-materialized?

You can run the aggregation query directly at inference time, but it's slower, you need to aggregate raw events. Latency jumps from 2 ms to 100+ ms. Pre-materialization (this journey) is the speed move. Trade-off: freshness versus latency. Most systems choose materialization plus refresh schedules.

## Do I need a vector database for this?

No. If your features include vectors, embeddings, similarity scores, Postgres with pgvector handles them. Vectors live in the same row as scalar features. Serve one row, get all features including vectors. No separate vector store needed.

## How do I keep the lakehouse and Lakebase features in sync?

The LTAP journey shows this pattern. You'd run:

1. Compute features in the lakehouse, SQL on Delta tables.
2. Write the result back to Lakebase, COPY or INSERT from the lakehouse connector.
3. Repeat on a schedule, hourly, daily, etc.

Both the training data and serving data come from the same source of truth, the lakehouse, so they stay aligned.

## Can I serve features from the lakehouse directly?

Not with the same latency. Lakehouse queries are analytical, optimized for throughput, not operational, optimized for latency. A feature lookup from the lakehouse takes 100+ ms, network plus query orchestration. Lakebase's in-region PRIMARY KEY lookup is 2-5 ms. For real-time fraud scoring, serve from Lakebase.
