# common/ — the shared toolbox

This folder is **not a step in the workshop**. It holds the runnable pieces the journeys reach
for. You never "do the common folder"; a journey's `instructions.md` tells you when to run
something here.

- **`scripts/`** — Python and shell you invoke from a journey (or from `00-setup/`). Shared
  helpers live here too: connecting to your branch, provisioning, creating your branch,
  resetting it. Write the hard SDK logic once; many journeys call it.
- **`notebooks/`** — Databricks / Jupyter notebooks you import and run for journeys that read
  better as a notebook (data generation, the LTAP round trip, vector and graph work).

The path you actually walk is `00-setup/` → `journeys/` → the capstone. This folder is what
that path picks up along the way.
