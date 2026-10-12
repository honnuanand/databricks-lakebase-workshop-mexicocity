# Break it, then rewind, expected results

Use this to check your run. Timings are from our measurements on a warm project; yours will be close but not identical. The *shape* is what matters: sub-second API calls, recovery branch ACTIVE in a couple of seconds, deleted data restored unchanged.

## Step 1, trades before

```text
('TRD-8821', 'FUND-GROWTH-A', 50, 'placed')
('TRD-8822', 'FUND-INCOME-B', 120, 'executing')
```

## Step 2, LSN captured

```text
  LSN captured: 0/1A2B3C4D (example; your LSN will differ)
```

The LSN is the write-ahead log position at this moment. The script stores it to create the recovery branch at this same LSN after the delete.

## Step 3, delete runs

```text
  deleted: 0 trades and 0 settlements remain (all gone)
```

Both tables are now empty. The delete removes the `settlement` rows first, because they
reference `trade` by a foreign key, then the trades themselves. That is the kind of over-broad
cleanup this journey recovers from.

## Step 4, recover from PITR branch

```text
  PITR branch created: u-alex-restore
  recovery API returned in ~700 ms; endpoint ACTIVE in ~1.9s
  Recovered trades from PITR branch:
  ('TRD-8821', 'FUND-GROWTH-A', 50, 'placed')
  ('TRD-8822', 'FUND-INCOME-B', 120, 'executing')
  (2 trades, 3 settlements)
```

The recovery branch is created at the LSN from before the delete (via `source_branch_lsn`), so
both the trades and their settlements come back exactly as they were.

The recovered rows are identical to Step 1. The PITR branch reached ACTIVE in a couple of seconds, the same speed as any branch creation.

## Step 5, discard

```text
  discarded u-alex-restore
```

## Full run

Running `python break_and_rewind.py` with no arguments prints the whole story:

```text
1. Establish the data:
  trades on your branch:
  ('TRD-8821', 'FUND-GROWTH-A', 50, 'placed')
  ('TRD-8822', 'FUND-INCOME-B', 120, 'executing')
2. Capture LSN (before the mistake):
  LSN: 0/1A2B3C4D
3. Make the mistake (DELETE all trades):
  2 trades deleted
4. Recover via point-in-time restore:
  PITR branch created: u-alex-restore
  recovery API returned in ~700 ms; endpoint ACTIVE in ~2.3s
  Recovered trades from PITR branch:
  ('TRD-8821', 'FUND-GROWTH-A', 50, 'placed')
  ('TRD-8822', 'FUND-INCOME-B', 120, 'executing')
5. Discard the PITR branch:
  discarded u-alex-restore
Done. Trades recovered, branch deleted, zero storage left behind.
```

## The numbers that matter

| What | Expected | Why it matters |
| ---- | -------- | -------------- |
| `create_branch` with `source_branch_lsn` | under ~1s (about 700 ms) | copy-on-write metadata accept; branching at past LSN is as fast as branching at present |
| recovery branch endpoint ACTIVE | about 2 to 3s | attaching connectable compute |
| recovered data | identical to pre-delete | PITR is correct; every byte is as it was |
| recovery window | ~30 days | you can recover from a mistake days ago, not just seconds ago |

> **From the field**
> The honest number: creating a PITR branch (even to a past LSN) takes the same couple of seconds as creating a branch from now. The magic is that the page server holds enough history (typically 30 days) that you can branch at any LSN in that window. A traditional Postgres PITR means base backups + WAL replay, which takes minutes to hours. Lakebase PITR is branching, so it's seconds.
