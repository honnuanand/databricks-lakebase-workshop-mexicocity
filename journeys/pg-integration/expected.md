# Pg integration, expected results

Use this to check your run. The point is that standard Postgres introspection works unmodified:
an `information_schema` query maps the whole schema, exactly what any BI tool or ORM does.

**One honest caveat on the counts.** `information_schema` returns *everything* on your branch, not
just the 14 bank tables. If you have run the PostGIS journey you will also see `geometry_columns`,
`geography_columns`, and `spatial_ref_sys`; if you have run the CDC / feature-store journeys you
will see `txn_history`, `account_events_for_features`, and `account_features_online`. That is the
correct, real BI-tool experience, a client sees the live state of the database. So your table and
column counts depend on which journeys you have run; the numbers below are the 14-table baseline.

## Step 1, list of tables

The 14 core bank tables:

```text
account
agent_memory
branch
case_note
counterparty
custodian
fund
holding
instrument
position
settlement
trade
trade_counterparty
txn
```

Plus any extension or prior-journey tables (see the caveat above). This is what a BI tool sees when
it connects.

## Step 2, columns (sample)

```text
account:
  account_id: text
  branch_id: text
  line: text
  type: text
  status: text
  health_pct: numeric
trade:
  trade_id: text
  branch_id: text
  fund_id: text
  qty: integer
  status: text
  due_ts: timestamp with time zone
txn:
  txn_id: bigint
  account_id: text
  ts: timestamp with time zone
  amount: numeric
  anomaly_score: numeric
  mcc: integer
  util_pct: numeric
  fraud_risk: numeric
```

An ORM or BI tool builds its type map from exactly this.

## Step 3, schema map

Running `python pg_integration.py --step schema-map` shows the readable schema:

```text
=== Bank Schema Map (discovered via information_schema) ===

TABLE: account
  account_id: text NOT NULL
  branch_id: text
  line: text
  type: text
  status: text
  health_pct: numeric

TABLE: branch
  branch_id: text NOT NULL
  name: text
  region: text
  operator: text
  lat: double precision
  lon: double precision

TABLE: trade
  trade_id: text NOT NULL
  branch_id: text
  fund_id: text
  qty: integer
  status: text
  due_ts: timestamp with time zone

TABLE: txn
  txn_id: bigint NOT NULL
  account_id: text
  ts: timestamp with time zone
  amount: numeric
  anomaly_score: numeric
  mcc: integer
  util_pct: numeric
  fraud_risk: numeric

... (the rest of the bank tables)

=== Statistics ===
Total tables: 14 (plus extension/prior-journey tables)
Total columns: ~90 across the core bank tables
```

## Step 4, sample rows

```text
Sample from account:
  ('CTA-100234', 'BR-CDMX', 'Checking', 'retail', 'good_standing', Decimal('98.50'), '999180000001002342')
  ('CTA-100235', 'BR-CDMX', 'Savings', 'retail', 'good_standing', Decimal('96.20'), '999180000001002355')
  ('CTA-100240', 'BR-CDMX', 'Credit', 'retail', 'watch', Decimal('91.00'), '999180000001002407')

Sample from trade:
  ('TRD-8821', 'BR-CDMX', 'FUND-GROWTH-A', 50, 'placed', datetime.datetime(...))
  ('TRD-8822', 'BR-MTY', 'FUND-INCOME-B', 120, 'executing', datetime.datetime(...))

Sample from txn:
  (1, 'CTA-100240', datetime.datetime(..., tzinfo=...), Decimal('2150.00'), 'MXN', 'tarjeta', Decimal('2.10'), 5411, Decimal('74.00'), None)
  (2, 'CTA-100240', datetime.datetime(..., tzinfo=...), Decimal('5980.00'), 'MXN', 'tarjeta', Decimal('2.40'), 5812, Decimal('76.50'), None)
  (3, 'CTA-100240', datetime.datetime(..., tzinfo=...), Decimal('38500.00'), 'MXN', 'SPEI', Decimal('8.70'), None, Decimal('92.00'), None)
```

Real data, all columns present, all types matching the schema inferred from information_schema. (The
trailing `None` on txn rows is the `fraud_risk` column, populated only by the write-to-analytics
journey.)

## Full run

Running `python pg_integration.py` with no arguments:

```text
1. List tables in the bank schema (via information_schema):
  <N> tables discovered   (14 core + any extension/prior-journey tables)
2. List columns and types (via information_schema):
  <M> columns across all tables
3. Build schema map (what a BI tool infers):
  [full schema map shown above]
4. Sample rows from key tables (verify data is real):
  account: 3 rows shown
  trade: 2 rows shown
  txn: 3 rows shown
5. Confirm schema in Unity Catalog (governance):
  (same tables and columns visible in UC Data Catalog)
Done. Lakebase is Postgres; your tools work unmodified.
```

## The numbers that matter

| What | Expected | Why it matters |
| ---- | -------- | -------------- |
| Core bank tables | 14 | the bank schema baseline |
| Tables discovered | 14 + extensions/prior journeys | a client sees the live database state |
| information_schema query time | <100 ms | fast introspection |
| Data sample accuracy | 100% | schema inference is correct |
| Governance integration | [Unity Catalog](../../docs/glossary.md) | UC tables visible for every Postgres table, no separate sync |

> **From the field**
> The key insight: you don't need to build a custom integration for Lakebase into your BI tool, ORM, or driver. If it speaks Postgres, it speaks Lakebase. The information_schema is the same. The wire protocol is the same. The only difference is governance: instead of a Postgres role/permission system, you get Unity Catalog on top, which is audit-friendly and works across the Databricks ecosystem. No proprietary metadata service, no SDK lock-in. Just Postgres.
