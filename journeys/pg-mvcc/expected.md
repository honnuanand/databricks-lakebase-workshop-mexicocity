# MVCC and the WAL, expected results

Use this to check your run. The numbers here are from our measurements; yours will be close but not identical. The *shape* of the results and the general magnitudes are what matter.

## Step 1, system columns before update

```text
machine_id  health_pct  xmin  xmax  ctid
M-204       91.00       1234  0     (0,5)
```

The row is alive: xmin=1234 (created by TID 1234), xmax=0 (not deleted), ctid=(0,5) (physical location: page 0, slot 5).

## Step 2, UPDATE and watch versioning

After UPDATE health_pct=50.0:

```text
-- Before:
machine_id  health_pct  xmin  xmax  ctid
M-204       91.00       1234  0     (0,5)

-- After:
machine_id  health_pct  xmin  xmax  ctid
M-204       50.00       1245  0     (0,7)
```

- `xmin` changed: 1234 → 1245 (new transaction)
- `ctid` changed: (0,5) → (0,7) (new physical location)
- The old version (health_pct=91, xmin=1234) is still on disk; its xmax is now set to 1245

The new version is alive (xmax=0); the old version is dead (xmax=1245).

## Step 3, dead tuples accumulate

After 10 UPDATEs:

```text
n_live_tup  n_dead_tup  last_vacuum
2507        9           <null or recent>
```

- `n_live_tup`: ~2507 (all rows in the machine table, or just the sample)
- `n_dead_tup`: 9 (the 9 old versions of M-204 that we UPDATEd)
- `last_vacuum`: NULL or a timestamp if VACUUM has run

The dead tuples accumulate until VACUUM cleans them up.

## Step 4, VACUUM reclaims space

After VACUUM:

```text
Before VACUUM:
n_live_tup  n_dead_tup
2507        9

After VACUUM:
n_live_tup  n_dead_tup
2507        0
```

- `n_dead_tup` drops to 0 (dead tuples are removed)
- `n_live_tup` stays the same (no rows were deleted, only old versions removed)
- Table size shrinks (the 9 dead versions occupied space; now reclaimed)

## Step 5, WAL position

```text
pg_current_wal_lsn
0/3F45AB20
```

The WAL log position advances with each transaction. Postgres uses this position to implement PITR (point-in-time restore): by replaying the WAL up to a specific LSN, you can recover the database to any point in time.

## The numbers that matter

| What | Expected | Why it matters |
| ---- | -------- | -------------- |
| xmin/xmax/ctid visibility | visible in SELECT | system columns expose the MVCC machinery |
| Dead tuples after 10 UPDATEs | ~9 | dead tuples accumulate until VACUUM |
| Dead tuples after VACUUM | 0 | VACUUM reclaims space |
| VACUUM time (small table) | < 100 ms | VACUUM is fast; run it regularly |
| Table size shrink (post-VACUUM) | ~10-20% (varies) | old versions occupied space; now reclaimed |

> **From the field**
> MVCC is the reason Postgres scales well under mixed read-write workloads. Because readers never block writers (they see snapshots), a table with a thousand concurrent readers and a hundred concurrent writers stays responsive. Every major database uses some form of versioning now (Oracle has UNDO, SQL Server has tempdb snapshots), but Postgres did it first and did it best. VACUUM is the price: if you run a billion transactions on the same row without ever vacuuming, the table will eventually bloat and need cleanup. But autovacuum (enabled by default) handles this automatically.
