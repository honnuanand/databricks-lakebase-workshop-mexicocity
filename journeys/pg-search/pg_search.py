#!/usr/bin/env python3
"""Search, three ways, full-text, fuzzy, and hybrid ranking.

FTS (full-text search) with ts_rank, fuzzy matching with pg_trgm trigrams,
and hybrid blending of keyword + semantic signals (with pgvector).
"""
import argparse
import os, sys
# The shared Lakebase helper lives in common/scripts/. Make it importable
# from this journey folder no matter where you run the script from.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "common", "scripts"))
from lakebase import connect, run_sql

def run_fts():
    """Full-text search on case notes."""
    print("\n=== Step 2: Full-Text Search (FTS) ===")
    sql = """
    SELECT note_id, account_id,
           ts_rank(to_tsvector('english', writeup),
                   to_tsquery('english', 'spei | takeover')) as rank
      FROM bank.case_note
     WHERE to_tsvector('english', writeup) @@ to_tsquery('english', 'spei | takeover')
     ORDER BY rank DESC
     LIMIT 5;
    """
    rows = run_sql(sql)
    print(f"Case notes matching 'SPEI OR takeover', ranked by relevance:")
    for row in rows:
        print(f"  note_id={row[0]}, account_id={row[1]}, rank={row[2]}")

def run_fuzzy():
    """Fuzzy matching on account IDs using pg_trgm."""
    print("\n=== Step 3: Fuzzy Matching (pg_trgm) ===")

    # Enable pg_trgm
    with connect() as conn:
        with conn.cursor() as cur:
            try:
                cur.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
            except:
                pass

    # Find accounts similar to a sample account ID
    sample_accounts = run_sql("SELECT account_id FROM bank.account LIMIT 1")
    if not sample_accounts:
        print("  No accounts found")
        return

    sample_id = sample_accounts[0][0]

    # Note: the pg_trgm similarity operator is `%`; psycopg treats `%` as a
    # parameter marker, so it must be doubled to `%%` in a parameterized query.
    sql = f"""
    SELECT account_id,
           similarity(account_id, %s) as sim
      FROM bank.account
     WHERE account_id %% %s
     ORDER BY sim DESC
     LIMIT 5;
    """
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (sample_id, sample_id))
            rows = cur.fetchall()

    print(f"Accounts similar to '{sample_id}' (fuzzy match, typo-tolerant):")
    for row in rows:
        print(f"  {row[0]} (similarity={row[1]:.3f})")

def run_index():
    """Create GIN index on FTS column."""
    print("\n=== Step 4: GIN Index on FTS ===")
    sql = """
    CREATE INDEX IF NOT EXISTS idx_case_note_fts
      ON bank.case_note
      USING gin(to_tsvector('english', writeup));
    """
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute(sql)
    print("  GIN index created on bank.case_note(writeup)")
    print("  (Subsequent FTS queries will use the index)")

def run_hybrid():
    """Hybrid search: blend FTS and semantic similarity (requires pgvector)."""
    print("\n=== Step 5: Hybrid Search (Keyword + Semantic) ===")
    print("  (Hybrid search requires pgvector for embeddings)")
    print("  (Skipping if embeddings are not available)")
    # This would require embeddings; skip if not present

def run_end_to_end():
    """Run all steps end to end."""
    print("\n" + "="*60)
    print("SEARCH, THREE WAYS, FTS, FUZZY, HYBRID")
    print("="*60)

    print("\n=== Step 1: Inspect Case Notes ===")
    sql = "SELECT note_id, account_id, writeup FROM bank.case_note LIMIT 3"
    rows = run_sql(sql)
    print(f"Sample case notes:")
    for row in rows:
        writeup = (row[2][:60] + "...") if row[2] and len(row[2]) > 60 else row[2]
        print(f"  note_id={row[0]}, account_id={row[1]}")
        print(f"    '{writeup}'")

    run_fts()
    run_fuzzy()
    run_index()
    run_hybrid()

    print("\n" + "="*60)
    print("Done. See instructions.md for detailed explanations.")
    print("="*60)

def main():
    ap = argparse.ArgumentParser(description="Search: FTS, fuzzy, and hybrid ranking")
    ap.add_argument("--step", choices=["fts", "fuzzy", "index", "hybrid"],
                    help="Run a specific step (default: all)")
    args = ap.parse_args()

    if args.step == "fts":
        run_fts()
    elif args.step == "fuzzy":
        run_fuzzy()
    elif args.step == "index":
        run_index()
    elif args.step == "hybrid":
        run_hybrid()
    else:
        run_end_to_end()

if __name__ == "__main__":
    main()
