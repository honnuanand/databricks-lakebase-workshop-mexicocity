"""Capstone dashboard, FastAPI backend.

A minimal, real service that shows how an application connects to and reads from
the bank on Lakebase. The teaching point is the WIRING, not the app framework:

  - Local dev authenticates with your Databricks profile (LAKEBASE_PROFILE).
  - On Databricks Apps, the runtime injects the app's Service Principal creds, so
    WorkspaceClient() needs no profile. The same code path handles both.

Endpoints:
  GET /api/accounts            list accounts (direct SQL on Lakebase)
  GET /api/accounts/{id}       one account + its recent transactions
  GET /api/holdings/{fund_id}  explode a fund's holdings tree (recursive CTE)
  GET /api/casenotes?q=...     search analyst case notes (full-text search)
  GET /api/health              liveness + which identity/branch we're serving

Config comes from environment (see app.yaml for the deployed values):
  LAKEBASE_PROFILE   Databricks profile for LOCAL dev; unset on Databricks Apps
  LAKEBASE_PROJECT   the Lakebase project id
  LAKEBASE_BRANCH    the branch to serve (production, or a shared demo branch)
  LAKEBASE_SCHEMA    schema (default: bank)
"""
from __future__ import annotations

import os
from contextlib import contextmanager
from pathlib import Path

import psycopg
from psycopg.rows import dict_row
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from databricks.sdk import WorkspaceClient

PROFILE = os.getenv("LAKEBASE_PROFILE")          # None on Databricks Apps (SP creds injected)
PROJECT = os.getenv("LAKEBASE_PROJECT")
BRANCH = os.getenv("LAKEBASE_BRANCH", "production")
SCHEMA = os.getenv("LAKEBASE_SCHEMA", "bank")
PORT = int(os.getenv("PORT", "8000"))

app = FastAPI(title="Bank dashboard", version="1.0")

_client: WorkspaceClient | None = None


def client() -> WorkspaceClient:
    global _client
    if _client is None:
        _client = WorkspaceClient(profile=PROFILE) if PROFILE else WorkspaceClient()
    return _client


def _endpoint(w: WorkspaceClient):
    """(host, endpoint_id) for the branch's primary endpoint."""
    parent = f"projects/{PROJECT}/branches/{BRANCH}"
    eps = list(w.postgres.list_endpoints(parent=parent))
    if not eps:
        raise HTTPException(503, f"branch {BRANCH} has no endpoint")
    ep = eps[0]
    host = ep.status.hosts.host if ep.status and ep.status.hosts else None
    state = ep.status.current_state.value if ep.status and ep.status.current_state else "?"
    # An IDLE (scaled-to-zero) endpoint still has a host; connecting wakes it.
    if not host:
        raise HTTPException(503, f"branch {BRANCH} has no host yet (state={state})")
    return host, (ep.endpoint_id or "primary")


@contextmanager
def db():
    """A short-lived connection to the branch, using a fresh OAuth credential as
    the password. Works locally (profile) and on Databricks Apps (SP creds)."""
    if not PROJECT:
        raise HTTPException(500, "LAKEBASE_PROJECT is not set")
    w = client()
    host, eid = _endpoint(w)
    cred = w.postgres.generate_database_credential(
        endpoint=f"projects/{PROJECT}/branches/{BRANCH}/endpoints/{eid}")
    conn = psycopg.connect(
        host=host, port=5432, dbname="databricks_postgres",
        user=w.current_user.me().user_name, password=cred.token,
        sslmode="require", autocommit=True, row_factory=dict_row, connect_timeout=15)
    try:
        with conn.cursor() as cur:
            cur.execute(f"SET search_path TO {SCHEMA}, public")
        yield conn
    finally:
        conn.close()


def query(sql: str, params: list | None = None) -> list[dict]:
    with db() as conn, conn.cursor() as cur:
        cur.execute(sql, params or [])
        return cur.fetchall() if cur.description else []


@app.get("/api/health")
def health():
    w = client()
    return {"ok": True, "identity": w.current_user.me().user_name,
            "project": PROJECT, "branch": BRANCH, "schema": SCHEMA}


@app.get("/api/accounts")
def accounts():
    return query(
        "SELECT account_id, branch_id, line, type, status, health_pct "
        "FROM account ORDER BY account_id")


@app.get("/api/accounts/{account_id}")
def account(account_id: str):
    rows = query("SELECT * FROM account WHERE account_id = %s", [account_id])
    if not rows:
        raise HTTPException(404, f"no account {account_id}")
    txns = query(
        "SELECT ts, amount, anomaly_score, mcc, util_pct FROM txn "
        "WHERE account_id = %s ORDER BY ts DESC LIMIT 20", [account_id])
    return {"account": rows[0], "recent_transactions": txns}


@app.get("/api/holdings/{fund_id}")
def holdings(fund_id: str):
    """Explode a fund's holdings tree with a recursive CTE, the same
    look-through the pg-sql-parity journey teaches: a fund holds a sleeve, the
    sleeve holds instruments, so one query flattens the whole tree."""
    return query(
        """
        WITH RECURSIVE explode(parent_id, instrument_id, qty, depth) AS (
            SELECT parent_id, instrument_id, qty, 1 FROM holding WHERE parent_id = %s
          UNION ALL
            SELECT b.parent_id, b.instrument_id, b.qty, e.depth + 1
            FROM holding b JOIN explode e ON b.parent_id = e.instrument_id
        )
        SELECT e.depth, e.instrument_id, p.name, e.qty
        FROM explode e LEFT JOIN instrument p ON p.instrument_id = e.instrument_id
        ORDER BY e.depth, e.instrument_id
        """, [fund_id])


@app.get("/api/casenotes")
def casenotes(q: str = Query("", description="full-text search over case notes")):
    if q.strip():
        return query(
            "SELECT note_id, account_id, ts, writeup, "
            "ts_rank(to_tsvector('english', writeup), plainto_tsquery('english', %s)) AS rank "
            "FROM case_note "
            "WHERE to_tsvector('english', writeup) @@ plainto_tsquery('english', %s) "
            "ORDER BY rank DESC LIMIT 25", [q, q])
    return query(
        "SELECT note_id, account_id, ts, writeup FROM case_note "
        "ORDER BY ts DESC LIMIT 25")


# ---- serve the single-page UI (a static index.html, no build step) ----
_STATIC = Path(__file__).parent / "static"


@app.get("/")
def index():
    page = _STATIC / "index.html"
    if not page.is_file():
        return {"message": "UI not found; open /docs for the API"}
    return FileResponse(page)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=PORT, reload=bool(PROFILE))
