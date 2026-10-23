# Feature store, served online

> ## What you'll learn
>
> **Key takeaways**
>
> - Materialize features from raw transaction events into a feature table keyed by account_id (PRIMARY KEY).
> - Serve features with a single primary-key lookup, measured latency in single-digit milliseconds.
> - A `computed_at` freshness stamp shows when each feature vector was materialized; the offline/online split is: lakehouse trains fraud models, Lakebase serves real-time scores.
>
> **You'll be able to:** build an online fraud-risk feature store in Lakebase, measure lookup latency, and frame the feature-store pattern across offline (lakehouse) and online (Lakebase).
>
> **Time:** about 10 minutes  ·  **Status:** live

## The scenario

You're training a fraud-risk model for accounts. Training happens offline in the lakehouse on historical data, months of transaction records, anomaly scores, and case notes. The model learns patterns that signal fraud. When deployed, it needs features at inference time: for a given account, what's the transaction count this month, average anomaly score, total amount spent, account utilization?

A naive approach: compute features on every authorization. That's slow, you'd need to aggregate millions of raw transactions in milliseconds. The better approach: precompute features offline, materialize them into an online store, and serve a lookup at inference time.

Lakebase plays the online-serving role: compute features in SQL, materialize them into a table keyed by account_id, and serve a single primary-key lookup in single-digit milliseconds. Measured, at the moment of authorization.

## The wow moment

You aggregate raw account transaction events into a feature table. Then you run 100 primary-key lookups and measure the latency: average 2-3 ms per lookup, with a `computed_at` timestamp showing freshness. That's fast enough for real-time fraud scoring at authorization time, right on the serving instance.

## What you'll do

1. Create a raw events table (account transaction events with anomaly scores).
2. Aggregate events into a feature table (txns_this_month, disputes_this_month, avg_anomaly_score, total_amount, computed_at).
3. Run 100 primary-key lookups and measure latency.
4. Show a sample feature vector (the data the fraud model receives at inference).

Full copy-paste steps are in [`instructions.md`](instructions.md); the exact output is in [`expected.md`](expected.md).

## Prerequisites

Finish [`../../00-setup/`](../../00-setup/) so you have a branch and can connect. Nothing else; this journey is self-contained.

## Wrapping up

This is the online half of the feature-store pattern. The offline half (training on historical data) lives in the lakehouse, Databricks + Delta. Lakebase bridges both: it's the [OLTP](../../docs/glossary.md) transactional store that also serves features at inference time. The next journey [`../pg-one-database/`](../pg-one-database/) is the finale: one table, every data type, all in one query.
