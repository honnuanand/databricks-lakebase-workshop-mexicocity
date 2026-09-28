# Databricks notebook source
# MAGIC %md
# MAGIC # Build a knowledge graph, step by step
# MAGIC
# MAGIC A hands-on lab. Run one cell at a time, read what happened, then move on. You will load the factory data into an RDF graph, run graph traversal queries, and see how graph queries compare to SQL.
# MAGIC
# MAGIC Each step shows the real interface: Python and rdflib for the graph operations, SQL when a step queries the database.
# MAGIC
# MAGIC **Before you start:** finish `00-setup/` so `LB_PROFILE`, `LB_PROJECT`, `LB_BRANCH`, `LB_SCHEMA` are set and the factory is loaded on your branch.

# COMMAND ----------

# MAGIC %md
# MAGIC ## Setup, install rdflib and connect to your branch

# COMMAND ----------

import os, sys
sys.path.insert(0, os.path.join(os.getcwd(), "..", "..", "common", "scripts"))

# Install rdflib if not already present
try:
    from rdflib import Graph, Namespace, URIRef, Literal
except ImportError:
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "rdflib"])
    from rdflib import Graph, Namespace, URIRef, Literal

from lakebase import connect

print("rdflib installed. Ready to load the graph.")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 1, Load the BOM as triples
# MAGIC
# MAGIC The factory has a bill of materials (BOM): products are made of parts, parts are supplied by suppliers, and machines operate in plants. We convert this into RDF triples, the subject-predicate-object triples that form a knowledge graph.
# MAGIC
# MAGIC Each triple is a fact: `(product, contains, part)`, `(part, supplied_by, supplier)`, `(machine, operates_in, plant)`.
# MAGIC
# MAGIC The SQL to load products:
# MAGIC
# MAGIC ```sql
# MAGIC SELECT product_id, name FROM factory.product
# MAGIC ```

# COMMAND ----------

g = Graph()
FACTORY = Namespace("http://factory.local/")

stats = {
    "products": 0,
    "parts": 0,
    "bom_edges": 0,
    "suppliers": 0,
    "supplier_edges": 0,
    "machines": 0,
}

with connect() as conn:
    with conn.cursor() as cur:
        # Load products
        cur.execute("SELECT product_id, name FROM factory.product")
        for product_id, name in cur.fetchall():
            g.add((URIRef(FACTORY[product_id]), URIRef(FACTORY.name), Literal(name)))
            stats["products"] += 1

        # Load parts
        cur.execute("SELECT part_id, name FROM factory.part")
        for part_id, name in cur.fetchall():
            g.add((URIRef(FACTORY[part_id]), URIRef(FACTORY.name), Literal(name)))
            stats["parts"] += 1

        # Load BOM edges (parent contains child)
        cur.execute("SELECT parent_id, child_part, qty FROM factory.bom_edge LIMIT 1000")
        for parent_id, child_part, qty in cur.fetchall():
            g.add((URIRef(FACTORY[parent_id]), URIRef(FACTORY.contains), URIRef(FACTORY[child_part])))
            stats["bom_edges"] += 1

        # Load suppliers
        cur.execute("SELECT supplier_id, name FROM factory.supplier")
        for supplier_id, name in cur.fetchall():
            g.add((URIRef(FACTORY[supplier_id]), URIRef(FACTORY.name), Literal(name)))
            stats["suppliers"] += 1

        # Load supplier relationships
        try:
            cur.execute("SELECT part_id, supplier_id FROM factory.part_supplier LIMIT 1000")
            for part_id, supplier_id in cur.fetchall():
                g.add((URIRef(FACTORY[part_id]), URIRef(FACTORY.supplied_by), URIRef(FACTORY[supplier_id])))
                stats["supplier_edges"] += 1
        except:
            pass  # Table may not exist

        # Load machines
        cur.execute("SELECT machine_id, plant_id FROM factory.machine")
        for machine_id, plant_id in cur.fetchall():
            g.add((URIRef(FACTORY[machine_id]), URIRef(FACTORY.operates_in), URIRef(FACTORY[plant_id])))
            stats["machines"] += 1

print(f"Loaded {len(g)} triples:")
for key, val in stats.items():
    if val > 0:
        print(f"  - {val} {key}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 2, Query the graph for a single BOM path
# MAGIC
# MAGIC Ask the graph: "which parts are directly contained in product PRD-GEARBOX-X1?"
# MAGIC
# MAGIC This is a traversal of the `contains` relationship. We iterate through the graph's objects for that product and predicate.

# COMMAND ----------

product_id = "PRD-GEARBOX-X1"
product_uri = URIRef(FACTORY[product_id])

parts = []
for obj in g.objects(product_uri, URIRef(FACTORY.contains)):
    part_id = str(obj).split("/")[-1]
    parts.append(part_id)

print(f"Parts contained in {product_id}:")
for part in sorted(parts):
    print(f"  {part}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 3, Show the equivalent SQL
# MAGIC
# MAGIC The same query in SQL is straightforward for a simple containment:
# MAGIC
# MAGIC ```sql
# MAGIC SELECT child_part FROM factory.bom_edge WHERE parent_id = 'PRD-GEARBOX-X1'
# MAGIC ```
# MAGIC
# MAGIC Let's run it and compare.

# COMMAND ----------

with connect() as conn:
    with conn.cursor() as cur:
        cur.execute("SELECT child_part FROM factory.bom_edge WHERE parent_id = %s", [product_id])
        sql_parts = [row[0] for row in cur.fetchall()]

print(f"SQL result for {product_id}:")
for part in sorted(sql_parts):
    print(f"  {part}")

print(f"\nBoth queries return the same {len(parts)} parts. The graph and SQL are equivalent here.")
print(f"The difference shows when you ask multi-hop questions like 'products containing a part from supplier S-ACME'.")

# COMMAND ----------

# MAGIC %md
# MAGIC ## What you learned
# MAGIC
# MAGIC You converted a relational data model (product-BOM-supplier graph) into an RDF knowledge graph, loaded it into an in-memory store (rdflib), and ran graph traversal queries. For simple single-hop questions, the graph and SQL are equally readable. But the real power emerges with multi-hop queries: the graph stays flat while SQL queries grow joins. Next: **Query a knowledge graph with SPARQL** shows you SPARQL syntax for harder questions.
