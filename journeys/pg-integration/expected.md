# Pg integration, expected results

Use this to check your run. The output should be deterministic (same tables and columns every time). The key is showing that standard Postgres introspection works unmodified.

## Step 1, list of tables

```text
bom_edge
inventory
machine
maintenance_log
operation
part
part_supplier
plant
product
sensor_reading
shipment
supplier
warehouse
work_order
```

14 tables in the factory schema. This is what a BI tool sees when it connects.

## Step 2, columns (sample)

```text
(plant, branch_id, text)
(plant, name, text)
(plant, region, text)
(plant, operator, text)
(plant, lat, double precision)
(plant, lon, double precision)
...
(machine, account_id, text)
(machine, branch_id, text)
(machine, line, text)
(machine, type, text)
(machine, status, text)
(machine, health_pct, numeric)
...
(work_order, trade_id, text)
(work_order, branch_id, text)
(work_order, fund_id, text)
(work_order, qty, integer)
(work_order, status, text)
(work_order, due_ts, timestamp with time zone)
...
```

The full list is 26 tables and ~133 columns across all tables. An ORM or BI tool builds its type map from this.

## Step 3, schema map

Running `python pg_integration.py --step schema-map` shows the readable schema:

```text
=== Factory Schema Map (discovered via information_schema) ===

TABLE: plant
  branch_id: text (PK)
  name: text
  region: text
  operator: text
  lat: double precision
  lon: double precision

TABLE: machine
  account_id: text (PK)
  branch_id: text (FK → plant)
  line: text
  type: text
  status: text
  health_pct: numeric

TABLE: work_order
  trade_id: text (PK)
  branch_id: text (FK → plant)
  fund_id: text (FK → product)
  qty: integer
  status: text
  due_ts: timestamp with time zone

TABLE: sensor_reading
  txn_id: bigserial (PK)
  account_id: text (FK → machine)
  ts: timestamp with time zone
  temp_c: numeric
  anomaly_score: numeric
  rpm: integer
  util_pct: numeric

... (10 more tables)

=== Statistics ===
Total tables: 14
Total columns: ~133
Inferred PK/FK relationships: ~12
```

## Step 4, sample rows

```text
Sample from account:
('ACCT-100234', 'BR-NYC', 'Stamping-A', 'press', 'healthy', Decimal('98.50'))
('ACCT-100240', 'BR-NYC', 'Stamping-B', 'press', 'healthy', Decimal('91.00'))

Sample from trade:
('WO-8821', 'BR-NYC', 'FUND-GROWTH-A', 50, 'released', datetime.datetime(...))
('WO-8822', 'BR-SFO', 'PRD-AXLE-A2', 120, 'in_progress', datetime.datetime(...))

Sample from txn:
(1, 'ACCT-100240', datetime.datetime(..., tzinfo=tzutc()), Decimal('62.50'), Decimal('2.10'), 1180, Decimal('74.00'))
(2, 'ACCT-100240', datetime.datetime(..., tzinfo=tzutc()), Decimal('63.10'), Decimal('2.40'), 1180, Decimal('76.50'))
```

Real data, all columns present, all types matching the schema inferred from information_schema.

## Full run

Running `python pg_integration.py` with no arguments:

```text
1. List tables in factory schema (via information_schema):
  14 tables discovered
2. List columns and types (via information_schema):
  ~133 columns across 14 tables
3. Build schema map (what a BI tool infers):
  [full schema map shown above]
4. Sample rows from key tables (verify data is real):
  machine: 8 rows
  work_order: 2 rows
  sensor_reading: 5 rows
5. Confirm schema in Unity Catalog (governance):
  (same tables and columns visible in UC Data Catalog)
Done. Lakebase is Postgres; your tools work unmodified.
```

## The numbers that matter

| What | Expected | Why it matters |
| ---- | -------- | -------------- |
| Tables discovered | 14 | all factory schema tables |
| Columns discovered | ~133 | all columns across all tables |
| information_schema query time | <100 ms | fast introspection |
| Data sample accuracy | 100% | schema inference is correct |
| Governance integration | [Unity Catalog](../../docs/glossary.md) | [Unity Catalog](../../docs/glossary.md) (UC) tables visible for every Postgres table, no separate sync |

> **From the field**
> The key insight: you don't need to build a custom integration for Lakebase into your BI tool, ORM, or driver. If it speaks Postgres, it speaks Lakebase. The information_schema is the same. The wire protocol is the same. The only difference is governance: instead of a Postgres role/permission system, you get Unity Catalog on top, which is audit-friendly and works across the Databricks ecosystem. No proprietary metadata service, no SDK lock-in. Just Postgres.
