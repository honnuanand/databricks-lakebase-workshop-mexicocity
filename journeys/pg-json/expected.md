# JSON documents, expected results

Use this to check your run. The numbers here are from our measurements; yours will be close but not identical. The *shape* of the results and the general magnitudes are what matter.

## Step 1, JSONB specs

```text
('PT-BEARING-6204', 'Deep groove ball bearing 6204', '{"load_capacity_kg": 500, "material": "steel", "temp_min_c": -20, "temp_max_c": 80}')
('PT-SHAFT-A', 'Precision shaft A', '{"material": "stainless", "diameter_mm": 15.5, "runout_mm": 0.05}')
('PT-FASTENER-M5', 'M5 hex bolt', '{"tensile_strength_mpa": 800, "coating": "zinc", "material": "steel"}')
```

Each part has a spec JSONB column with varying fields. No nulls, just the fields that apply to each part.

## Step 2, containment operator (@>)

```text
('PT-BEARING-6204', 'Deep groove ball bearing 6204', '{"load_capacity_kg": 500, "material": "steel", ...}')
('PT-SHAFT-A', 'Precision shaft A', '{"material": "stainless", ...}')
('PT-FASTENER-M5', 'M5 hex bolt', '{"tensile_strength_mpa": 800, "coating": "zinc", "material": "steel"}')
```

All parts that have `"material": "steel"` in their spec (the containment check). The query returns 3-5 rows depending on how many parts were seeded with steel material.

## Step 3, path extraction (#>>)

```text
('PT-BEARING-6204', 'Deep groove ball bearing 6204', '...', 'steel')
('PT-SHAFT-A', 'Precision shaft A', '...', 'stainless')
('PT-FASTENER-M5', 'M5 hex bolt', '...', 'steel')
```

The `spec #>> '{material}'` extracts the material value as text. The `?` operator filters to parts that have a material key. Result shows the material field extracted and displayed as a column.

## Step 4, GIN index

```text
CREATE INDEX idx_part_spec_gin ON factory.part USING gin(spec jsonb_path_ops);
```

The index is created. Queries over the JSONB column will now use the index if the planner decides it's beneficial. On the factory dataset (typically a few hundred parts), the difference is invisible; on millions of parts, GIN turns a table scan into an index scan.

## Step 5, compliance query

```text
('PT-BEARING-6204', 'Deep groove ball bearing 6204', '{"load_capacity_kg": 500, "material": "steel", "temp_min_c": -20, "temp_max_c": 80}')
```

Parts that meet the harsh-environment spec: material is stainless OR steel, min temp is -20 or colder, and max temp is 80 or warmer. The query runs in under 50 ms. The result set size depends on how many parts in the seeded factory match the criteria; typically 1-5 rows for a strict query.

## The numbers that matter

| What | Expected | Why it matters |
| ---- | -------- | -------------- |
| JSONB query (small dataset) | < 5 ms | fast even without index |
| JSONB query with GIN index | < 2 ms | index helps at scale; minimal overhead |
| Containment (@>) performance | same as indexed column | GIN is transparent and powerful |
| Path extraction (#>>) | included in query time | very fast; no separate evaluation |

> **From the field**
> The real win with JSONB is not speed, regular columns are fast too. The win is flexibility: you can add new fields to the spec without a schema migration (ALTER TABLE is expensive on large tables). You just insert new JSON with the new fields, and queries adapt. This is game-changing for products with evolving spec requirements.
