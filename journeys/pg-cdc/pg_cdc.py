#!/usr/bin/env python3
"""Change feed: logical decoding (roadmap on Lakebase, Postgres capability preview).

Tap the commit log itself: every INSERT/UPDATE/DELETE emerges as an ordered,
LSN-stamped change feed via logical decoding + test_decoding.

NOTE: Logical replication is on the Lakebase roadmap (not GA yet).
This journey previews the capability against a Postgres instance.

Usage:
    python pg_cdc.py                    # run the whole preview
    python pg_cdc.py --step setup       # create demo table
    python pg_cdc.py --step slot        # create logical replication slot
    python pg_cdc.py --step changes     # make writes and decode them

Env: LB_PROFILE, LB_PROJECT, LB_BRANCH, LB_SCHEMA (see 00-setup/).
"""
from __future__ import annotations

import argparse

import psycopg
import os, sys
# The shared Lakebase helper lives in common/scripts/. Make it importable
# from this journey folder no matter where you run the script from.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "common", "scripts"))
from lakebase import connect, _env

DEMO_TABLE = "account_cdc_demo"
SLOT_NAME = "workshop_slot"


def setup(conn):
    """Create a demo table."""
    schema = _env("LB_SCHEMA", "bank")

    with conn.cursor() as cur:
        # Drop if exists
        cur.execute(f"DROP TABLE IF EXISTS {schema}.{DEMO_TABLE} CASCADE")

        cur.execute(f"""
            CREATE TABLE {schema}.{DEMO_TABLE} (
                account_id TEXT PRIMARY KEY,
                status TEXT NOT NULL,
                health_pct NUMERIC(5,2)
            )
        """)

        # Seed with 5 accounts
        cur.execute(f"""
            INSERT INTO {schema}.{DEMO_TABLE}(account_id, status, health_pct)
            VALUES
                ('ACCT-001', 'good_standing', 95.5),
                ('ACCT-002', 'good_standing', 92.0),
                ('ACCT-003', 'frozen', 50.0),
                ('ACCT-004', 'good_standing', 98.2),
                ('ACCT-005', 'watch', 87.3)
        """)

        print(f"Created {schema}.{DEMO_TABLE} with 5 accounts")


def create_slot(conn):
    """Create a logical replication slot (prerequisite for decoding)."""
    with conn.cursor() as cur:
        # Drop slot if it exists
        try:
            cur.execute(f"DROP REPLICATION SLOT {SLOT_NAME}")
        except psycopg.Error:
            pass

        # Create a logical replication slot with test_decoding
        try:
            cur.execute(f"CREATE_REPLICATION_SLOT {SLOT_NAME} LOGICAL test_decoding")
            print(f"Created logical replication slot: {SLOT_NAME}")
        except psycopg.Error as e:
            print(f"⚠ Could not create logical replication slot (may not have superuser perms): {e}")
            print("  Logical decoding is roadmap on Lakebase; this is a capability preview.")


def make_changes_and_decode(conn):
    """Make some writes (INSERT/UPDATE/DELETE) and decode them from the slot."""
    schema = _env("LB_SCHEMA", "bank")

    with conn.cursor() as cur:
        try:
            # Get current LSN position before changes
            cur.execute("SELECT pg_current_wal_lsn()")
            start_lsn = cur.fetchone()[0]
            print(f"\nCurrent LSN: {start_lsn}")

            # Make some DML changes
            print(f"\nMaking DML changes:")

            # Insert a new account
            cur.execute(f"INSERT INTO {schema}.{DEMO_TABLE} VALUES ('ACCT-100', 'good_standing', 99.5)")
            print(f"  INSERT ACCT-100 (new account)")

            # Update an existing account
            cur.execute(f"UPDATE {schema}.{DEMO_TABLE} SET status='frozen' WHERE account_id='ACCT-001'")
            print(f"  UPDATE ACCT-001 (status changed to frozen)")

            # Delete an account
            cur.execute(f"DELETE FROM {schema}.{DEMO_TABLE} WHERE account_id='ACCT-003'")
            print(f"  DELETE ACCT-003 (account closed/removed)")

            # Get the new LSN after changes
            cur.execute("SELECT pg_current_wal_lsn()")
            end_lsn = cur.fetchone()[0]
            print(f"\nLSN after changes: {end_lsn}")

            # Try to decode changes from the slot
            print(f"\nDecoding changes from slot {SLOT_NAME}:")
            try:
                cur.execute(f"SELECT lsn, data FROM pg_logical_slot_get_changes(%s, NULL, NULL)", [SLOT_NAME])
                changes = cur.fetchall()
                if changes:
                    for lsn, data in changes:
                        print(f"  LSN={lsn}: {data[:80]}...")
                else:
                    print("  (No changes decoded; may require additional permissions or setup)")
            except psycopg.Error as e:
                print(f"  ⚠ Could not decode changes: {e}")
                print(f"    Logical decoding requires REPLICATION role; this is a Postgres capability.")

        except psycopg.Error as e:
            print(f"⚠ Error during CDC demo: {e}")
            print(f"  Logical replication/decoding is on the Lakebase roadmap (not GA yet).")


def cleanup(conn):
    """Drop the logical replication slot."""
    with conn.cursor() as cur:
        try:
            cur.execute(f"DROP REPLICATION SLOT {SLOT_NAME}")
            print(f"Dropped replication slot: {SLOT_NAME}")
        except psycopg.Error:
            pass  # Slot may not exist or may require special cleanup


def main():
    ap = argparse.ArgumentParser(description="Change feed via logical decoding (roadmap preview)")
    ap.add_argument(
        "--step",
        choices=["setup", "slot", "changes"],
        help="run a specific step",
    )
    args = ap.parse_args()

    with connect() as conn:
        if args.step == "setup":
            setup(conn)
        elif args.step == "slot":
            setup(conn)
            create_slot(conn)
        elif args.step == "changes":
            setup(conn)
            create_slot(conn)
            make_changes_and_decode(conn)
            cleanup(conn)
        else:
            # Run the whole story
            print("PREVIEW: Logical replication/decoding is on the Lakebase roadmap.")
            print("\n1. Creating demo table:")
            setup(conn)
            print("\n2. Creating logical replication slot:")
            create_slot(conn)
            print("\n3. Making DML changes and decoding:")
            make_changes_and_decode(conn)
            print("\n4. Cleaning up:")
            cleanup(conn)
            print("\n✓ Logical decoding is roadmap on Lakebase.")
            print("  When GA: drive cache invalidation, outbox, AML/fraud ledger sync straight off the WAL.")


if __name__ == "__main__":
    main()
