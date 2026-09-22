#!/usr/bin/env python3
"""Build a knowledge graph from the factory schema using RDF triples and rdflib.

Loads BOM, supplier, and machine relationships from Lakebase into an in-memory
RDF graph, then runs SPARQL queries to demonstrate graph traversal.

Usage:
    python kg_build.py                 # run full build + queries
    python kg_build.py --step load     # just load the graph
    python kg_build.py --step query    # load + query
    python kg_build.py --verbose       # show each triple as it's added
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


def load_graph(verbose: bool = False) -> Graph:
    """Load the factory schema into an RDF graph.

    Returns (graph, stats) where stats is a dict of counts.
    """
    g = Graph()
    FACTORY = Namespace("http://factory.local/")

    stats = {
        "products": 0,
        "parts": 0,
        "bom_edges": 0,
        "suppliers": 0,
        "supplier_edges": 0,
        "machines": 0,
        "machine_edges": 0,
    }

    with connect() as conn:
        with conn.cursor() as cur:
            # Load products
            if verbose:
                print("Loading products...")
            cur.execute("SELECT product_id, name FROM factory.product")
            for product_id, name in cur.fetchall():
                g.add((
                    URIRef(FACTORY[product_id]),
                    URIRef(FACTORY.name),
                    Literal(name)
                ))
                stats["products"] += 1
                if verbose:
                    print(f"  +product {product_id}")

            # Load parts
            if verbose:
                print("Loading parts...")
            cur.execute("SELECT part_id, name FROM factory.part")
            for part_id, name in cur.fetchall():
                g.add((
                    URIRef(FACTORY[part_id]),
                    URIRef(FACTORY.name),
                    Literal(name)
                ))
                stats["parts"] += 1
                if verbose:
                    print(f"  +part {part_id}")

            # Load BOM edges (parent contains child parts)
            if verbose:
                print("Loading BOM edges...")
            cur.execute("""
                SELECT parent_id, child_part, qty
                FROM factory.bom_edge
                LIMIT 1000
            """)
            for parent_id, child_part, qty in cur.fetchall():
                g.add((
                    URIRef(FACTORY[parent_id]),
                    URIRef(FACTORY.contains),
                    URIRef(FACTORY[child_part])
                ))
                stats["bom_edges"] += 1
                if verbose:
                    print(f"  +edge {parent_id} contains {child_part}")

            # Load suppliers
            if verbose:
                print("Loading suppliers...")
            cur.execute("SELECT supplier_id, name FROM factory.supplier")
            for supplier_id, name in cur.fetchall():
                g.add((
                    URIRef(FACTORY[supplier_id]),
                    URIRef(FACTORY.name),
                    Literal(name)
                ))
                stats["suppliers"] += 1
                if verbose:
                    print(f"  +supplier {supplier_id}")

            # Load supplier relationships (if part_supplier table exists)
            try:
                if verbose:
                    print("Loading supplier edges...")
                cur.execute("""
                    SELECT part_id, supplier_id
                    FROM factory.part_supplier
                    LIMIT 1000
                """)
                for part_id, supplier_id in cur.fetchall():
                    g.add((
                        URIRef(FACTORY[part_id]),
                        URIRef(FACTORY.supplied_by),
                        URIRef(FACTORY[supplier_id])
                    ))
                    stats["supplier_edges"] += 1
                    if verbose:
                        print(f"  +edge {part_id} supplied_by {supplier_id}")
            except Exception:
                # part_supplier may not exist; skip gracefully
                pass

            # Load machines
            if verbose:
                print("Loading machines...")
            cur.execute("SELECT machine_id, plant_id FROM factory.machine")
            for machine_id, plant_id in cur.fetchall():
                g.add((
                    URIRef(FACTORY[machine_id]),
                    URIRef(FACTORY.operates_in),
                    URIRef(FACTORY[plant_id])
                ))
                stats["machines"] += 1
                stats["machine_edges"] += 1
                if verbose:
                    print(f"  +edge {machine_id} operates_in {plant_id}")

    return g, stats


def query_bom(g: Graph, product_id: str) -> list[str]:
    """Query: which parts does a product contain (direct children)?"""
    from rdflib import RDF, RDFS

    FACTORY = Namespace("http://factory.local/")
    product_uri = URIRef(FACTORY[product_id])

    parts = []
    for obj in g.objects(product_uri, URIRef(FACTORY.contains)):
        part_id = str(obj).split("/")[-1]
        parts.append(part_id)

    return sorted(parts)


def main() -> None:
    ap = argparse.ArgumentParser(description="Build a knowledge graph from factory schema")
    ap.add_argument("--step", choices=["load", "query", "sql", "list-products", "inspect"],
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
        print("\nQuery: which parts does PRD-GEARBOX-X1 contain?")
        parts = query_bom(g, "PRD-GEARBOX-X1")
        for part in parts:
            print(f"  {part}")

        if args.step:
            return

    if args.step == "sql" or not args.step:
        print("\nEquivalent SQL:")
        print("  SELECT child_part FROM factory.bom_edge WHERE parent_id = 'PRD-GEARBOX-X1'")

        with connect() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT child_part FROM factory.bom_edge WHERE parent_id = 'PRD-GEARBOX-X1'
                """)
                rows = cur.fetchall()
                print(f"  Result: {rows}")

    if args.step == "list-products":
        print("Products in graph:")
        FACTORY = Namespace("http://factory.local/")
        products = set()
        for subj in g.subjects():
            product_id = str(subj).split("/")[-1]
            if product_id.startswith("PRD-"):
                products.add(product_id)
        for product_id in sorted(products):
            print(f"  {product_id}")

    if args.step == "inspect":
        print("Graph inspection:")
        print(f"  Triples: {len(g)}")
        print(f"  Subjects: {len(set(g.subjects()))}")
        print(f"  Predicates: {len(set(g.predicates()))}")
        print(f"  Objects: {len(set(g.objects()))}")


if __name__ == "__main__":
    main()
