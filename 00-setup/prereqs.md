# 1 · Prerequisites

A short checklist. If you already work in Databricks day to day, you likely have most of this.

## What you need

**A Databricks workspace you can log into**, on a workspace where Lakebase is available. You
need to be able to create (or have someone create) a Lakebase project, and to run SQL against
it. If your instructor gave you a workspace and a project name, you have this.

**The Databricks CLI**, version 1.6 or newer. Check:

```bash
databricks version
```

```text
Databricks CLI v1.6.0
```

If it's missing or older, install or upgrade it. On macOS:

```bash
brew tap databricks/tap && brew install databricks
# or upgrade:
brew upgrade databricks
```

Other platforms: see the install guide at <https://docs.databricks.com/en/dev-tools/cli/install.html>.

**Python 3.10 or newer**, with `pip`. Check:

```bash
python3 --version
```

**Two Python libraries**, the Databricks SDK (to drive projects and branches) and the Postgres
driver (to run SQL). Install them into a virtual environment so you don't disturb your system
Python:

```bash
python3 -m venv .venv
source .venv/bin/activate           # Windows: .venv\Scripts\activate
pip install "databricks-sdk==0.120.0" "psycopg[binary]==3.3.4"
```

> **Note**
> Pinning these versions matches what this workshop was built and tested against. Newer
> versions will usually work, but if a script behaves differently, pin to these first.

> **Tip**
> You don't need to know the SDK to start, but when a step calls `w.postgres.*` and you want to
> understand it, [`docs/lakebase-sdk.md`](../docs/lakebase-sdk.md) is a one-page reference for
> the Lakebase part of the Databricks SDK, with links to the official docs for the latest.

## Quick check

With the virtual environment active, this should print the versions with no errors:

```bash
python3 -c "import databricks.sdk, psycopg; print('sdk', databricks.sdk.version.__version__); print('psycopg', psycopg.__version__)"
```

```text
sdk 0.120.0
psycopg 3.3.4
```

If both print, you're ready for [`auth.md`](auth.md).

## If your machine blocks public PyPI

Some managed environments block public PyPI. If `pip install` can't reach it, install through
whatever package index your organization provides (ask your admin for the index URL), for
example:

```bash
pip install --index-url <your-org-package-index-url> "databricks-sdk==0.120.0" "psycopg[binary]==3.3.4"
```

---

Next: [`auth.md`](auth.md), log in to your workspace.
