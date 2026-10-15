#!/usr/bin/env python3
"""Create, check, or reset YOUR personal zero-copy branch.

Your branch (LB_BRANCH, e.g. u-alex) is where every journey runs. It forks the
shared `production` branch copy-on-write, so creating it copies no data and a
whole room can each have their own without colliding.

Usage:
    python branch.py --create        # create u-<name> off production (idempotent), wait ACTIVE
    python branch.py --status        # show your branch's endpoint state + host
    python branch.py --reset         # drop and recreate your branch (fresh start), then reload bank
    python branch.py --delete        # drop your branch (leaves nothing behind)

Env: LB_PROFILE, LB_PROJECT, LB_BRANCH (see 00-setup/).
"""
from __future__ import annotations

import argparse
import os
import time

from databricks.sdk.service.postgres import Branch, BranchSpec
from databricks.sdk.common.types.fieldmask import FieldMask

from lakebase import client, branch_name, branch_endpoint, wait_active, _env, _t

PRODUCTION = "production"


def _project_branch() -> tuple[str, str]:
    return _env("LB_PROJECT", required=True), _env("LB_BRANCH", required=True)


def create(reload: bool = False) -> None:
    w = client()
    project, branch = _project_branch()
    # idempotent: only create if absent
    try:
        w.postgres.get_branch(name=branch_name(project, branch))
        print(_t(f"branch {branch} already exists", f"la rama {branch} ya existe"))
    except Exception:
        t0 = time.time()
        w.postgres.create_branch(
            parent=f"projects/{project}",
            branch=Branch(spec=BranchSpec(
                source_branch=branch_name(project, PRODUCTION), no_expiry=True)),
            branch_id=branch, replace_existing=False)
        ms = (time.time() - t0) * 1000
        print(_t(f"create_branch API returned in {ms:.0f} ms", f"la API create_branch respondió en {ms:.0f} ms"))
    waited = wait_active(w, project, branch)
    host, _, state = branch_endpoint(w, project, branch)
    print(_t(f"branch {branch} is {state} in ~{waited:.1f}s  (host {host})",
             f"la rama {branch} está {state} en ~{waited:.1f}s  (host {host})"))
    if reload:
        _reload_bank()


def status() -> None:
    w = client()
    project, branch = _project_branch()
    host, eid, state = branch_endpoint(w, project, branch)
    print(f"project={project} branch={branch}\n  endpoint={eid} state={state} host={host or '(none)'}")


def delete() -> None:
    w = client()
    project, branch = _project_branch()
    if branch == PRODUCTION:
        raise SystemExit(_t("refusing to delete the production branch", "no se puede eliminar la rama production"))
    # unprotect (best effort) then delete
    try:
        w.postgres.update_branch(
            name=branch_name(project, branch),
            branch=Branch(spec=BranchSpec(is_protected=False)),
            update_mask=FieldMask(field_mask=['spec.is_protected']))
    except Exception:
        pass
    w.postgres.delete_branch(name=branch_name(project, branch))
    print(_t(f"deleted branch {branch}", f"rama {branch} eliminada"))


def reset() -> None:
    delete()
    time.sleep(2)
    create(reload=True)


def _reload_bank() -> None:
    # import here so create/status don't require the SQL files
    from load_bank import main as load_main
    import sys
    sys.argv = ["load_bank.py"]
    load_main()


def main() -> None:
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--create", action="store_true")
    g.add_argument("--status", action="store_true")
    g.add_argument("--reset", action="store_true")
    g.add_argument("--delete", action="store_true")
    args = ap.parse_args()
    if args.create:
        create()
    elif args.status:
        status()
    elif args.reset:
        reset()
    elif args.delete:
        delete()


if __name__ == "__main__":
    main()
