# common/ — the shared toolbox

This folder holds only what is **shared across journeys**. It is not a step in the workshop, and
it is not where a journey's own script lives. A journey's script or notebook belongs in that
journey's own folder, next to its README and instructions. Only genuinely common pieces live
here.

- **`scripts/`** — the shared helpers every journey (or `00-setup/`) reaches for:
  - `lakebase.py` — connect to your branch and run SQL. Journey scripts import from this.
  - `provision.py` — provision a Lakebase project (used by `00-setup/`).
  - `branch.py` — create, check, reset, or delete your branch (used by `00-setup/`).
  - `load_factory.py` — load the factory schema and seed onto your branch.
  - `factory_schema.sql` / `factory_seed.sql` — the running-example schema and data.
- **`notebooks/`** — any notebook shared across journeys. A notebook specific to one journey
  lives in that journey's folder instead.

A journey's own runnable artifact (for example `journeys/pg-vector/pg_vector.py`) sits in the
journey folder and imports the shared helper from here with a small path bootstrap at the top of
the file. That keeps each journey self-contained: everything you need for it is in one folder,
and this toolbox holds only the pieces that truly belong to all of them.
