#!/usr/bin/env python3
"""Knowledge graph inference: define rules and derive new facts.

Demonstrates RDF inference/entailment: state that "if an instrument is distressed,
every fund that holds it (directly or through a sleeve) is exposed," then let the
graph infer which funds are exposed, following the holdings tree transitively.

Usage:
    python kg_infer.py                        # full inference demo
    python kg_infer.py --step rule-simple     # define the simple rule
    python kg_infer.py --step distress        # assert one distressed instrument
    python kg_infer.py --step entail          # apply entailment
    python kg_infer.py --step query-after     # query inferred (exposed) funds
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

BANK = Namespace("http://bank.local/")

# The instrument we will mark distressed. INS-QTZL sits two hops below FUND-GROWTH-A
# (fund -> INS-SLEEVE-EQ -> INS-QTZL), so the entailment has to walk the tree to find it.
DISTRESSED = "INS-QTZL"


def load_graph() -> Graph:
    """Load the bank holdings structure into an RDF graph.

    Funds and instruments become typed nodes; each `holding` row becomes a
    `contains` edge from the parent (a fund or a sleeve instrument) to the held
    instrument. A sleeve is an instrument that itself contains other instruments,
    so `contains` forms a tree we can reason over transitively.
    """
    g = Graph()

    with connect() as conn:
        with conn.cursor() as cur:
            # Load funds
            cur.execute("SELECT fund_id FROM bank.fund LIMIT 100")
            for (fund_id,) in cur.fetchall():
                g.add((URIRef(BANK[fund_id]), URIRef(BANK.type), URIRef(BANK.Fund)))

            # Load instruments
            cur.execute("SELECT instrument_id FROM bank.instrument LIMIT 100")
            for (instrument_id,) in cur.fetchall():
                g.add((URIRef(BANK[instrument_id]), URIRef(BANK.type), URIRef(BANK.Instrument)))

            # Load holding edges (parent contains instrument)
            cur.execute("SELECT parent_id, instrument_id FROM bank.holding LIMIT 500")
            for parent_id, instrument_id in cur.fetchall():
                g.add((
                    URIRef(BANK[parent_id]),
                    URIRef(BANK.contains),
                    URIRef(BANK[instrument_id])
                ))

    return g


def simple_rule_example() -> str:
    """Show the simple rule pattern."""
    return """
    Rule: if (fund holds instrument) and (instrument distressed) then (fund exposed)

    In logic:
        (?fund bank:contains ?instrument) AND (?instrument bank:distressed true)
            => (?fund bank:exposed true)

    'contains' is transitive here: a fund that holds a sleeve, and the sleeve holds the
    instrument, means the fund holds the instrument. So the rule chains down the tree.
    """


def main() -> None:
    ap = argparse.ArgumentParser(description="Knowledge graph inference with rules")
    ap.add_argument("--step", choices=["load", "rule-simple", "distress", "query-before",
                                       "entail", "query-after", "rule-chain", "list-instruments"],
                    help="run a specific step")
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()

    if args.step == "load" or not args.step:
        print("Loading graph...")
        g = load_graph()
        print(f"  Loaded {len(g)} triples")
        if args.step:
            return
    else:
        g = load_graph()

    if args.step == "rule-simple" or not args.step:
        print("\nDefining rule: instrument distressed → fund exposed")
        print(simple_rule_example())
        if args.step:
            return

    if args.step == "distress" or not args.step:
        print(f"\nMarking {DISTRESSED} as distressed...")
        g.add((
            URIRef(BANK[DISTRESSED]),
            URIRef(BANK.distressed),
            Literal(True)
        ))
        print(f"  Asserted: {DISTRESSED} distressed=true")
        if args.step:
            return

    if args.step == "query-before" or not args.step:
        print("\nQuery (before inference): which funds are exposed?")
        exposed = []
        for subj in g.subjects(URIRef(BANK.exposed), Literal(True)):
            fund_id = str(subj).split("/")[-1]
            exposed.append(fund_id)
        print(f"  Funds exposed: {exposed if exposed else '[]'}")
        if args.step:
            return

    if args.step == "entail" or not args.step:
        print("\nApplying entailment...")

        # Forward-chaining for the rule: a fund is exposed if it holds a distressed
        # instrument ANYWHERE in its holdings tree (directly or through a sleeve).
        # `contains` chains parent->child, so we walk it transitively from each fund.
        count_before = len(g)

        # 1. collect the distressed instruments (subjects of `distressed = true`)
        distressed = {s for s, o in g.subject_objects(URIRef(BANK.distressed))
                      if o == Literal(True)}

        # 2. for every fund, walk contains* and mark it exposed if it reaches a distressed instrument
        def reaches(node, targets, seen=None):
            seen = seen or set()
            for child in g.objects(node, URIRef(BANK.contains)):
                if child in targets:
                    return True
                if child not in seen:
                    seen.add(child)
                    if reaches(child, targets, seen):
                        return True
            return False

        for fund in g.subjects(URIRef(BANK.type), URIRef(BANK.Fund)):
            if reaches(fund, distressed):
                g.add((fund, URIRef(BANK.exposed), Literal(True)))

        count_after = len(g)
        print(f"  Triples before: {count_before}")
        print(f"  Triples after: {count_after}")
        print(f"  Inferred: {count_after - count_before} new triples")
        if args.step:
            return

    if args.step == "query-after" or not args.step:
        print("\nQuery (after inference): which funds are exposed?")
        exposed = []
        for subj in g.subjects(URIRef(BANK.exposed), Literal(True)):
            fund_id = str(subj).split("/")[-1]
            if fund_id.startswith("FUND-"):
                exposed.append(fund_id)
        print(f"  Funds exposed:")
        for fund in sorted(exposed):
            print(f"    {fund}")

    if args.step == "rule-chain":
        print("\nDefining chain rule: exposed sleeve → exposed fund")
        print("""
        Rule: if (fund contains sleeve) and (sleeve exposed) then (fund exposed)
        """)

    if args.step == "list-instruments":
        print("Instruments in graph:")
        instruments = set()
        for subj in g.subjects(URIRef(BANK.type), URIRef(BANK.Instrument)):
            instrument_id = str(subj).split("/")[-1]
            instruments.add(instrument_id)
        for instrument_id in sorted(instruments)[:20]:  # Show first 20
            print(f"  {instrument_id}")
        if len(instruments) > 20:
            print(f"  ... and {len(instruments) - 20} more")


if __name__ == "__main__":
    main()
