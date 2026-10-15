# Finance edition: journey re-map spec

The finance branch keeps the SAME 31 journeys and the SAME Lakebase mechanics (all proven live
in manufacturing). Only the DOMAIN changes: table names, scenarios, and prose move from a smart
factory to a bank. This file is the authority for that re-map.

> **Mexico data (2026-10-14):** the bank's data was then localized for Mexico, in place. Ids changed
> (`ACCT-` → `CTA-`, `BR-NYC/SFO/LON` → `BR-CDMX/MTY/GDL`, fictional counterparties, custodians, and
> listed companies), `txn.amount_usd` became `amount` + `currency` + `channel`, and `account` gained
> `clabe`. The tables below still show the original finance names; `common/scripts/finance_seed.sql`
> is the source of truth for the current data.

## Schema (already built + verified live)

`common/scripts/finance_schema.sql` (schema `bank`), loaded by `common/scripts/load_bank.py`.
Default `LB_SCHEMA=bank`.

## Table + column role-map (manufacturing -> finance)

| Manufacturing (old) | Finance (new) | Notes |
| ------------------- | ------------- | ----- |
| schema `factory` | schema `bank` | |
| `plant` | `branch` | id `plant_id`->`branch_id`; a bank branch / LOB; RLS boundary + geo (lat/lon) |
| `machine` | `account` | id `machine_id`->`account_id`; the live "twin"; `line` = Checking/Savings/Credit/Wealth; `type` = retail/commercial/wealth; `status` good_standing\|watch\|frozen\|closed; `health_pct` kept |
| `sensor_reading` | `txn` | `reading_id`->`txn_id`; `machine_id`->`account_id`; `temp_c`->`amount_usd`; `vibration_mm_s`->`anomaly_score`; `rpm`->`mcc`; `load_pct`->`util_pct` |
| `product` | `fund` | `product_id`->`fund_id`; root of the holdings tree |
| `part` | `instrument` | `part_id`->`instrument_id`; `part_type`->`kind` (equity/bond/etf/cash) |
| `bom_edge` | `holding` | `child_part`->`instrument_id`; qty = units; the recursive-CTE + KG tree (fund->sub-fund->instrument) |
| `work_order` | `trade` | `wo_id`->`trade_id`; `product_id`->`fund_id`; status placed\|executing\|settled\|cancelled |
| `operation` | `settlement` | `op_id`->`settlement_id`; `wo_id`->`trade_id`; `machine_id`->`account_id`; booked into starts_at/ends_at (GiST no-overlap) |
| `supplier` | `counterparty` | `supplier_id`->`counterparty_id`; spec: credit_rating, exposure_limit_m, dual_source |
| `warehouse` | `custodian` | `warehouse_id`->`custodian_id` |
| `inventory` | `position` | `part_id`->`instrument_id`; `warehouse_id`->`custodian_id` |
| `part_supplier` | `trade_counterparty` | `lead_time_weeks`->`settle_days` |
| `maintenance_log` | `case_note` | `log_id`->`note_id`; `machine_id`->`account_id`; `system`->`category`; `defect`->`finding`; `action` kept; `confidence` kept |
| `agent_memory` | `agent_memory` | unchanged; agents renamed maintenance_advisor->`fraud_advisor`, mes_assistant->`ops_assistant` |

## Seed ids to use in prose/examples (from finance_seed.sql)

- Branches: BR-NYC, BR-SFO, BR-LON. Business units: RetailBank, GlobalMarkets.
- Accounts: ACCT-100234/100235/100240/100241 (NYC), ACCT-200310/200311 (SFO), ACCT-300420/300421 (LON).
  The recurring one (was M-204) is **ACCT-100240** (a retail Credit account, status `watch`, health 91)
  with a transaction anomaly_score spiking to 8.7 (the fraud signal).
- Funds: FUND-GROWTH-A (holds cash + 2x INS-SLEEVE-EQ + MSFT; sleeve holds AAPL + 2x UST-10Y),
  FUND-INCOME-B. Instruments: INS-AAPL, INS-UST-10Y, INS-MSFT, INS-CASH-USD, INS-SLEEVE-EQ.
- Trades: TRD-8821, TRD-8822. Counterparties: CP-GOLDMAN, CP-BARCLAYS, CP-CITADEL. Custodians: CUST-BNY, CUST-STT.

## Scenario re-maps (keep the Lakebase point identical; change the story)

- branch-the-brain: fork an account (ACCT-100240) to test a risky status change (freeze) in isolation.
- break-and-rewind: a bad DELETE wipes trades/settlements; PITR restores them.
- scale-to-zero: an idle account/branch database auto-suspends; wakes on the next query.
- write-to-analytics: write a `txn` through Lakebase, score fraud risk on the lakehouse, write it back.
- agent-memory: fraud_advisor + ops_assistant share one memory table ("is ACCT-100240 cleared, or freeze it?").
- agentic-work: an agent reads account/txn, ACTS by placing a hold (a settlement/flag), remembers it.
- learning-loop: AI reads free-text `case_note` alerts, extracts category/finding/action + confidence,
  routes low-confidence to a human analyst; corrections write back.
- pg-vector: match the most-similar instrument by spec embedding (find comparable securities).
- pg-geo: branches/counterparties/custodians on a map; "counterparties within N km", nearest custodian.
- pg-rls: business units (RetailBank vs GlobalMarkets) share one account table; each sees only its own.
- pg-booking: no double-booking a settlement slot on an account (GiST exclusion on tstzrange).
- pg-search: search analyst case notes (FTS + fuzzy account/instrument id + hybrid).
- pg-sql-parity: the recursive CTE explodes a FUND's holdings tree (was the BOM).
- pg-json: instrument/fund spec sheets (varying fields) in JSONB.
- pg-* (explain/index/mvcc/iso/perf/partition/one-database): same mechanics over account/txn.
- kg-build/sparql/infer: instrument -> fund -> branch + counterparty graph; infer "which funds are
  exposed to a distressed counterparty / a downgraded instrument?" (was recall impact).
- cmk: explainer (unchanged concept). data-api: REST over the bank schema. capstone: a bank dashboard.

## Rules

- Keep the 4-file + 2-notebook + script structure, the hero blocks, the "how to run" block, the
  book voice (no em dashes, numbers not adjectives, name the catch), and the glossary links.
- Every SQL reference updates to the bank tables/columns above. Self-seeding journeys (pg-explain/
  pg-index/pg-partition/pg-one-database) build their own demo tables, just re-theme them to bank data.
- The shared helper import and env vars are unchanged (LB_SCHEMA defaults to bank now).
- Do NOT re-introduce manufacturing nouns (machine, plant, bom, work order, sensor, factory) in
  finance content. After re-mapping, grep for those and fix any leftovers.
