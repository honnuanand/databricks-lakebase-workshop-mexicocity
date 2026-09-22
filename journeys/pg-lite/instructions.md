# Postgres in your browser, instructions

## How to run this journey

There are a few ways to work through the steps. Pick one:

- **Notebook, step by step (recommended for learning):** open [`pg_lite.ipynb`](pg_lite.ipynb) and run one cell at a time. Reading each result before the next step is where the learning happens.
- **In a Databricks workspace:** import [`pg_lite_databricks.py`](pg_lite_databricks.py) and run it cell by cell there.
- **By hand:** follow the numbered steps below, copying each command yourself.

This journey is interactive: you run SQL in your browser using PGlite (a WASM Postgres).
There's no Python script to run; instead, you use an HTML editor.

## Open the editor

Open the interactive editor in your browser:

```
pglite-demo.html
```

It sits right here in this journey folder. Double-click it, or open it in your editor
(VS Code, Sublime, etc.) and right-click "Open with Browser", or load it as a file:// URL in
Firefox, Chrome, Safari, or Edge.

The page loads PGlite (a few MB of WebAssembly) on first load. You'll see a status message: "✓ PGlite ready."

## Type or paste SQL

In the "SQL Editor" pane (left side), type or paste any Postgres SQL. Examples:

**CREATE TABLE:**
```sql
CREATE TABLE machines (
  id TEXT PRIMARY KEY,
  status TEXT,
  health NUMERIC
);
```

**INSERT:**
```sql
INSERT INTO machines VALUES
  ('M-204', 'healthy', 91.5),
  ('M-205', 'derated', 72.0);
```

**SELECT:**
```sql
SELECT * FROM machines;
```

**JSON aggregation:**
```sql
SELECT
  status,
  jsonb_agg(jsonb_build_object('id', id, 'health', health)) as machines
FROM machines
GROUP BY status;
```

**Window functions:**
```sql
SELECT
  id,
  status,
  ROW_NUMBER() OVER (ORDER BY health DESC) as rank
FROM machines
ORDER BY rank;
```

**ON CONFLICT (upsert):**
```sql
INSERT INTO machines VALUES ('M-204', 'operational', 99.0)
ON CONFLICT (id) DO UPDATE SET health = 99.0;
```

## Run SQL

Hit the "Run SQL" button. The SQL executes in the browser. Results appear in the "Output" pane (right side)
in a few milliseconds, no server round-trip.

## Use Quick Examples

Click any of the "Quick Examples" buttons (at the bottom) to load pre-written SQL:
- **CREATE TABLE + INSERT**, builds a table and inserts rows.
- **JSON aggregation**, shows JSONB_AGG and JSON query patterns.
- **Window functions**, ROW_NUMBER, ranking.
- **ON CONFLICT**, upsert pattern.
- **SELECT version()**, shows "PostgreSQL on wasm32", proof it's real Postgres.

## Clear output

Hit "Clear Output" to reset the output pane and start fresh.

## What you just did

You ran real Postgres SQL in the browser, client-side, with zero network. The entire Postgres engine runs
in WebAssembly. Same SQL as Lakebase; same results, same semantics.

Check the results against [`expected.md`](expected.md), and if anything went sideways, [`faq.md`](faq.md)
has common issues (usually browser-related, not SQL).
