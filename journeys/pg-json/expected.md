# JSON documents, expected results

Use this to check your run. The numbers here are from our measurements; yours will be close but not identical. The *shape* of the results and the general magnitudes are what matter.

## Step 1, JSONB specs

```text
('INS-CASH-MXN', 'Mexican Peso Cash', '{"ccy":"MXN"}')
('INS-SLEEVE-EQ', 'Equity Sleeve', '{"theme":"large-cap"}')
('INS-QTZL', 'Quetzal Tecnologia', '{"ticker":"QTZL","sector":"tech","beta":1.2}')
```

Each instrument has a spec JSONB column with varying fields. No nulls, just the fields that apply to each instrument.

## Step 2, containment operator (@>)

```text
('INS-QTZL', 'Quetzal Tecnologia', '{"ticker":"QTZL","sector":"tech","beta":1.2}')
('INS-ZAFR', 'Zafiro Software', '{"ticker":"ZAFR","sector":"tech","beta":0.9}')
```

All instruments that have `"sector": "tech"` in their spec (the containment check). The query returns 2 rows: QTZL and ZAFR are the seeded equities in the tech sector.

## Step 3, path extraction (#>>)

```text
('INS-QTZL', 'Quetzal Tecnologia', '...', 'tech')
('INS-ZAFR', 'Zafiro Software', '...', 'tech')
```

The `spec #>> '{sector}'` extracts the sector value as text. The `?` operator filters to instruments that have a sector key. Result shows the sector field extracted and displayed as a column. Only the two equities have a sector key.

## Step 4, GIN index

```text
CREATE INDEX idx_instrument_spec_gin ON bank.instrument USING gin(spec jsonb_path_ops);
```

The index is created. Queries over the JSONB column will now use the index if the planner decides it's beneficial. On the bank dataset (typically a few dozen instruments), the difference is invisible; on millions of instruments, GIN turns a table scan into an index scan.

## Step 5, screening query

```text
('INS-QTZL', 'Quetzal Tecnologia', '{"ticker":"QTZL","sector":"tech","beta":1.2}')
('INS-ZAFR', 'Zafiro Software', '{"ticker":"ZAFR","sector":"tech","beta":0.9}')
```

Instruments that are equities in the tech sector. The query runs in under 50 ms. The result set includes QTZL and ZAFR, which are the seeded equities with sector 'tech'.

## The numbers that matter

| What | Expected | Why it matters |
| ---- | -------- | -------------- |
| JSONB query (small dataset) | < 5 ms | fast even without index |
| JSONB query with GIN index | < 2 ms | index helps at scale; minimal overhead |
| Containment (@>) performance | same as indexed column | GIN is transparent and powerful |
| Path extraction (#>>) | included in query time | very fast; no separate evaluation |

> **From the field**
> The real win with JSONB is not speed, regular columns are fast too. The win is flexibility: you can add new fields to the spec without a schema migration (ALTER TABLE is expensive on large tables). You just insert new JSON with the new fields, and queries adapt. This is game-changing for financial products with evolving spec requirements.
