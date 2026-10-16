# Search, three ways, expected results

Use this to check your run. The numbers here are from our measurements; yours will be close but not identical. The *shape* of the results and the general magnitudes are what matter.

## Step 1, case notes

```text
note_id account_id  writeup
1       CTA-100240 "Cardholder reports three card-not-present charges to a foreign merchant they do not recognize, then a late-night SPEI transfer to a new beneficiary. Suspect account takeover, recommend freeze and card reissue."
2       CTA-300421 "Large outbound SPEI transfer to a new beneficiary, just under the internal reporting threshold. Structuring pattern? Needs AML review."
3       CTA-200311 "Customer disputed a recurring subscription charge. Confirmed merchant error, refunded, closed."
```

Free-text notes from analysts. These are the search corpus.

## Step 2, full-text search

```text
note_id account_id  rank
1       CTA-100240 0.0608
2       CTA-300421 0.0304
```

The query `to_tsquery('english', 'spei | takeover')` searches for either word. Note #1 matches on both
("SPEI transfer" and "account takeover"), so it ranks higher; note #2 matches on "SPEI" only. Notes #3
and #4 mention neither word, so they don't match. The rank score is a number proportional to relevance.
Try `'card | freeze | dispute'` to see other notes ranked.

## Step 3, fuzzy matching

```text
account_id       similarity
CTA-100234      1.000
CTA-100235      0.692
CTA-100240      0.571
CTA-100241      0.571
```

Accounts similar to "CTA-100234". The exact id scores 1.000; ids that share most of their characters
score lower but still match, which is what keeps a typo like "CTA-100243" close. [Trigram](../../docs/glossary.md)
similarity is the share of three-character chunks two strings have in common. Results are sorted by
similarity, highest first.

## Step 4, GIN index

```text
CREATE INDEX idx_case_note_fts ON bank.case_note USING gin(to_tsvector('english', writeup));
```

Index is created. Subsequent full-text search queries will use it. On small datasets (< 10k rows),
the index overhead might outweigh the benefit, so the planner may still choose a sequential scan.
On large datasets (millions of notes), the index is essential.

## Step 5, hybrid search (explained, not run)

```text
Hybrid search (keyword + semantic) requires pgvector for embeddings.
You have now mastered FTS (full-text search) and fuzzy matching (pg_trgm).
Those two approaches cover most production search use cases.
```

This journey doesn't run a hybrid query; the cell only explains it. Hybrid search blends the
full-text rank from Step 2 with a vector similarity score (see *Vector Similarity Search*), weighted
to taste, and needs an embedding on each case note.

## The numbers that matter

| What | Expected | Why it matters |
| ---- | -------- | -------------- |
| [Full-text search](../../docs/glossary.md) query (100 notes) | < 10 ms | fast ranking by relevance |
| Fuzzy match (8 accounts) | < 5 ms | fast typo-tolerant search |
| [GIN](../../docs/glossary.md) index creation | instant (small dataset) | cheap to build; huge speedup at scale |

> **From the field**
> [Full-text search](../../docs/glossary.md) is the unsung hero of many apps. You write a full-text search query once, index it, and it scales to millions of documents. Fuzzy matching ([pg_trgm](../../docs/glossary.md)) is simpler than it sounds and catches real typos in user input. Hybrid search (blending keyword and semantic) is a recent addition (with [pgvector](../../docs/glossary.md)) and can produce surprisingly good results with modest tuning.
