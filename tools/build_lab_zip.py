#!/usr/bin/env python3
"""Build the lab ZIP that Vocareum extracts into each attendee's workspace folder.

Packs only what the workshop path needs (START_HERE, setup, the 9 journeys of
Part 1 and the App developers track in English and Spanish, the shared scripts,
the Lakebase Search notes, the capstone app, and the glossaries)
under one top-level folder, keeping the repo's layout: the notebooks find
common/scripts and each other through relative paths. Files come from git, so
nothing untracked ends up in the ZIP. Then it checks the ZIP: every notebook
has the Databricks source header and every $./ or $../ link points to a
notebook inside it.

Usage:
    python tools/build_lab_zip.py                      # writes dist/lakebase-workshop-mx.zip
    python tools/build_lab_zip.py --out /tmp/lab.zip   # somewhere else

In Vocareum: Lab Content -> Individual files -> ADD FILES (the ZIP) or ADD FOLDER
(the unzipped lakebase-workshop/ folder); Entry Notebook lakebase-workshop/START_HERE_es.
"""
from __future__ import annotations

import argparse
import pathlib
import posixpath
import re
import subprocess
import sys
import zipfile

REPO = pathlib.Path(__file__).resolve().parent.parent
TOP = "lakebase-workshop"
NOTEBOOK_HEADER = "# Databricks notebook source"

JOURNEYS = [
    # Part 1
    "branch-the-brain", "break-and-rewind", "write-to-analytics", "scale-to-zero", "pg-integration",
    # Part 2, App developers
    "pg-json", "lakebase-search", "data-api", "capstone-app",
]
FILES = [
    "START_HERE.py", "START_HERE_es.py",
    "00-setup/setup_databricks.py", "00-setup/setup_databricks_es.py",
    "common/scripts/lakebase.py", "common/scripts/branch.py", "common/scripts/project.py",
    "common/scripts/load_bank.py", "common/scripts/finance_schema.sql", "common/scripts/finance_seed.sql",
    "docs/glossary.md", "docs/glosario-es.md",
    "journeys/lakebase-search/search_notes.sql",   # the 40 notes Lakebase Search loads
]
# The capstone deploys this folder as the app's source code; the shell scripts are laptop-only.
APP_DIR = "journeys/capstone-app/app/"
APP_EXCLUDE = {"deploy.sh", "run_local.sh"}

LINK = re.compile(r'href="\$(\.{1,2}/[^"#]+)"')


def tracked_files() -> set[str]:
    out = subprocess.run(["git", "ls-files"], cwd=REPO, capture_output=True, text=True, check=True).stdout
    return set(out.split())


def select(tracked: set[str]) -> list[str]:
    wanted = list(FILES)
    for j in JOURNEYS:
        nbs = [f for f in tracked if re.fullmatch(rf"journeys/{j}/[a-z_]+_databricks(_es)?\.py", f)]
        if len(nbs) != 2:
            raise SystemExit(f"journeys/{j}: expected an English and a Spanish notebook, found {sorted(nbs)}")
        wanted += nbs
    wanted += [f for f in tracked if f.startswith(APP_DIR) and posixpath.basename(f) not in APP_EXCLUDE]
    missing = [f for f in wanted if f not in tracked]
    if missing:
        raise SystemExit(f"not tracked in git: {missing}")
    return sorted(set(wanted))


def check(files: list[str]) -> list[str]:
    """Return problems: notebooks without the source header, links to notebooks not in the ZIP."""
    problems = []
    present = set(files)
    for f in files:
        if not f.endswith(".py") or f.startswith(("common/", APP_DIR)):
            continue
        text = (REPO / f).read_text()
        if not text.startswith(NOTEBOOK_HEADER):
            problems.append(f"{f}: missing '{NOTEBOOK_HEADER}'")
        for link in LINK.findall(text):
            target = posixpath.normpath(posixpath.join(posixpath.dirname(f), link)) + ".py"
            if target not in present:
                problems.append(f"{f}: link {link} -> {target} is not in the ZIP")
    return problems


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(REPO / "dist" / "lakebase-workshop-mx.zip"))
    args = ap.parse_args()

    files = select(tracked_files())
    problems = check(files)
    if problems:
        print("\n".join(problems))
        raise SystemExit(f"{len(problems)} problem(s); the ZIP was not written")

    out = pathlib.Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for f in files:
            z.write(REPO / f, f"{TOP}/{f}")
    notebooks = sum(1 for f in files if f.endswith(".py") and not f.startswith(("common/", APP_DIR)))
    print(f"wrote {out} ({out.stat().st_size // 1024} KB): {len(files)} files, {notebooks} notebooks")
    print(f"Entry Notebook: {TOP}/START_HERE_es")


if __name__ == "__main__":
    sys.exit(main())
