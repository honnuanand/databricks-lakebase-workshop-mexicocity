# No double-booking, expected results

Use this to check your run. The numbers here are from our measurements; yours will be close but not identical. The *shape* of the results and the general magnitudes are what matter.

## Step 1, inspect operations

```text
op_id  machine_id  starts_at                    ends_at
OP-1   M-204       2024-01-15 14:00:00+00       2024-01-15 15:00:00+00
OP-2   M-204       2024-01-15 16:00:00+00       2024-01-15 17:00:00+00
OP-3   M-301       2024-01-15 14:30:00+00       2024-01-15 16:30:00+00
```

Operations are scheduled on machines with non-overlapping time windows.

## Step 2, GiST exclusion constraint created

```text
CREATE EXTENSION IF NOT EXISTS btree_gist;
ALTER TABLE factory.operation
  ADD CONSTRAINT no_machine_overlap
  EXCLUDE USING gist (machine_id WITH =, tstzrange(starts_at, ends_at) WITH &&);
```

The constraint is created silently. All existing operations satisfy it (they don't overlap).

## Step 3, attempt to insert overlapping operation

```text
ERROR: conflicting key value violates exclusion constraint "no_machine_overlap"
DETAIL: Key (machine_id, tstzrange(starts_at, ends_at))=(M-204, ["2024-01-15 14:30:00+00","2024-01-15 15:30:00+00"]) conflicts with existing key.
```

The INSERT is rejected. The database prevents the overlap from ever existing.

## Step 4, EXPLAIN shows GiST check

```text
Insert on operation  (cost=0.31..0.37 rows=0 width=0)
  Conflict Arbiter Indexes: no_machine_overlap
```

The plan shows the exclusion constraint is checked (Conflict Arbiter). This happens automatically; the app just tries to insert and gets an error if there's a conflict.

## The numbers that matter

| What | Expected | Why it matters |
| ---- | -------- | -------------- |
| Constraint check overhead | < 1 ms | negligible on INSERT |
| Overlapping INSERT attempts | 100% rejected | no escape hatch; constraint is universal |
| Non-overlapping INSERTs | succeed | the constraint only blocks overlaps |
| Constraint enforcement | atomic | no race condition window |

> **From the field**
> Exclusion constraints are Postgres' answer to the "double-booking" problem that plagues many systems. They're not well-known (many engineers don't know they exist), but they solve a problem that typically requires careful app code. The database handles it correctly by default. This is the philosophy: make the database enforce the rules so the app doesn't have to.
