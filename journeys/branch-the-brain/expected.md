# Branch the brain, expected results

Use this to check your run. Timings are from our measurements on a warm project; yours will be
close but not identical. The *shape* is what matters: sub-second API calls, endpoint ACTIVE in a
couple of seconds, production unchanged.

## Step 1, M-204 before

```text
('M-204', 'healthy', Decimal('91.00'))
```

## Step 2, fork

```text
  fork API returned in ~700 ms; endpoint ACTIVE in ~2.4s
```

The API call is well under a second. The endpoint reaches ACTIVE in roughly 2 to 3 seconds. If
your first fork of a session is slower (cold), run it again; warm forks are consistently a
couple of seconds.

## Step 3, diverge on the fork

```text
  [fork after change] M-204: status=derated health=70.0
```

## Step 4, your branch is untouched

```text
('M-204', 'healthy', Decimal('91.00'))
```

Identical to Step 1. This is the whole point: the change lives only on the fork.

## Full run

Running `python branch_the_brain.py` with no arguments prints the whole story:

```text
1. Production (your branch) before:
  [your branch] M-204: status=healthy health=91.00
2. Forking u-alex -> u-alex-exp (zero-copy):
  fork API returned in ~700 ms; endpoint ACTIVE in ~2.4s
3. Diverge on the fork:
  [fork after change] M-204: status=derated health=70.0
4. Your branch is untouched:
  [your branch] M-204: status=healthy health=91.00
5. Discard the fork:
  discarded u-alex-exp
Done. Production untouched, fork gone, zero storage left behind.
```

## The numbers that matter

| What | Expected | Why it matters |
| ---- | -------- | -------------- |
| `create_branch` API | under ~1s (about 700 ms) | copy-on-write metadata accept; no data copied |
| fork endpoint ACTIVE | about 2 to 3s | attaching connectable compute |
| storage used by the fork | ~0 until you write | that's what "zero-copy" means |
| your branch after diverge | unchanged | isolation: the fork can't affect the source |

> **From the field**
> If someone insists branching should be "under 500 milliseconds end to end," that figure is the
> copy-on-write metadata step alone, not a database you can connect to. The honest, defensible
> claim is "ready in seconds," and the two-number breakdown above is why. An Aurora fast clone,
> by contrast, is typically minutes before first use.
