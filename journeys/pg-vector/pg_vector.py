#!/usr/bin/env python3
"""Operational vectors — pgvector for similarity search on live data.

Demonstrates pgvector on Lakebase:
  1. Create pgvector extension
  2. Add embedding column to part table
  3. Populate embeddings (using deterministic hash; real systems use embedding model)
  4. Run similarity search query to find replacement parts
  5. Create HNSW index for faster lookups at scale

Usage:
    python pg_vector.py                    # run the whole story
    python pg_vector.py --step check       # check part table
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
# The shared Lakebase helper lives in common/scripts/. Make it importable
# from this journey folder no matter where you run the script from.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "common", "scripts"))
from lakebase import connect


def _hash_to_embedding(text: str, dim: int = 768) -> str:
    """Deterministic hash-based embedding (for reproducibility; real systems use embedding model).

    Returns a string representation of a vector suitable for Postgres vector type.
    """
    # Hash the text
    h = hashlib.sha256(text.encode()).digest()

    # Generate dim values from the hash (deterministic but varied)
    values = []
    for i in range(dim):
        # Use different bytes from the hash, cycling through it
        byte_idx = (i * 2) % len(h)
        # Convert byte to a float in [-1, 1]
        val = (struct.unpack("B", h[byte_idx : byte_idx + 1])[0] / 255.0) * 2 - 1
        # Add some variation based on the hash position
        variation = (i / dim) * 0.2  # +/- 0.1 variation
        val = max(-1, min(1, val + variation))
        values.append(f"{val:.4f}")

    return "[" + ",".join(values) + "]"


def check():
    """Check the part table."""
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT count(*) FROM factory.part")
            count = cur.fetchone()[0]
            cur.execute("SELECT part_id, name FROM factory.part LIMIT 5")
            parts = cur.fetchall()

    print(f"Checking part table:")
    print(f"  Total parts: {count}")
    print(f"  Sample parts:")
    for p in parts:
        print(f"    - {p[0]}: {p[1]}")
    print()


def create_extension():
    """Create the pgvector extension."""
    print(f"Creating pgvector extension:")
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute("CREATE EXTENSION IF NOT EXISTS vector")
            print(f"  Extension 'vector' created")
    print()


def add_embedding_column():
    """Add embedding column to the part table."""
    print(f"Adding embedding column (768-dim):")
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute("ALTER TABLE factory.part ADD COLUMN IF NOT EXISTS embedding vector(768)")
            print(f"  Column 'embedding' added to factory.part")
    print()


def populate_embeddings():
    """Populate embeddings for all parts."""
    print(f"Populating embeddings:")
    with connect() as conn:
        with conn.cursor() as cur:
            # Get all parts
            cur.execute("SELECT part_id, name, spec FROM factory.part ORDER BY part_id")
            parts = cur.fetchall()

            print(f"  Embedding {len(parts)} parts:")
            for part_id, name, spec in parts:
                # Create embedding from part name + spec (if spec is not None)
                spec_str = spec if spec else "{}"
                text_to_embed = f"{name} {spec_str}"
                embedding_str = _hash_to_embedding(text_to_embed)

                # Update the part row
                cur.execute(
                    f"UPDATE factory.part SET embedding = %s::vector(768) WHERE part_id = %s",
                    [embedding_str, part_id],
                )
                print(f"    {part_id}: embedded")

    print()


def search():
    """Run similarity search for replacement parts."""
    print(f"Running similarity search:")

    # Reference part
    ref_part_id = "PT-BEARING-6204"

    with connect() as conn:
        with conn.cursor() as cur:
            # Get the embedding of the reference part
            cur.execute(
                f"SELECT embedding FROM factory.part WHERE part_id = %s", [ref_part_id]
            )
            ref_row = cur.fetchone()
            if not ref_row or ref_row[0] is None:
                print(f"  Reference part {ref_part_id} not found or has no embedding")
                return

            # Query for similar parts (excluding the reference itself)
            cur.execute(
                f"""SELECT part_id, name, part_type,
                      1 - (embedding <=> %s::vector(768)) AS similarity
                   FROM factory.part
                   WHERE embedding IS NOT NULL AND part_id != %s
                   ORDER BY similarity DESC LIMIT 5""",
                [ref_row[0], ref_part_id],
            )
            similar_parts = cur.fetchall()

    print(f"  Reference part: {ref_part_id}")
    print(f"  Top 5 similar parts:")
    for i, (part_id, name, part_type, similarity) in enumerate(similar_parts, 1):
        print(f"    {i}. {part_id}: similarity={similarity:.2f} ({name})")
    print()


def create_index():
    """Create an HNSW index on the embedding column."""
    print(f"Creating HNSW index:")
    with connect() as conn:
        with conn.cursor() as cur:
            # Check if index already exists
            cur.execute(
                """SELECT indexname FROM pg_indexes
                   WHERE tablename='part' AND indexname LIKE '%embedding%'"""
            )
            if cur.fetchone():
                print(f"  Index already exists")
            else:
                cur.execute(
                    "CREATE INDEX ON factory.part USING hnsw (embedding vector_cosine_ops)"
                )
                print(f"  HNSW index created on embedding column")
    print()


def main():
    ap = argparse.ArgumentParser(
        description="Operational vectors — pgvector for similarity search"
    )
    ap.add_argument(
        "--step",
        choices=["check", "extend", "embed", "search", "index"],
        help="Run just one step (default: run all)",
    )
    args = ap.parse_args()

    if args.step == "check":
        check()
        return
    if args.step == "extend":
        create_extension()
        return
    if args.step == "embed":
        populate_embeddings()
        return
    if args.step == "search":
        search()
        return
    if args.step == "index":
        create_index()
        return

    # Full story
    print("Operational vectors — pgvector journey\n")
    check()
    create_extension()
    add_embedding_column()
    populate_embeddings()
    search()
    create_index()
    print("Done. Single SQL query finds replacement parts by similarity, no network hop.")


if __name__ == "__main__":
    main()
