#!/usr/bin/env python3
"""Query a knowledge graph with SPARQL.

Builds the graph from factory schema, then runs SPARQL queries
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
    """Load factory schema into RDF graph."""
    g = Graph()
    FACTORY = Namespace("http://factory.local/")

    with connect() as conn:
        with conn.cursor() as cur:
            # Load products, parts
            cur.execute("SELECT product_id, name FROM factory.product")
            for product_id, name in cur.fetchall():
                g.add((URIRef(FACTORY[product_id]), URIRef(FACTORY.name), Literal(name)))

            cur.execute("SELECT part_id, name FROM factory.part")
            for part_id, name in cur.fetchall():
                g.add((URIRef(FACTORY[part_id]), URIRef(FACTORY.name), Literal(name)))

            # Load BOM edges
            cur.execute("SELECT parent_id, child_part FROM factory.bom_edge LIMIT 1000")
            for parent_id, child_part in cur.fetchall():
                g.add((
                    URIRef(FACTORY[parent_id]),
                    URIRef(FACTORY.contains),
                    URIRef(FACTORY[child_part])
                ))

            # Load suppliers
            cur.execute("SELECT supplier_id, name FROM factory.supplier")
            for supplier_id, name in cur.fetchall():
                g.add((URIRef(FACTORY[supplier_id]), URIRef(FACTORY.name), Literal(name)))

            # Load supplier edges (if part_supplier exists)
            try:
                cur.execute("SELECT part_id, supplier_id FROM factory.part_supplier LIMIT 1000")
                for part_id, supplier_id in cur.fetchall():
                    g.add((
                        URIRef(FACTORY[part_id]),
                        URIRef(FACTORY.supplied_by),
                        URIRef(FACTORY[supplier_id])
                    ))
            except Exception:
                pass

    return g


def simple_query(g: Graph) -> list[str]:
    """SPARQL query: which parts does PRD-GEARBOX-X1 contain?"""
    query_text = """
        PREFIX factory: <http://factory.local/>
        SELECT ?part WHERE {
            ?product factory:contains ?part .
            FILTER (?product = factory:PRD-GEARBOX-X1)
        }
    """
    results = g.query(query_text)
    return [str(row[0]).split("/")[-1] for row in results]


def multi_hop_query(g: Graph) -> list[str]:
    """SPARQL query: which products contain parts from supplier S-ACME?"""
    query_text = """
        PREFIX factory: <http://factory.local/>
        SELECT DISTINCT ?product WHERE {
            ?product factory:contains ?part .
            ?part factory:supplied_by ?supplier .
            FILTER (?supplier = factory:S-ACME)
        }
    """
    results = g.query(query_text)
    return sorted([str(row[0]).split("/")[-1] for row in results])


def aggregate_query(g: Graph) -> dict[str, int]:
    """SPARQL query: for each supplier, how many distinct parts do they supply?"""
    query_text = """
        PREFIX factory: <http://factory.local/>
        SELECT ?supplier (COUNT(DISTINCT ?part) as ?part_count) WHERE {
            ?part factory:supplied_by ?supplier .
        }
        GROUP BY ?supplier
    """
    results = g.query(query_text)
    agg = {}
    for row in results:
        supplier_id = str(row[0]).split("/")[-1]
        count = int(row[1])
        agg[supplier_id] = count
    return agg


def main() -> None:
    ap = argparse.ArgumentParser(description="Query a knowledge graph with SPARQL")
    ap.add_argument("--step", choices=["load", "simple-query", "multi-hop", "sql", "aggregate",
                                       "list-suppliers"],
                    help="run a specific step")
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()

    print("Loading graph...")
    g = load_graph()
    print(f"  Loaded {len(g)} triples")

    if args.step == "simple-query" or not args.step:
        print("\nSPARQL query: which parts are contained in PRD-GEARBOX-X1?")
        parts = simple_query(g)
        for part in parts:
            print(f"  {part}")
        if args.step:
            return

    if args.step == "multi-hop" or not args.step:
        print("\nSPARQL multi-hop query: which products contain a part from S-ACME?")
        products = multi_hop_query(g)
        for product in products:
            print(f"  {product}")
        if args.step:
            return

    if args.step == "sql" or not args.step:
        print("\nEquivalent SQL query:")
        sql = """
        SELECT DISTINCT p.product_id
        FROM factory.product p
        JOIN factory.bom_edge b ON p.product_id = b.parent_id
        JOIN factory.part pt ON b.child_part = pt.part_id
        LEFT JOIN factory.part_supplier ps ON pt.part_id = ps.part_id
        LEFT JOIN factory.supplier s ON ps.supplier_id = s.supplier_id
        WHERE s.supplier_id = 'S-ACME'
        """
        print(sql)

        with connect() as conn:
            with conn.cursor() as cur:
                try:
                    cur.execute("""
                        SELECT DISTINCT p.product_id
                        FROM factory.product p
                        JOIN factory.bom_edge b ON p.product_id = b.parent_id
                        JOIN factory.part pt ON b.child_part = pt.part_id
                        LEFT JOIN factory.part_supplier ps ON pt.part_id = ps.part_id
                        LEFT JOIN factory.supplier s ON ps.supplier_id = s.supplier_id
                        WHERE s.supplier_id = 'S-ACME'
                    """)
                    rows = cur.fetchall()
                    print(f"  SQL Result: {rows}")
                except Exception as e:
                    print(f"  SQL query failed (may be missing part_supplier table): {e}")
        if args.step:
            return

    if args.step == "aggregate":
        print("\nSPARQL aggregation: parts per supplier")
        agg = aggregate_query(g)
        for supplier, count in sorted(agg.items(), key=lambda x: x[0]):
            print(f"  {supplier}: {count}")

    if args.step == "list-suppliers":
        print("Suppliers in graph:")
        FACTORY = Namespace("http://factory.local/")
        suppliers = set()
        for obj in g.objects(None, URIRef(FACTORY.supplied_by)):
            supplier_id = str(obj).split("/")[-1]
            suppliers.add(supplier_id)
        for supplier_id in sorted(suppliers):
            print(f"  {supplier_id}")


if __name__ == "__main__":
    main()
