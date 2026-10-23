"""Capstone: a fraud analyst console, FastAPI backend.

A small, real service on Lakebase that puts the App developers track together. Each tab of
the UI uses what one journey taught, on your own branch, and every endpoint returns the SQL
or REST call it ran so the page can show it:

  GET  /api/health                  Tab 1, your database: project, branch, endpoint, and who the app is (Part 1)
  GET  /api/search?q=&mode=...      Tab 2, search: keyword (BM25), semantic (vectors), hybrid (RRF), or compare (Lakebase Search)
  GET  /api/accounts/{id}           Tab 3, the account over the Data API (REST), its transactions over SQL (Data API)
  GET  /api/instruments?filter=...  Tab 4, instruments whose JSONB spec sheet contains a filter, with @> (JSONB)

On Databricks Apps, the runtime injects the app's service principal credentials, so
WorkspaceClient() needs no profile: the app reads your branch as its own identity, which
the capstone notebook granted. Locally, LAKEBASE_PROFILE signs in as you instead.

Config comes from environment (the notebook sets them at deploy time; see app.yaml):
  LAKEBASE_PROFILE   Databricks profile for LOCAL dev; unset on Databricks Apps
  LAKEBASE_PROJECT   your Lakebase project id, e.g. bank-alex-kim
  LAKEBASE_BRANCH    the branch to serve, e.g. u-alex-kim
  LAKEBASE_SCHEMA    schema (default: bank)
  EMBED_ENDPOINT     embedding model serving endpoint (default: databricks-gte-large-en)
"""
from __future__ import annotations

import json
import os
from contextlib import contextmanager
from pathlib import Path

import psycopg
import requests
from psycopg.rows import dict_row
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from databricks.sdk import WorkspaceClient

PROFILE = os.getenv("LAKEBASE_PROFILE")          # None on Databricks Apps (SP creds injected)
PROJECT = os.getenv("LAKEBASE_PROJECT")
BRANCH = os.getenv("LAKEBASE_BRANCH", "production")
SCHEMA = os.getenv("LAKEBASE_SCHEMA", "bank")
EMBED_ENDPOINT = os.getenv("EMBED_ENDPOINT", "databricks-gte-large-en")
PORT = int(os.getenv("PORT", "8000"))

app = FastAPI(title="Consola del analista de fraude", version="3.0")

_client: WorkspaceClient | None = None


def client() -> WorkspaceClient:
    global _client
    if _client is None:
        _client = WorkspaceClient(profile=PROFILE) if PROFILE else WorkspaceClient()
    return _client


def _primary_endpoint(w: WorkspaceClient):
    eps = list(w.postgres.list_endpoints(parent=f"projects/{PROJECT}/branches/{BRANCH}"))
    if not eps:
        raise HTTPException(503, f"la rama {BRANCH} no tiene endpoint")
    return eps[0]


def _endpoint(w: WorkspaceClient):
    """(host, endpoint_id) for the branch's primary endpoint."""
    ep = _primary_endpoint(w)
    host = ep.status.hosts.host if ep.status and ep.status.hosts else None
    # An IDLE (scaled-to-zero) endpoint still has a host; connecting wakes it.
    if not host:
        raise HTTPException(503, f"la rama {BRANCH} todavía no tiene host")
    return host, (ep.endpoint_id or "primary")


@contextmanager
def db():
    """A short-lived connection to the branch, with a fresh OAuth credential as the password."""
    if not PROJECT:
        raise HTTPException(500, "falta LAKEBASE_PROJECT")
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


def query(sql: str, params=None) -> list[dict]:
    try:
        with db() as conn, conn.cursor() as cur:
            cur.execute(sql, params or [])
            return cur.fetchall() if cur.description else []
    except (psycopg.errors.UndefinedTable, psycopg.errors.UndefinedObject,
            psycopg.errors.UndefinedFunction) as e:
        raise HTTPException(409, "Falta la tabla o los índices del recorrido Lakebase Search en esta rama. "
                                 f"Haz primero ese recorrido. ({str(e).splitlines()[0]})")


def embed(text: str) -> str | None:
    """The text's embedding as a Postgres vector literal, or None if the model can't be reached."""
    w = client()
    try:
        r = requests.post(f"{w.config.host}/serving-endpoints/{EMBED_ENDPOINT}/invocations",
                          headers=w.config.authenticate(), json={"input": [text]}, timeout=30)
        r.raise_for_status()
        return "[" + ",".join(f"{x:.6f}" for x in r.json()["data"][0]["embedding"]) + "]"
    except Exception:
        return None


def shown(sql: str, q: str | None = None) -> str:
    """The SQL as the page shows it: the question inlined, the 1,024-number vector abbreviated."""
    sql = sql.replace("%(v)s", "'<embedding de la pregunta: 1,024 números>'")
    if q is not None:
        sql = sql.replace("%(q)s", "'" + q.replace("'", "''") + "'")
    return "\n".join(line.rstrip() for line in sql.strip().splitlines())


# ---- Tab 1, Part 1: your project, branch, and endpoint ----

@app.get("/api/health")
def health():
    w = client()
    me = w.current_user.me()
    project = w.postgres.get_project(name=f"projects/{PROJECT}")
    branch = w.postgres.get_branch(name=f"projects/{PROJECT}/branches/{BRANCH}")
    ep = _primary_endpoint(w)
    es = ep.status
    return {
        "identity": {"name": me.display_name, "id": me.user_name},
        "project": {"id": PROJECT, "pg_version": project.status.pg_version, "owner": project.status.owner},
        "branch": {"id": BRANCH, "source": (branch.status.source_branch or "").rsplit("/", 1)[-1],
                   "size_mb": round((branch.status.logical_size_bytes or 0) / 1e6, 1)},
        "endpoint": {"id": ep.endpoint_id, "state": es.current_state.value if es.current_state else "?",
                     "host": es.hosts.host if es.hosts else None,
                     "cu": f"{es.autoscaling_limit_min_cu:g}–{es.autoscaling_limit_max_cu:g} CU",
                     "suspend_after_min": round(es.suspend_timeout_duration.seconds / 60) if es.suspend_timeout_duration else None},
        "schema": SCHEMA,
    }


# ---- Tab 2, Lakebase Search: keyword, semantic, and hybrid ----

BM25 = "writeup_tsv <@> to_bm25query(to_tsvector('english', %(q)s), 'search_note_bm25')"

KEYWORD = f"""
SELECT n.note_id, n.account_id, n.category, a.status AS account_status, n.writeup,
       {BM25} AS score
  FROM search_note n JOIN account a USING (account_id)
 WHERE n.category <> 'cleared'
 ORDER BY score
 LIMIT 10
"""

SEMANTIC = """
SELECT n.note_id, n.account_id, n.category, a.status AS account_status, n.writeup,
       n.embedding <=> %(v)s::vector AS distance
  FROM search_note n JOIN account a USING (account_id)
 WHERE n.category <> 'cleared' AND n.embedding IS NOT NULL
 ORDER BY distance
 LIMIT 10
"""

HYBRID = f"""
WITH v AS (SELECT note_id, RANK() OVER (ORDER BY d) AS rank FROM (
             SELECT note_id, embedding <=> %(v)s::vector AS d
               FROM search_note WHERE embedding IS NOT NULL ORDER BY d LIMIT 20) x),
     k AS (SELECT note_id, RANK() OVER (ORDER BY s) AS rank FROM (
             SELECT note_id, {BM25} AS s
               FROM search_note ORDER BY s LIMIT 20) y)
SELECT n.note_id, n.account_id, n.category, a.status AS account_status, n.writeup,
       v.rank AS vector_rank, k.rank AS keyword_rank,
       COALESCE(1.0 / (60 + v.rank), 0) + COALESCE(1.0 / (60 + k.rank), 0) AS rrf
  FROM search_note n
  JOIN account a USING (account_id)
  LEFT JOIN v USING (note_id)
  LEFT JOIN k USING (note_id)
 WHERE (v.note_id IS NOT NULL OR k.note_id IS NOT NULL)
   AND n.category <> 'cleared'
 ORDER BY rrf DESC, n.note_id
 LIMIT 10
"""

MODES = {"keyword": KEYWORD, "semantic": SEMANTIC, "hybrid": HYBRID}


def _run_mode(mode: str, q: str, vector: str | None) -> dict:
    sql = MODES[mode]
    if mode != "keyword" and vector is None:
        return {"mode": mode, "error": f"El endpoint de embeddings {EMBED_ENDPOINT} no responde, así que "
                                       "esta búsqueda no está disponible; la búsqueda por palabras sí funciona.",
                "sql": shown(sql, q), "results": []}
    return {"mode": mode, "sql": shown(sql, q), "results": query(sql, {"q": q, "v": vector})}


@app.get("/api/search")
def search(q: str = Query(..., min_length=1), mode: str = Query("hybrid", pattern="^(keyword|semantic|hybrid|compare)$")):
    vector = embed(q) if mode != "keyword" else None
    if mode == "compare":
        return {m: _run_mode(m, q, vector) for m in ("keyword", "semantic", "hybrid")}
    return _run_mode(mode, q, vector)


# ---- Tab 3, Data API: the account over REST, its transactions over SQL ----

_data_api_url: str | None = None


def data_api_url() -> str:
    global _data_api_url
    if _data_api_url is None:
        _data_api_url = client().postgres.get_data_api(
            name=f"projects/{PROJECT}/branches/{BRANCH}/databases/databricks-postgres/data-api").status.url
    return _data_api_url


TXNS = """
SELECT ts, amount, currency, channel, anomaly_score
  FROM txn
 WHERE account_id = %s
 ORDER BY ts DESC
 LIMIT 20
"""


@app.get("/api/accounts/{account_id}")
def account(account_id: str):
    w = client()
    url = f"{data_api_url()}/{SCHEMA}/account"
    r = requests.get(url, params={"account_id": f"eq.{account_id}"}, headers=w.config.authenticate(), timeout=20)
    if r.status_code != 200:
        raise HTTPException(502, f"la Data API respondió {r.status_code}: {r.text[:200]}")
    rows = r.json()
    if not rows:
        raise HTTPException(404, f"no existe la cuenta {account_id}")
    return {"account": rows[0],
            "rest": f"GET {url}?account_id=eq.{account_id}\nAuthorization: Bearer <token OAuth del service principal de la app>",
            "transactions": query(TXNS, [account_id]),
            "sql": shown(TXNS.replace("%s", "'" + account_id.replace("'", "''") + "'"))}


# ---- Tab 4, JSONB: instruments by their spec sheet ----

INSTRUMENTS = """
SELECT instrument_id, name, kind, spec
  FROM instrument
 WHERE spec @> %s::jsonb
 ORDER BY instrument_id
"""


@app.get("/api/instruments")
def instruments(filter: str = Query('{"sector": "tech"}')):
    try:
        wanted = json.loads(filter)
    except json.JSONDecodeError:
        wanted = None
    if not isinstance(wanted, dict):
        raise HTTPException(400, 'el filtro debe ser un objeto JSON, por ejemplo {"sector": "tech"}')
    doc = json.dumps(wanted)
    return {"results": query(INSTRUMENTS, [doc]),
            "sql": shown(INSTRUMENTS.replace("%s", "'" + doc.replace("'", "''") + "'"))}


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
