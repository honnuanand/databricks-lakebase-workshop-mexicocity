#!/usr/bin/env python3
"""Operational vectors, pgvector for similarity search on live data.

Demonstrates pgvector on Lakebase for banking:
  1. Create the pgvector extension
  2. Add an embedding column to the instrument table
  3. Populate embeddings (deterministic hash here; real systems use an embedding model)
  4. Run a similarity search to find comparable instruments (securities)
  5. Create an HNSW index for faster lookups at scale

Scenario: a portfolio manager wants the instruments most similar to a given holding,
to find substitutes or hedges. "Similar" is a judgement over the instrument's profile
(asset kind, sector, risk), not any single column, so it is a vector-similarity query,
run in the same transaction as the operational data, no separate vector store.

Usage:
    python pg_vector.py                    # run the whole story
    python pg_vector.py --step check       # check instrument table
    python pg_vector.py --step extend      # create pgvector extension
    python pg_vector.py --step embed       # populate embeddings
    python pg_vector.py --step search      # run similarity search
    python pg_vector.py --step index       # create HNSW index

Env: LB_PROFILE, LB_PROJECT, LB_BRANCH, LB_SCHEMA (see 00-setup/).
"""
from __future__ import annotations

import argparse
import hashlib
import struct

import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "common", "scripts"))
from lakebase import connect


def _hash_to_embedding(text: str, dim: int = 768) -> str:
    """Deterministic hash-based embedding (reproducible; real systems use an embedding model).
    Returns a string vector suitable for the Postgres vector type."""
    h = hashlib.sha256(text.encode()).digest()
    values = []
    for i in range(dim):
        byte_idx = (i * 2) % len(h)
        val = (struct.unpack("B", h[byte_idx:byte_idx + 1])[0] / 255.0) * 2 - 1
        variation = (i / dim) * 0.2
        val = max(-1, min(1, val + variation))
        values.append(f"{val:.4f}")
    return "[" + ",".join(values) + "]"


def check():
    """Check the instrument table."""
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT count(*) FROM bank.instrument")
            count = cur.fetchone()[0]
            cur.execute("SELECT instrument_id, name FROM bank.instrument LIMIT 5")
            rows = cur.fetchall()
    print("Checking instrument table:")
    print(f"  Total instruments: {count}")
    print("  Sample instruments:")
    for r in rows:
        print(f"    - {r[0]}: {r[1]}")
    print()


def create_extension():
    print("Creating pgvector extension:")
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute("CREATE EXTENSION IF NOT EXISTS vector")
            print("  Extension 'vector' created")
    print()


def add_embedding_column():
    print("Adding embedding column (768-dim):")
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute("ALTER TABLE bank.instrument ADD COLUMN IF NOT EXISTS embedding vector(768)")
            print("  Column 'embedding' added to bank.instrument")
    print()


def populate_embeddings():
    print("Populating embeddings:")
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT instrument_id, name, kind, spec FROM bank.instrument ORDER BY instrument_id")
            rows = cur.fetchall()
            print(f"  Embedding {len(rows)} instruments:")
            for instrument_id, name, kind, spec in rows:
                spec_str = spec if spec else "{}"
                text_to_embed = f"{name} {kind} {spec_str}"
                embedding_str = _hash_to_embedding(text_to_embed)
                cur.execute(
                    "UPDATE bank.instrument SET embedding = %s::vector(768) WHERE instrument_id = %s",
                    [embedding_str, instrument_id])
                print(f"    {instrument_id}: embedded")
    print()


def search():
    """Find the instruments most similar to a reference instrument."""
    print("Running similarity search:")
    ref_id = "INS-QTZL"   # a real seed instrument (Quetzal Tecnologia equity)
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT embedding FROM bank.instrument WHERE instrument_id = %s", [ref_id])
            ref = cur.fetchone()
            if not ref or ref[0] is None:
                print(f"  Reference instrument {ref_id} not found or has no embedding")
                return
            cur.execute(
                """SELECT instrument_id, name, kind,
                      1 - (embedding <=> %s::vector(768)) AS similarity
                   FROM bank.instrument
                   WHERE embedding IS NOT NULL AND instrument_id != %s
                   ORDER BY similarity DESC LIMIT 5""",
                [ref[0], ref_id])
            similar = cur.fetchall()
    print(f"  Reference instrument: {ref_id}")
    print("  Top comparable instruments:")
    for i, (instrument_id, name, kind, similarity) in enumerate(similar, 1):
        print(f"    {i}. {instrument_id}: similarity={similarity:.2f} ({name}, {kind})")
    print()


def create_index():
    """Create an HNSW index on the embedding column."""
    print("Creating HNSW index:")
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT indexname FROM pg_indexes
                   WHERE tablename='instrument' AND indexname LIKE '%embedding%'""")
            if cur.fetchone():
                print("  Index already exists")
            else:
                cur.execute("CREATE INDEX ON bank.instrument USING hnsw (embedding vector_cosine_ops)")
                print("  HNSW index created on embedding column")
    print()


def main():
    ap = argparse.ArgumentParser(description="Operational vectors, pgvector for similarity search")
    ap.add_argument("--step", choices=["check", "extend", "embed", "search", "index"])
    args = ap.parse_args()

    if args.step == "check": check(); return
    if args.step == "extend": create_extension(); return
    if args.step == "embed": populate_embeddings(); return
    if args.step == "search": search(); return
    if args.step == "index": create_index(); return

    print("Operational vectors, pgvector journey\n")
    check()
    create_extension()
    add_embedding_column()
    populate_embeddings()
    search()
    create_index()
    print("Done. A single SQL query finds comparable instruments by similarity, no network hop.")


if __name__ == "__main__":
    main()
