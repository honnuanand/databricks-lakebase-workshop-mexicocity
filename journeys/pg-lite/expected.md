# Postgres in your browser, expected results

This journey runs in your browser using PGlite (WASM Postgres). Results depend on what SQL you run.
Check your browser console (Dev Tools) if something doesn't work as expected.

## Page load

```text
Loading PGlite (WASM Postgres)...
```

After a moment (a few seconds, depending on bandwidth):

```text
✓ PGlite ready. Type SQL and run.
PostgreSQL: PostgreSQL 18.3 on x86_64-pc-linux-gnu, compiled by emcc (Emscripten gcc/clang-like replacement)
```

This proves it: full Postgres 18.3 running on WASM inside your browser.

## Quick Example: CREATE TABLE + INSERT

```sql
CREATE TABLE accounts (
  account_id TEXT PRIMARY KEY,
  status TEXT,
  health_pct NUMERIC(5,2)
);

INSERT INTO accounts VALUES
  ('ACCT-100234', 'good_standing', 98.5),
  ('ACCT-100240', 'watch', 91.0),
  ('ACCT-100241', 'good_standing', 99.1);

SELECT * FROM accounts;
```

Output:

```text
(0 rows affected)
(3 rows affected)
account_id | status | health_pct
-----------|--------|----------
ACCT-100234 | good_standing | 98.5
ACCT-100240 | watch | 91.0
ACCT-100241 | good_standing | 99.1
```

CREATE and INSERT report row counts; SELECT shows the results as a table.

## Quick Example: JSON aggregation

```sql
CREATE TABLE instruments (
  instrument_id TEXT PRIMARY KEY,
  spec JSONB
);

INSERT INTO instruments VALUES
  ('INS-AAPL', '{"kind": "equity", "ticker": "AAPL"}'),
  ('INS-UST-10Y', '{"kind": "bond", "tenor": "10Y"}');

SELECT
  instrument_id,
  spec->>'kind' as kind,
  spec->>'ticker' as ticker
FROM instruments;
```

Output:

```text
(0 rows affected)
(2 rows affected)
instrument_id | kind | ticker
--------------|------|-------
INS-AAPL | equity | AAPL
INS-UST-10Y | bond | null
```

JSON extraction (->>) works in the browser the same way as on Lakebase.

## Quick Example: Window functions

```sql
CREATE TABLE txns (
  id SERIAL PRIMARY KEY,
  account_id TEXT,
  amount_usd INT
);

INSERT INTO txns(account_id, amount_usd) VALUES
  ('ACCT-1', 100), ('ACCT-1', 95), ('ACCT-2', 80), ('ACCT-2', 85);

SELECT
  account_id,
  amount_usd,
  ROW_NUMBER() OVER (PARTITION BY account_id ORDER BY amount_usd DESC) as rank
FROM txns
ORDER BY account_id, rank;
```

Output:

```text
(0 rows affected)
(4 rows affected)
account_id | amount_usd | rank
-----------|------------|-----
ACCT-1 | 100 | 1
ACCT-1 | 95 | 2
ACCT-2 | 85 | 1
ACCT-2 | 80 | 2
```

Window functions work identically in the browser Postgres.

## Quick Example: SELECT version()

```sql
SELECT version() as pg_version;
```

Output:

```text
pg_version
-----------
PostgreSQL 18.3 on x86_64-pc-linux-gnu, compiled by emcc (Emscripten gcc/clang-like replacement)
```

Proof: real Postgres, running on WASM. "emcc" = Emscripten compiler (the WASM toolchain).

## Full run (all examples)

If you loaded each Quick Example in sequence, you'd see:
- CREATE TABLE + INSERT: table built, 3 rows inserted
- JSON aggregation: JSONB extraction works
- Window functions: PARTITION BY and ranking work
- ON CONFLICT: upsert syntax works
- SELECT version(): PostgreSQL 18.3 on WASM

**Output latency: single-digit milliseconds per query.** No network round-trip.

## The numbers that matter

| What | Expected | Why it matters |
| ---- | -------- | -------------- |
| Page load time | 2-5 seconds | WASM Postgres downloads (few MB); first load only |
| Query latency | 1-10 ms | Sub-network speeds; no round-trip |
| SQL surface | full Postgres | CREATE, INSERT, SELECT, JSON, window functions, ON CONFLICT, everything |
| Network calls | 0 | All computation is client-side |
| Persistence | IndexedDB or memory | Data survives page reload (if IndexedDB) or resets (if memory) |

> **From the field**
> This is the same Postgres engine you run on Lakebase, now compiled to WASM. Same SQL, same
> data types, same semantics. The difference: no network latency, no server infrastructure.
> Works offline. Perfect for local-first apps, edge deployments, agent sandboxes, and development.
