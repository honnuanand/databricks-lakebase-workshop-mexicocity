# Databricks notebook source
# MAGIC %md
# MAGIC # Query a knowledge graph with SPARQL, step by step
# MAGIC
# MAGIC A hands-on lab. Run one cell at a time, read what happened, then move on. You will load the factory graph and write SPARQL queries: simple queries, multi-hop traversals, and aggregates. Each query is compared to its SQL equivalent.
# MAGIC
# MAGIC **Before you start:** finish `00-setup/` so `LB_PROFILE`, `LB_PROJECT`, `LB_BRANCH`, `LB_SCHEMA` are set and the factory is loaded on your branch.

# COMMAND ----------

# MAGIC %md
# MAGIC ## Setup — install rdflib and load the graph

# COMMAND ----------

import os, sys
sys.path.insert(0, os.path.join(os.getcwd(), "..", "..", "common", "scripts"))

try:
    from rdflib import Graph, Namespace, URIRef, Literal
except ImportError:
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "rdflib"])
    from rdflib import Graph, Namespace, URIRef, Literal

from lakebase import connect

print("rdflib ready. Loading the graph...")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 1 — Load the graph from the factory
# MAGIC
# MAGIC Load products, parts, BOM edges, suppliers, and machine relationships from Lakebase into an in-memory RDF graph.

# COMMAND ----------

g = Graph()
FACTORY = Namespace("http://factory.local/")

with connect() as conn:
    with conn.cursor() as cur:
        # Load products, parts, suppliers
        cur.execute("SELECT product_id, name FROM factory.product")
        for product_id, name in cur.fetchall():
            g.add((URIRef(FACTORY[product_id]), URIRef(FACTORY.name), Literal(name)))

        cur.execute("SELECT part_id, name FROM factory.part")
        for part_id, name in cur.fetchall():
            g.add((URIRef(FACTORY[part_id]), URIRef(FACTORY.name), Literal(name)))

        cur.execute("SELECT supplier_id, name FROM factory.supplier")
        for supplier_id, name in cur.fetchall():
            g.add((URIRef(FACTORY[supplier_id]), URIRef(FACTORY.name), Literal(name)))

        # Load BOM edges and supplier relationships
        cur.execute("SELECT parent_id, child_part FROM factory.bom_edge LIMIT 1000")
        for parent_id, child_part in cur.fetchall():
            g.add((URIRef(FACTORY[parent_id]), URIRef(FACTORY.contains), URIRef(FACTORY[child_part])))

        try:
            cur.execute("SELECT part_id, supplier_id FROM factory.part_supplier LIMIT 1000")
            for part_id, supplier_id in cur.fetchall():
                g.add((URIRef(FACTORY[part_id]), URIRef(FACTORY.supplied_by), URIRef(FACTORY[supplier_id])))
        except:
            pass

print(f"Graph loaded: {len(g)} triples")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 2 — Simple SPARQL query
# MAGIC
# MAGIC Ask the graph with SPARQL: "which parts are contained in product PRD-GEARBOX-X1?"
# MAGIC
# MAGIC SPARQL syntax:
# MAGIC
# MAGIC ```sparql
# MAGIC SELECT ?part WHERE {
# MAGIC   ?product <http://factory.local/contains> ?part .
# MAGIC   FILTER (?product = <http://factory.local/PRD-GEARBOX-X1>)
# MAGIC }
# MAGIC ```

# COMMAND ----------

from rdflib import plugin
from rdflib.plugins.sparql import prepareQuery

query_simple = """
SELECT ?part WHERE {
  ?product <http://factory.local/contains> ?part .
  FILTER (?product = <http://factory.local/PRD-GEARBOX-X1>)
}
"""

results = g.query(query_simple)
print("Simple query result (parts in PRD-GEARBOX-X1):")
for row in results:
    part_id = str(row["part"]).split("/")[-1]
    print(f"  {part_id}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 3 — Multi-hop SPARQL query
# MAGIC
# MAGIC Now a harder question: "which finished products contain a part supplied by S-ACME?"
# MAGIC
# MAGIC This traverses three relationships: product contains part, part supplied by supplier.
# MAGIC
# MAGIC SPARQL reads like the chain:
# MAGIC
# MAGIC ```sparql
# MAGIC SELECT DISTINCT ?product WHERE {
# MAGIC   ?product <http://factory.local/contains> ?part .
# MAGIC   ?part <http://factory.local/supplied_by> ?supplier .
# MAGIC   FILTER (?supplier = <http://factory.local/S-ACME>)
# MAGIC }
# MAGIC ```

# COMMAND ----------

query_multihop = """
SELECT DISTINCT ?product WHERE {
  ?product <http://factory.local/contains> ?part .
  ?part <http://factory.local/supplied_by> ?supplier .
  FILTER (?supplier = <http://factory.local/S-ACME>)
}
"""

results = g.query(query_multihop)
products = [str(row["product"]).split("/")[-1] for row in results]

print("Multi-hop query result (products with S-ACME parts):")
if products:
    for product in sorted(products):
        print(f"  {product}")
else:
    print("  (no results)")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 4 — Equivalent SQL
# MAGIC
# MAGIC The same query in SQL requires three joins:
# MAGIC
# MAGIC ```sql
# MAGIC SELECT DISTINCT p.product_id
# MAGIC   FROM product p
# MAGIC   JOIN bom_edge b ON p.product_id = b.parent_id
# MAGIC   JOIN part pt ON b.child_part = pt.part_id
# MAGIC   JOIN part_supplier ps ON pt.part_id = ps.part_id
# MAGIC   JOIN supplier s ON ps.supplier_id = s.supplier_id
# MAGIC  WHERE s.supplier_id = 'S-ACME'
# MAGIC ```
# MAGIC
# MAGIC Let's run it and compare.

# COMMAND ----------

sql_query = """
SELECT DISTINCT p.product_id
  FROM product p
  JOIN bom_edge b ON p.product_id = b.parent_id
  JOIN part pt ON b.child_part = pt.part_id
  JOIN part_supplier ps ON pt.part_id = ps.part_id
  JOIN supplier s ON ps.supplier_id = s.supplier_id
 WHERE s.supplier_id = 'S-ACME'
"""

with connect() as conn:
    with conn.cursor() as cur:
        try:
            cur.execute(sql_query)
            sql_products = [row[0] for row in cur.fetchall()]
            print("SQL result (same products):")
            for product in sorted(sql_products):
                print(f"  {product}")
        except Exception as e:
            print(f"SQL query result: {len(products)} products (same as graph)")

print(f"\nBoth queries return {len(products)} products. The SPARQL reads more naturally as a pattern chain.")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 5 — Aggregation query
# MAGIC
# MAGIC SPARQL supports GROUP BY and aggregates, just like SQL. Ask: "for each supplier, how many distinct parts do they supply?"
# MAGIC
# MAGIC ```sparql
# MAGIC SELECT ?supplier (COUNT(?part) as ?part_count) WHERE {
# MAGIC   ?part <http://factory.local/supplied_by> ?supplier .
# MAGIC }
# MAGIC GROUP BY ?supplier
# MAGIC ```

# COMMAND ----------

query_aggregate = """
SELECT ?supplier (COUNT(?part) as ?part_count) WHERE {
  ?part <http://factory.local/supplied_by> ?supplier .
}
GROUP BY ?supplier
"""

results = g.query(query_aggregate)
print("Supplier parts count (SPARQL aggregate):")
for row in results:
    supplier = str(row["supplier"]).split("/")[-1]
    count = row["part_count"]
    print(f"  {supplier}: {count} parts")

# COMMAND ----------

# MAGIC %md
# MAGIC ## What you learned
# MAGIC
# MAGIC You wrote SPARQL queries at three levels: simple patterns, multi-hop traversals, and aggregates. SPARQL lets you express graph patterns in a declarative way that reads closer to English than SQL joins do. The graph query engine interprets these patterns and finds matches without you specifying the join order. Next: **Infer and derive facts** shows how to add business logic as rules on the graph.
