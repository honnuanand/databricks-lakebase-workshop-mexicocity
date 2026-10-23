# No settlement overlap, expected results

Use this to check your run. The numbers here are from our measurements; yours will be close but not identical. The *shape* of the results and the general magnitudes are what matter.

## Step 1, inspect settlements

```text
settlement_id  account_id   starts_at                    ends_at
STL-1          CTA-100240  2024-01-15 14:00:00+00       2024-01-15 16:00:00+00
STL-2          CTA-100241  2024-01-15 15:00:00+00       2024-01-15 16:00:00+00
STL-3          CTA-200310  2024-01-15 14:30:00+00       2024-01-15 16:30:00+00
```

Settlements are scheduled on accounts with non-overlapping time windows. The times are relative to
when you loaded the bank (the seed uses `now()`), so yours will show today's date.

## Step 2, GiST exclusion constraint created

```text
CREATE EXTENSION IF NOT EXISTS btree_gist;
ALTER TABLE bank.settlement
  ADD CONSTRAINT no_account_overlap
  EXCLUDE USING gist (account_id WITH =, tstzrange(starts_at, ends_at) WITH &&);
```

The constraint is created silently. All existing settlements satisfy it (they don't overlap).

## Step 3, attempt to insert overlapping settlement

```text
ERROR: conflicting key value violates exclusion constraint "no_account_overlap"
DETAIL: Key (account_id, tstzrange(starts_at, ends_at))=(CTA-100240, ["2024-01-15 14:30:00+00","2024-01-15 15:30:00+00"]) conflicts with existing key.
```

The INSERT is rejected. The database prevents the overlap from ever existing.

## Step 4, EXPLAIN an insert

```text
Query plan (the exclusion check runs when the row is written, so it isn't listed here):
  Insert on settlement  (cost=0.00..0.36 rows=0 width=0)
    ->  Subquery Scan on "*SELECT*"  (cost=0.00..0.36 rows=1 width=148)
          ->  Limit  (cost=0.00..0.35 rows=1 width=148)
                ->  Seq Scan on settlement settlement_1  (cost=0.00..1.05 rows=3 width=148)
```

The plan only shows how the new row is produced. The exclusion constraint doesn't appear because
Postgres checks it when the row is written, using the constraint's GiST index; Step 3's rejected
insert is the proof. The app doesn't have to do anything: it tries the insert and gets an error if
there's a conflict.

## The numbers that matter

| What | Expected | Why it matters |
| ---- | -------- | -------------- |
| Constraint check overhead | < 1 ms | negligible on INSERT |
| Overlapping INSERT attempts | 100% rejected | no escape hatch; constraint is universal |
| Non-overlapping INSERTs | succeed | the constraint only blocks overlaps |
| Constraint enforcement | atomic | no race condition window |

> **From the field**
> Exclusion constraints are Postgres' answer to the settlement overlap problem that plagues many financial systems. They're not well-known (many engineers don't know they exist), but they solve a problem that typically requires careful app code. The database handles it correctly by default. This is the philosophy: make the database enforce the rules so the app doesn't have to.
