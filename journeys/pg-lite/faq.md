# Postgres in your browser, FAQ

## The page won't load or says "Loading PGlite..." forever

PGlite is a few megabytes of WebAssembly. On a slow connection, loading can take 10+ seconds.
Give it time. If it still doesn't load after 30 seconds:

1. Check the browser console (F12 → Console). Look for errors like CORS or network failures.
2. Try a different browser (Firefox, Chrome, Safari, Edge).
3. Check your internet connection.
4. Try opening `pglite-demo.html` as a local file (File → Open in your browser) rather than via HTTP.

## I typed SQL but nothing happens when I hit "Run"

1. Check that the status says "✓ PGlite ready." If not, wait for the page to fully load.
2. Check the browser console (F12) for JavaScript errors.
3. Make sure your SQL is valid Postgres syntax. Hover over the "Run SQL" button; a tooltip may show if it's disabled.

## My SQL has a syntax error

Paste the SQL into a terminal against a real Postgres to test syntax:

```bash
psql -U your_user -d your_db -c "your SQL here"
```

Then paste the corrected SQL into the editor.

## The output looks weird or truncated

The output pane has a max-height and scrolls. If results are cut off, scroll down in the output area.
For large result sets, the HTML demo may not format nicely; it's a simple demo, not production-grade.

## Can I save my data between page reloads?

Yes, but only if persistence is enabled (IndexedDB). By default, the demo uses IndexedDB, so your tables
persist until you clear browser data.

To verify: create a table, reload the page, and try `SELECT * FROM machines;`, it should still be there.

## Can I download my data or export it?

The demo doesn't have an export feature. To get data out:
1. Run `SELECT * FROM table` and copy the output by hand.
2. Or, extend the HTML demo (it's open source) to add an export button that creates a CSV file.

## Why is PGlite so slow compared to a server?

It's not necessarily slow, but it IS single-threaded (WASM runs on one thread). On a 1000-row table with a complex
query, you might see 100+ ms instead of 10 ms. That's still fast enough for most UX; it's just not parallelized.

For heavy analytics, use Lakebase (the server).

## Can I sync PGlite back to Lakebase?

Not in this demo, it's purely local. In production, you'd use the ElectricSQL sync engine (the team behind
PGlite is now at Databricks) to reconcile local changes back to the central instance.

This journey is local-first; the sync layer is beyond scope here.

## Do I need internet to use the SQL editor?

After PGlite loads (first time), you can use the editor offline. Queries run 100% locally. Close the browser,
turn off your internet, open the editor again, it works (assuming IndexedDB persistence).

The initial load does need internet to download the WASM blob.

## What SQL is *not* supported in PGlite?

Almost everything works. Some limitations:
- **Transactions** (`BEGIN`, `COMMIT`) work but in a single-threaded context (so no real concurrency testing).
- **Triggers** and **stored procedures** (PL/pgSQL) work but are less tested.
- **Extensions** like pgvector or PostGIS are not included (you can add them with custom builds, but the demo doesn't).
- **Server configuration** commands (`ALTER SYSTEM`, `RELOAD`, etc.) don't apply.

99% of standard SQL works.

## Can I use this for production?

No. PGlite is great for:
- **Local development** (faster than spinning up a server).
- **Testing** (ship Postgres tests that run in CI without a database).
- **Local-first apps** (offline-capable web apps).
- **Agent sandboxes** (give an agent a disposable Postgres to run SQL against).

For production operational data, use Lakebase (the server).

## How is this different from SQLite?

Both run locally; both are single-process. Differences:

- **Postgres (PGlite)**: full SQL, JSON, window functions, [common table expressions](../../docs/glossary.md) (CTEs), better concurrency model (though single-threaded in WASM).
- **SQLite**: simpler, more compact, less SQL surface (no window functions natively, no JSON aggregation, fewer types).

If you know Postgres SQL, PGlite feels like home. If you want minimal footprint, SQLite is smaller.

## Can I create more complex schemas?

Yes. Create foreign keys, indexes, views, functions (PL/pgSQL), all the same as server Postgres.

The demo is simple for clarity; real schemas work the same way.
