#!/usr/bin/env python3
"""Knowledge graph inference: define rules and derive new facts.

Demonstrates RDF inference/entailment: state that "if a part is recalled,
all products containing it are affected," then let the graph infer which
products are affected.

Usage:
    python kg_infer.py                     # full inference demo
    python kg_infer.py --step rule-simple  # define simple rule
    python kg_infer.py --step entail       # apply entailment
    python kg_infer.py --step query-after  # query inferred facts
"""
from __future__ import annotations

import argparse
from lakebase import connect

try:
    from rdflib import Graph, Namespace, URIRef, Literal
except ImportError:
    raise ImportError("rdflib not installed. Run: pip install rdflib")


def load_graph() -> Graph:
    """Load factory schema into RDF graph."""
    g = Graph()
    FACTORY = Namespace("http://factory.local/")

    with connect() as conn:
        with conn.cursor() as cur:
            # Load products
            cur.execute("SELECT product_id FROM factory.product LIMIT 100")
            for (product_id,) in cur.fetchall():
                g.add((URIRef(FACTORY[product_id]), URIRef(FACTORY.type), URIRef(FACTORY.Product)))

            # Load parts
            cur.execute("SELECT part_id FROM factory.part LIMIT 100")
            for (part_id,) in cur.fetchall():
                g.add((URIRef(FACTORY[part_id]), URIRef(FACTORY.type), URIRef(FACTORY.Part)))

            # Load BOM edges
            cur.execute("SELECT parent_id, child_part FROM factory.bom_edge LIMIT 500")
            for parent_id, child_part in cur.fetchall():
                g.add((
                    URIRef(FACTORY[parent_id]),
                    URIRef(FACTORY.contains),
                    URIRef(FACTORY[child_part])
                ))

    return g


def simple_rule_example() -> str:
    """Show the simple rule pattern."""
    return """
    Rule: if (product contains part) and (part recalled) then (product affected_by_recall)

    In logic:
        (?product factory:contains ?part) AND (?part factory:recalled true)
            => (?product factory:affected_by_recall true)
    """


def main() -> None:
    ap = argparse.ArgumentParser(description="Knowledge graph inference with rules")
    ap.add_argument("--step", choices=["load", "rule-simple", "recall-part", "query-before",
                                       "entail", "query-after", "rule-chain", "list-parts"],
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
        print("\nDefining rule: part recalled → product affected")
        print(simple_rule_example())
        if args.step:
            return

    if args.step == "recall-part" or not args.step:
        FACTORY = Namespace("http://factory.local/")
        print("\nMarking PT-BEARING-6204 as recalled...")
        g.add((
            URIRef(FACTORY["PT-BEARING-6204"]),
            URIRef(FACTORY.recalled),
            Literal(True)
        ))
        print("  Asserted: PT-BEARING-6204 recalled=true")
        if args.step:
            return

    if args.step == "query-before" or not args.step:
        print("\nQuery (before inference): which products are affected?")
        FACTORY = Namespace("http://factory.local/")
        affected = []
        for subj in g.subjects(URIRef(FACTORY.affected_by_recall), Literal(True)):
            product_id = str(subj).split("/")[-1]
            affected.append(product_id)
        print(f"  Products affected: {affected if affected else '[]'}")
        if args.step:
            return

    if args.step == "entail" or not args.step:
        print("\nApplying entailment...")
        FACTORY = Namespace("http://factory.local/")

        # Manual forward-chaining for this simple rule
        # Find all (product contains part) where (part recalled=true)
        count_before = len(g)
        for obj in g.objects(None, URIRef(FACTORY.recalled)):
            if obj == Literal(True):
                # This is a recalled part
                for subj in g.subjects(URIRef(FACTORY.contains), obj):
                    # subj is a product containing the recalled part
                    g.add((
                        subj,
                        URIRef(FACTORY.affected_by_recall),
                        Literal(True)
                    ))

        count_after = len(g)
        print(f"  Triples before: {count_before}")
        print(f"  Triples after: {count_after}")
        print(f"  Inferred: {count_after - count_before} new triples")
        if args.step:
            return

    if args.step == "query-after" or not args.step:
        print("\nQuery (after inference): which products are affected?")
        FACTORY = Namespace("http://factory.local/")
        affected = []
        for subj in g.subjects(URIRef(FACTORY.affected_by_recall), Literal(True)):
            product_id = str(subj).split("/")[-1]
            if product_id.startswith("PRD-"):
                affected.append(product_id)
        print(f"  Products affected:")
        for product in sorted(affected):
            print(f"    {product}")

    if args.step == "rule-chain":
        print("\nDefining chain rule: affected parts → affected assemblies")
        print("""
        Rule: if (assembly part_of product) and (part recalled) then (assembly affected)
        """)

    if args.step == "list-parts":
        print("Parts in graph:")
        FACTORY = Namespace("http://factory.local/")
        parts = set()
        for subj in g.subjects(URIRef(FACTORY.type), URIRef(FACTORY.Part)):
            part_id = str(subj).split("/")[-1]
            parts.add(part_id)
        for part_id in sorted(parts)[:20]:  # Show first 20
            print(f"  {part_id}")
        if len(parts) > 20:
            print(f"  ... and {len(parts) - 20} more")


if __name__ == "__main__":
    main()
