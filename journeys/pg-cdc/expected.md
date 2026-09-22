# Your commits are a change feed, expected results

PREVIEW: Logical replication is on the Lakebase roadmap. This journey shows the Postgres capability;
exact output depends on permissions and instance setup.

## Setup

```text
Created machine_cdc_demo with 5 machines
```

## Create logical replication slot

```text
Created logical replication slot: workshop_slot
(If you see a permissions error, see the FAQ, logical decoding requires REPLICATION role.)
```

## Make writes and decode

If you have the necessary permissions (REPLICATION role):

```text
Current LSN: 0/XXXXXXXX

Making DML changes:
  INSERT M-100 (new machine)
  UPDATE M-001 (status changed to maintenance)
  DELETE M-003 (machine removed)

LSN after changes: 0/YYYYYYYY

Decoding changes from slot workshop_slot:
  LSN=0/XXXXXXXX: BEGIN
  LSN=0/XXXXXXXX: INSERT M-100 (operational)
  LSN=0/XXXXXXXX: COMMIT
  LSN=0/YYYYYYYY: BEGIN
  LSN=0/YYYYYYYY: UPDATE M-001 (status = maintenance)
  LSN=0/YYYYYYYY: COMMIT
  LSN=0/ZZZZZZZZ: BEGIN
  LSN=0/ZZZZZZZZ: DELETE M-003
  LSN=0/ZZZZZZZZ: COMMIT

Dropped replication slot: workshop_slot

✓ Logical decoding is roadmap on Lakebase.
  When GA: drive cache invalidation, outbox, downstream sync straight off the WAL.
```

## Full run (permission granted)

```text
PREVIEW: Logical replication/decoding is on the Lakebase roadmap.

1. Creating demo table:
Created machine_cdc_demo with 5 machines

2. Creating logical replication slot:
Created logical replication slot: workshop_slot

3. Making DML changes and decoding:
Current LSN: 0/XXXXXXXX

Making DML changes:
  INSERT M-100 (new machine)
  UPDATE M-001 (status changed to maintenance)
  DELETE M-003 (machine removed)

LSN after changes: 0/YYYYYYYY

Decoding changes from slot workshop_slot:
  (decoded records shown above)

4. Cleaning up:
Dropped replication slot: workshop_slot

✓ Logical decoding is roadmap on Lakebase.
  When GA: drive cache invalidation, outbox, downstream sync straight off the WAL.
```

## Full run (permission denied)

If you don't have REPLICATION role:

```text
PREVIEW: Logical replication/decoding is on the Lakebase roadmap.

1. Creating demo table:
Created machine_cdc_demo with 5 machines

2. Creating logical replication slot:
⚠ Could not create logical replication slot (may not have superuser perms): [error]
  Logical decoding is roadmap on Lakebase; this is a capability preview.

3. Making DML changes and decoding:
⚠ Error during CDC demo: [error]
  Logical replication/decoding is on the Lakebase roadmap (not GA yet).

✓ Logical decoding is roadmap on Lakebase.
  When GA: drive cache invalidation, outbox, downstream sync straight off the WAL.
```

## The numbers that matter

| What | Captured | Why it matters |
| ---- | --------- | -------------- |
| Logical slot | 1 | Durable cursor into the WAL; survives server restarts |
| LSN positions | per-record | Ordered, comparable across transactions |
| Record types | BEGIN/INSERT/UPDATE/DELETE/COMMIT | Exact transaction structure, decodable |
| No polling | native stream | Avoids load from repeated queries; changes are pushed not pulled |

> **From the field**
> Logical decoding is how change-data-capture (CDC) should work: native to the database, ordered,
> durable, no external pipeline. Lakebase will offer this; until GA, you can see it here as a
> Postgres capability. When available on Lakebase, this pattern powers cache invalidation, outbox
> transactional outbox, and downstream microservice sync, all driven straight off the WAL.
