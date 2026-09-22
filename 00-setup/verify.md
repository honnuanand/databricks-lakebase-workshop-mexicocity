# 6 · Verify

One last check that everything is wired up, then you're ready for the journeys.

## Connect and run SELECT 1

```bash
python ../common/scripts/lakebase.py --check
```

```text
branch OK, SELECT 1 -> 1
```

If you see `1`, your environment can authenticate, resolve your branch's endpoint, generate a
credential, and run SQL. That's the whole chain the journeys depend on.

## Look at your factory

Run a real query against the seeded data:

```bash
python ../common/scripts/lakebase.py --sql \
  "SELECT plant_id, count(*) AS machines FROM factory.machine GROUP BY plant_id ORDER BY plant_id"
```

```text
('PL-AUSTIN', 2)
('PL-DETROIT', 4)
('PL-MUNICH', 2)
```

Three plants, eight machines. That's the smart factory you'll spend the rest of the workshop
branching, breaking, querying, and reasoning over.

## Troubleshooting

> **Warning**
> **"refresh token" / authentication error:** your login expired. Re-run the `databricks auth
> login` command from [`auth.md`](auth.md).

> **Note**
> **"branch has no endpoint host yet":** the branch is still provisioning, or wasn't created. Run
> `python ../common/scripts/branch.py --status` to see its state, and `--create` if it's missing.

> **Note**
> **"Missing required env var LB_PROJECT / LB_BRANCH":** you're in a fresh terminal that didn't
> load your env. Run `source workshop.env` (or re-export the variables from
> [`your-branch.md`](your-branch.md)).

## You're ready

Head to [`../journeys/`](../journeys/) and start with
[**Branch the brain**](../journeys/branch-the-brain/), the same branching you just did, turned
into your first hands-on journey.
