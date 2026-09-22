# Search, three ways, expected results

Use this to check your run. The numbers here are from our measurements; yours will be close but not identical. The *shape* of the results and the general magnitudes are what matter.

## Step 1, maintenance write-ups

```text
log_id  machine_id  writeup
1       M-204       "Vibration on bearing housing, likely wear. Replaced bearing 6204, tested OK."
2       M-301       "Hydraulic pressure drop detected. Checked seal, replaced filter."
3       M-405       "Nosewheel hydraulic actuator sluggish in retract. Replaced O-ring, actuator responsive."
```

Free-text notes from engineers. These are the search corpus.

## Step 2, full-text search (FTS)

```text
log_id  machine_id  rank
3       M-405       1.234
5       M-204       0.987
2       M-301       0.654
```

Logs ranked by relevance to "hydraulic & bearing". Log #3 ranks highest because it has both words close together ("hydraulic actuator" near "bearing"). The rank score is a number proportional to relevance.

## Step 3, fuzzy matching

```text
part_id             similarity
PT-BEARING-6204     1.000
PT-BEARING-6205     0.850
PT-BEARING-630      0.600
```

Parts similar to "PT-BEARING-6204". Even with a typo like "PT-BEARING-6240", trigram overlap keeps the match close (similarity 0.85+). Results are sorted by similarity descending.

## Step 4, GIN index

```text
CREATE INDEX idx_maintenance_log_fts ON factory.maintenance_log USING gin(to_tsvector('english', writeup));
```

Index is created. Subsequent FTS queries will use it. On small datasets (< 10k rows), the index overhead might outweigh the benefit, so the planner may still choose a sequential scan. On large datasets (millions of rows), the index is essential.

## Step 5, hybrid search

```text
log_id  keyword_rank  semantic_sim  blended_rank
3       1.234         0.87          1.078
5       0.987         0.45          0.798
2       0.654         0.92          0.724
```

Results ranked by a blend of keyword relevance (60%) and semantic similarity (40%). Log #3 wins because it has good keyword match, even though log #2 has higher semantic similarity. The blend depends on your weights (60/40 here; tune as needed).

## The numbers that matter

| What | Expected | Why it matters |
| ---- | -------- | -------------- |
| FTS query (500 logs) | < 10 ms | fast ranking by relevance |
| Fuzzy match (500 parts) | < 5 ms | fast typo-tolerant search |
| GIN index creation | instant (small dataset) | cheap to build; huge speedup at scale |
| Hybrid query (keyword + semantic) | < 20 ms | blends two signals for better results |

> **From the field**
> Full-text search is the unsung hero of many apps. You write a FTS query once, index it, and it scales to millions of documents. Fuzzy matching (pg_trgm) is simpler than it sounds and catches real typos in user input. Hybrid search (blending keyword and semantic) is a recent addition (with pgvector) and can produce surprisingly good results with modest tuning.
