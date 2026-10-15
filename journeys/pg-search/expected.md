# Search, three ways, expected results

Use this to check your run. The numbers here are from our measurements; yours will be close but not identical. The *shape* of the results and the general magnitudes are what matter.

## Step 1, case notes

```text
note_id account_id  writeup
1       CTA-100240 "Cardholder reports three card-not-present charges to an overseas merchant they do not recognize; velocity spike overnight. Suspect card compromise, recommend freeze and reissue."
2       CTA-300421 "Large outbound wire to a new beneficiary in a high-risk jurisdiction, just under the reporting threshold. Structuring pattern? Needs AML review."
3       CTA-200311 "Customer disputed a recurring subscription charge. Confirmed merchant error, refunded, closed."
```

Free-text notes from analysts. These are the search corpus.

## Step 2, full-text search

```text
note_id account_id  rank
2       CTA-300421 0.121
```

The query `to_tsquery('english', 'wire | fraud')` searches for either word. Note #2 matches on "wire"
(wire to new beneficiary). Note #1 mentions "card compromise" but not the exact terms, so it doesn't
match. The rank score is a number proportional to relevance. Try `'card | compromise | freeze'`
to see more results ranked.

## Step 3, fuzzy matching

```text
account_id       similarity
CTA-100240      1.000
CTA-100241      0.923
CTA-100234      0.846
```

Accounts similar to "CTA-100240". Even with a typo like "CTA-100204", [trigram](../../docs/glossary.md)
overlap keeps the match close (similarity 0.85+). Results are sorted by similarity descending.

## Step 4, GIN index

```text
CREATE INDEX idx_case_note_fts ON bank.case_note USING gin(to_tsvector('english', writeup));
```

Index is created. Subsequent full-text search queries will use it. On small datasets (< 10k rows),
the index overhead might outweigh the benefit, so the planner may still choose a sequential scan.
On large datasets (millions of notes), the index is essential.

## Step 5, hybrid search

```text
note_id keyword_rank  semantic_sim  blended_rank
2       0.121         0.82          0.413
1       0.074         0.76          0.292
3       0.068         0.58          0.230
```

Results ranked by a blend of keyword relevance (60%) and semantic similarity (40%). Note #2 wins
because it has a strong keyword match (wire) and good semantic similarity. Notes #1 and #3 have
lower keyword scores but still appear ranked by semantic closeness. The blend depends on your weights
(60/40 here; tune as needed).

## The numbers that matter

| What | Expected | Why it matters |
| ---- | -------- | -------------- |
| [Full-text search](../../docs/glossary.md) query (100 notes) | < 10 ms | fast ranking by relevance |
| Fuzzy match (8 accounts) | < 5 ms | fast typo-tolerant search |
| [GIN](../../docs/glossary.md) index creation | instant (small dataset) | cheap to build; huge speedup at scale |
| Hybrid query (keyword + semantic) | < 20 ms | blends two signals for better results |

> **From the field**
> [Full-text search](../../docs/glossary.md) is the unsung hero of many apps. You write a full-text search query once, index it, and it scales to millions of documents. Fuzzy matching ([pg_trgm](../../docs/glossary.md)) is simpler than it sounds and catches real typos in user input. Hybrid search (blending keyword and semantic) is a recent addition (with [pgvector](../../docs/glossary.md)) and can produce surprisingly good results with modest tuning.
