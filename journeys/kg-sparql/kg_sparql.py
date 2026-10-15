#!/usr/bin/env python3
"""Query a knowledge graph with SPARQL.

Builds the graph from the bank schema, then runs SPARQL queries
and compares them to equivalent SQL.

Usage:
    python kg_sparql.py                        # full queries
    python kg_sparql.py --step simple-query    # just simple query
    python kg_sparql.py --step multi-hop       # multi-hop query
    python kg_sparql.py --step sql             # SQL comparison
    python kg_sparql.py --step aggregate       # aggregation query
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


def load_graph() -> Graph:
    """Load the bank schema into an RDF graph."""
    g = Graph()
    BANK = Namespace("http://bank.local/")

    with connect() as conn:
        with conn.cursor() as cur:
            # Load funds, instruments
            cur.execute("SELECT fund_id, name FROM bank.fund")
            for fund_id, name in cur.fetchall():
                g.add((URIRef(BANK[fund_id]), URIRef(BANK.name), Literal(name)))

            cur.execute("SELECT instrument_id, name FROM bank.instrument")
            for instrument_id, name in cur.fetchall():
                g.add((URIRef(BANK[instrument_id]), URIRef(BANK.name), Literal(name)))

            # Load holdings edges (parent holds child instrument/sleeve)
            cur.execute("SELECT parent_id, instrument_id FROM bank.holding LIMIT 1000")
            for parent_id, instrument_id in cur.fetchall():
                g.add((
                    URIRef(BANK[parent_id]),
                    URIRef(BANK.holds),
                    URIRef(BANK[instrument_id])
                ))

            # Load counterparties
            cur.execute("SELECT counterparty_id, name FROM bank.counterparty")
            for counterparty_id, name in cur.fetchall():
                g.add((URIRef(BANK[counterparty_id]), URIRef(BANK.name), Literal(name)))

            # Load counterparty edges (if trade_counterparty exists)
            try:
                cur.execute("SELECT instrument_id, counterparty_id FROM bank.trade_counterparty LIMIT 1000")
                for instrument_id, counterparty_id in cur.fetchall():
                    g.add((
                        URIRef(BANK[instrument_id]),
                        URIRef(BANK.traded_by),
                        URIRef(BANK[counterparty_id])
                    ))
            except Exception:
                pass

    return g


def simple_query(g: Graph) -> list[str]:
    """SPARQL query: which instruments does FUND-GROWTH-A hold directly?"""
    query_text = """
        PREFIX bank: <http://bank.local/>
        SELECT ?instrument WHERE {
            ?fund bank:holds ?instrument .
            FILTER (?fund = bank:FUND-GROWTH-A)
        }
    """
    results = g.query(query_text)
    return sorted(str(row[0]).split("/")[-1] for row in results)


def multi_hop_query(g: Graph) -> list[str]:
    """SPARQL: which funds hold an instrument traded by CP-ALTAMAR?

    `holds` chains parent->child, so `holds+` (one or more hops) walks the whole
    holdings tree, catching instruments nested under sub-sleeves too. That multi-hop
    reachability is exactly what reads naturally as a graph and is painful as SQL joins.
    In the seed, CP-ALTAMAR trades INS-QTZL, which sits under INS-SLEEVE-EQ, which
    FUND-GROWTH-A holds, so FUND-GROWTH-A comes back."""
    query_text = """
        PREFIX bank: <http://bank.local/>
        SELECT DISTINCT ?fund WHERE {
            ?fund bank:holds+ ?instrument .
            ?instrument bank:traded_by bank:CP-ALTAMAR .
        }
    """
    results = g.query(query_text)
    return sorted(str(row[0]).split("/")[-1] for row in results)


def aggregate_query(g: Graph) -> dict[str, int]:
    """SPARQL query: for each counterparty, how many distinct instruments do they trade?"""
    query_text = """
        PREFIX bank: <http://bank.local/>
        SELECT ?counterparty (COUNT(DISTINCT ?instrument) as ?instrument_count) WHERE {
            ?instrument bank:traded_by ?counterparty .
        }
        GROUP BY ?counterparty
    """
    results = g.query(query_text)
    agg = {}
    for row in results:
        counterparty_id = str(row[0]).split("/")[-1]
        count = int(row[1])
        agg[counterparty_id] = count
    return agg


def main() -> None:
    ap = argparse.ArgumentParser(description="Query a knowledge graph with SPARQL")
    ap.add_argument("--step", choices=["load", "simple-query", "multi-hop", "sql", "aggregate",
                                       "list-counterparties"],
                    help="run a specific step")
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()

    print("Loading graph...")
    g = load_graph()
    print(f"  Loaded {len(g)} triples")

    if args.step == "simple-query" or not args.step:
        print("\nSPARQL query: which instruments does FUND-GROWTH-A hold directly?")
        instruments = simple_query(g)
        for instrument in instruments:
            print(f"  {instrument}")
        if args.step:
            return

    if args.step == "multi-hop" or not args.step:
        print("\nSPARQL multi-hop query: which funds hold an instrument traded by CP-ALTAMAR?")
        funds = multi_hop_query(g)
        for fund in funds:
            print(f"  {fund}")
        if args.step:
            return

    if args.step == "sql" or not args.step:
        print("\nEquivalent SQL query:")
        sql = """
        WITH RECURSIVE tree(root_fund, node) AS (
            SELECT f.fund_id, f.fund_id FROM bank.fund f
          UNION ALL
            SELECT t.root_fund, h.instrument_id
            FROM tree t JOIN bank.holding h ON h.parent_id = t.node
        )
        SELECT DISTINCT t.root_fund
        FROM tree t
        JOIN bank.trade_counterparty tc ON tc.instrument_id = t.node
        WHERE tc.counterparty_id = 'CP-ALTAMAR'
          AND t.root_fund LIKE 'FUND-%'
        """
        print(sql)

        with connect() as conn:
            with conn.cursor() as cur:
                try:
                    cur.execute("""
                        WITH RECURSIVE tree(root_fund, node) AS (
                            SELECT f.fund_id, f.fund_id FROM bank.fund f
                          UNION ALL
                            SELECT t.root_fund, h.instrument_id
                            FROM tree t JOIN bank.holding h ON h.parent_id = t.node
                        )
                        SELECT DISTINCT t.root_fund
                        FROM tree t
                        JOIN bank.trade_counterparty tc ON tc.instrument_id = t.node
                        WHERE tc.counterparty_id = 'CP-ALTAMAR'
                          AND t.root_fund LIKE 'FUND-%'
                    """)
                    rows = cur.fetchall()
                    print(f"  SQL Result: {rows}")
                except Exception as e:
                    print(f"  SQL query failed (may be missing trade_counterparty table): {e}")
        if args.step:
            return

    if args.step == "aggregate":
        print("\nSPARQL aggregation: instruments per counterparty")
        agg = aggregate_query(g)
        for counterparty, count in sorted(agg.items(), key=lambda x: x[0]):
            print(f"  {counterparty}: {count}")

    if args.step == "list-counterparties":
        print("Counterparties in graph:")
        BANK = Namespace("http://bank.local/")
        counterparties = set()
        for obj in g.objects(None, URIRef(BANK.traded_by)):
            counterparty_id = str(obj).split("/")[-1]
            counterparties.add(counterparty_id)
        for counterparty_id in sorted(counterparties):
            print(f"  {counterparty_id}")


if __name__ == "__main__":
    main()
