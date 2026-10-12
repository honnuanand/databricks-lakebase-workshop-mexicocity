#!/usr/bin/env python3
"""Build a knowledge graph from the bank schema using RDF triples and rdflib.

Loads the holdings tree, the fund-to-branch bookings, and the counterparty
network from Lakebase into an in-memory RDF graph, then runs graph traversal
queries to show how linked finance data speaks for itself.

Usage:
    python kg_build.py                 # run full build + queries
    python kg_build.py --step load     # just load the graph
    python kg_build.py --step query    # load + query
    python kg_build.py --verbose       # show each triple as it is added
"""
from __future__ import annotations

import argparse
import os, sys
# The shared Lakebase helper lives in common/scripts/. Make it importable
# from this journey folder no matter where you run the script from.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "common", "scripts"))
from lakebase import connect

try:
    from rdflib import Graph, Namespace, URIRef, Literal
except ImportError:
    raise ImportError("rdflib not installed. Run: pip install rdflib")


def load_graph(verbose: bool = False):
    """Load the bank schema into an RDF graph.

    Returns (graph, stats) where stats is a dict of counts.
    """
    g = Graph()
    BANK = Namespace("http://bank.local/")

    stats = {
        "funds": 0,
        "instruments": 0,
        "holdings": 0,
        "counterparties": 0,
        "traded_by_edges": 0,
        "branches": 0,
        "booked_at_edges": 0,
    }

    with connect() as conn:
        with conn.cursor() as cur:
            # Load funds
            if verbose:
                print("Loading funds...")
            cur.execute("SELECT fund_id, name FROM bank.fund")
            for fund_id, name in cur.fetchall():
                g.add((URIRef(BANK[fund_id]), URIRef(BANK.name), Literal(name)))
                stats["funds"] += 1
                if verbose:
                    print(f"  +fund {fund_id}")

            # Load instruments
            if verbose:
                print("Loading instruments...")
            cur.execute("SELECT instrument_id, name, kind FROM bank.instrument")
            for instrument_id, name, kind in cur.fetchall():
                g.add((URIRef(BANK[instrument_id]), URIRef(BANK.name), Literal(name)))
                g.add((URIRef(BANK[instrument_id]), URIRef(BANK.kind), Literal(kind)))
                stats["instruments"] += 1
                if verbose:
                    print(f"  +instrument {instrument_id}")

            # Load holdings edges (parent holds child instrument/sleeve)
            if verbose:
                print("Loading holdings edges...")
            cur.execute("""
                SELECT parent_id, instrument_id, qty
                FROM bank.holding
                LIMIT 1000
            """)
            for parent_id, instrument_id, qty in cur.fetchall():
                g.add((
                    URIRef(BANK[parent_id]),
                    URIRef(BANK.holds),
                    URIRef(BANK[instrument_id])
                ))
                stats["holdings"] += 1
                if verbose:
                    print(f"  +edge {parent_id} holds {instrument_id}")

            # Load counterparties
            if verbose:
                print("Loading counterparties...")
            cur.execute("SELECT counterparty_id, name FROM bank.counterparty")
            for counterparty_id, name in cur.fetchall():
                g.add((URIRef(BANK[counterparty_id]), URIRef(BANK.name), Literal(name)))
                stats["counterparties"] += 1
                if verbose:
                    print(f"  +counterparty {counterparty_id}")

            # Load counterparty relationships (instrument traded_by counterparty)
            try:
                if verbose:
                    print("Loading counterparty edges...")
                cur.execute("""
                    SELECT instrument_id, counterparty_id
                    FROM bank.trade_counterparty
                    LIMIT 1000
                """)
                for instrument_id, counterparty_id in cur.fetchall():
                    g.add((
                        URIRef(BANK[instrument_id]),
                        URIRef(BANK.traded_by),
                        URIRef(BANK[counterparty_id])
                    ))
                    stats["traded_by_edges"] += 1
                    if verbose:
                        print(f"  +edge {instrument_id} traded_by {counterparty_id}")
            except Exception:
                # trade_counterparty may not exist; skip gracefully
                pass

            # Load branches and the fund-to-branch bookings (from the trade table)
            if verbose:
                print("Loading branches...")
            cur.execute("SELECT branch_id, name FROM bank.branch")
            for branch_id, name in cur.fetchall():
                g.add((URIRef(BANK[branch_id]), URIRef(BANK.name), Literal(name)))
                stats["branches"] += 1
                if verbose:
                    print(f"  +branch {branch_id}")

            if verbose:
                print("Loading fund booked_at branch edges...")
            cur.execute("SELECT DISTINCT fund_id, branch_id FROM bank.trade")
            for fund_id, branch_id in cur.fetchall():
                g.add((
                    URIRef(BANK[fund_id]),
                    URIRef(BANK.booked_at),
                    URIRef(BANK[branch_id])
                ))
                stats["booked_at_edges"] += 1
                if verbose:
                    print(f"  +edge {fund_id} booked_at {branch_id}")

    return g, stats


def query_holdings(g, fund_id: str) -> list[str]:
    """Query: which instruments does a fund hold directly (its direct children)?"""
    BANK = Namespace("http://bank.local/")
    fund_uri = URIRef(BANK[fund_id])

    instruments = []
    for obj in g.objects(fund_uri, URIRef(BANK.holds)):
        instrument_id = str(obj).split("/")[-1]
        instruments.append(instrument_id)

    return sorted(instruments)


def main() -> None:
    ap = argparse.ArgumentParser(description="Build a knowledge graph from the bank schema")
    ap.add_argument("--step", choices=["load", "query", "sql", "list-funds", "inspect"],
                    help="run a specific step")
    ap.add_argument("--verbose", action="store_true", help="print each triple")
    args = ap.parse_args()

    if args.step == "load" or not args.step:
        print("Loading graph...")
        g, stats = load_graph(verbose=args.verbose)
        print(f"Loaded {len(g)} triples:")
        for key, val in stats.items():
            if val > 0:
                print(f"  - {val} {key}")

        if args.step:
            return
    else:
        g, _ = load_graph(verbose=args.verbose)

    if args.step == "query" or not args.step:
        print("\nQuery: which instruments does FUND-GROWTH-A hold directly?")
        instruments = query_holdings(g, "FUND-GROWTH-A")
        for instrument in instruments:
            print(f"  {instrument}")

        if args.step:
            return

    if args.step == "sql" or not args.step:
        print("\nEquivalent SQL:")
        print("  SELECT instrument_id FROM bank.holding WHERE parent_id = 'FUND-GROWTH-A'")

        with connect() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT instrument_id FROM bank.holding WHERE parent_id = 'FUND-GROWTH-A'
                """)
                rows = cur.fetchall()
                print(f"  Result: {rows}")

    if args.step == "list-funds":
        print("Funds in graph:")
        funds = set()
        for subj in g.subjects():
            fund_id = str(subj).split("/")[-1]
            if fund_id.startswith("FUND-"):
                funds.add(fund_id)
        for fund_id in sorted(funds):
            print(f"  {fund_id}")

    if args.step == "inspect":
        print("Graph inspection:")
        print(f"  Triples: {len(g)}")
        print(f"  Subjects: {len(set(g.subjects()))}")
        print(f"  Predicates: {len(set(g.predicates()))}")
        print(f"  Objects: {len(set(g.objects()))}")


if __name__ == "__main__":
    main()
