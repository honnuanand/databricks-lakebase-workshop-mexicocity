# Feature store, served online

> ## What you'll learn
>
> **Key takeaways**
>
> - Materialize features from raw events into a feature table keyed by machine_id (PRIMARY KEY).
> - Serve features with a single primary-key lookup, measured latency in single-digit milliseconds.
> - A `computed_at` freshness stamp shows when each vector was materialized; the offline/online split is: lakehouse trains, Lakebase serves.
>
> **You'll be able to:** build an online feature store in Lakebase, measure lookup latency, and frame the feature-store pattern across offline (lakehouse) and online (Lakebase).
>
> **Time:** about 10 minutes  ·  **Status:** live

## The scenario

You're training a maintenance-risk model for machines. Training happens offline in the lakehouse on historical data (months of sensor readings, maintenance logs, failure records). The model learns patterns. When deployed, it needs *features at inference time*: for a given machine, what's the number of runs this month, average temperature, total cycles, utilization rate?

A naive approach: compute features on every inference request. That's slow (you'd need to aggregate millions of raw events in milliseconds). The better approach: precompute features offline, materialize them into an online store, and serve a vector lookup at inference time.

Lakebase plays the online-serving role: compute features in SQL, materialize them into a table keyed by machine_id, and serve a single primary-key lookup in single-digit milliseconds. Measured.

## The wow moment

You aggregate raw machine events into a feature table. Then you run 100 primary-key lookups and measure the latency: average 2-3 ms per lookup, with a `computed_at` timestamp showing freshness. That's fast enough for real-time model inference, right on the serving instance.

## What you'll do

1. Create a raw events table (machine runs, failures, maintenance).
2. Aggregate events into a feature table (runs_this_month, failures_this_month, avg_temp, total_cycles, computed_at).
3. Run 100 primary-key lookups and measure latency.
4. Show a sample feature vector (the data the model receives at inference).

Full copy-paste steps are in [`instructions.md`](instructions.md); the exact output is in [`expected.md`](expected.md).

## Prerequisites

Finish [`../../00-setup/`](../../00-setup/) so you have a branch and can connect. Nothing else; this journey is self-contained.

## Wrapping up

This is the online half of the feature-store pattern. The offline half (training on historical data) lives in the
lakehouse (Databricks + Delta). Lakebase bridges both: it's the OLTP transactional store that also serves features
at inference time. The next journey [`../pg-one-database/`](../pg-one-database/) is the finale: one table, every data type, all in one query.
