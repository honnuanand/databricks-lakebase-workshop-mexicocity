# Branch the brain, instructions

Run these on your own branch. If you haven't done [`../../00-setup/`](../../00-setup/), do that
first; you need `LB_PROFILE`, `LB_PROJECT`, `LB_BRANCH`, and `LB_SCHEMA` set, and the factory
loaded.

Everything here is a single script you can read: [`./branch_the_brain.py`](./branch_the_brain.py).
You can run it end to end, or follow the steps by hand to see each piece.

## Run it end to end

```bash
cd journeys/branch-the-brain
python branch_the_brain.py
```

This walks the whole story and prints timings. Read on for what each step does; the exact output
to expect is in [`expected.md`](expected.md).

## Or step through it by hand

### Step 1, look at M-204 on your branch

```bash
python ../../common/scripts/lakebase.py --sql \
  "SELECT machine_id, status, health_pct FROM factory.machine WHERE machine_id='M-204'"
```

M-204 is `healthy`. This is the state you're about to fork.

### Step 2, fork your branch into an experiment branch

The experiment branch is a zero-copy fork of *your* branch. This uses the same
`w.postgres.create_branch` call you met in setup, with a source of your branch instead of
production. The script times how long until the fork's endpoint is `ACTIVE`:

```bash
python branch_the_brain.py --step fork
```

Watch the timing: the API returns in under a second, the endpoint is `ACTIVE` in about two
seconds. A full, independent copy of your factory, ready to query, in seconds.

### Step 3, diverge on the fork

Set M-204 to `derated` on the experiment branch only:

```bash
python branch_the_brain.py --step diverge
```

The script connects to the *fork* and runs:

```sql
UPDATE factory.machine SET status='derated', health_pct=70.0 WHERE machine_id='M-204';
```

Then reads M-204 back from the fork: it's now `derated`.

### Step 4, prove production (your branch) is untouched

```bash
python ../../common/scripts/lakebase.py --sql \
  "SELECT machine_id, status, health_pct FROM factory.machine WHERE machine_id='M-204'"
```

Still `healthy`, `91.0`. Your branch never changed. The divergence lives only on the fork. Two
live databases, forked moments ago, holding different facts about the same machine.

### Step 5, discard the fork

```bash
python branch_the_brain.py --step discard
```

The experiment branch is deleted. Zero storage left behind, your branch intact. Confirm it's
gone:

```bash
python branch_the_brain.py --step list
```

The experiment branch is no longer listed.

## What you just did

You forked a live database, changed data on the fork, proved the original was untouched, and
threw the fork away, all in seconds and all copy-on-write. Compare the timings you saw against
[`expected.md`](expected.md), and if anything went sideways, [`faq.md`](faq.md) has the common
causes.
