# Databricks notebook source
# MAGIC %md
# MAGIC # Infer and derive facts, step by step
# MAGIC
# MAGIC A hands-on lab. Run one cell at a time, read what happened, then move on. You will define business logic as forward-chaining inference rules on a knowledge graph, then apply entailment to derive new facts automatically. This is how you express "if this part is recalled, then any product containing it is affected", and let the graph reason about consequences.
# MAGIC
# MAGIC **Before you start:** finish `00-setup/` so `LB_PROFILE`, `LB_PROJECT`, `LB_BRANCH`, `LB_SCHEMA` are set and the factory is loaded on your branch.

# COMMAND ----------

# MAGIC %md
# MAGIC ## Setup, install rdflib and load the graph

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
# MAGIC ## Step 1, Load the graph from the factory

# COMMAND ----------

g = Graph()
FACTORY = Namespace("http://factory.local/")

with connect() as conn:
    with conn.cursor() as cur:
        cur.execute("SELECT product_id, name FROM factory.product")
        for product_id, name in cur.fetchall():
            g.add((URIRef(FACTORY[product_id]), URIRef(FACTORY.name), Literal(name)))

        cur.execute("SELECT part_id, name FROM factory.part")
        for part_id, name in cur.fetchall():
            g.add((URIRef(FACTORY[part_id]), URIRef(FACTORY.name), Literal(name)))

        cur.execute("SELECT supplier_id, name FROM factory.supplier")
        for supplier_id, name in cur.fetchall():
            g.add((URIRef(FACTORY[supplier_id]), URIRef(FACTORY.name), Literal(name)))

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
# MAGIC ## Step 2, Define a business rule: if a part is recalled, products containing it are affected

# COMMAND ----------

# The rule expressed in natural language:
# "If a product contains a part, and that part is recalled, then the product is affected."

rule_text = """
(?product <http://factory.local/contains> ?part)
(?part <http://factory.local/recalled> ?status)
-> (?product <http://factory.local/affected_by_recall> true)
"""

print("Rule defined:")
print("  If (product contains part) AND (part is recalled)")
print("  Then (product is affected by recall)")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 3, Mark a part as recalled
# MAGIC
# MAGIC Add a fact to the graph: part PT-BEARING-6204 is recalled.

# COMMAND ----------

recalled_part = "PT-BEARING-6204"
g.add((URIRef(FACTORY[recalled_part]), URIRef(FACTORY.recalled), Literal(True)))

print(f"Marked {recalled_part} as recalled.")
print(f"Graph now has {len(g)} triples.")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 4, Query for affected products BEFORE inference
# MAGIC
# MAGIC Ask: "which products are marked as affected by a recall?"
# MAGIC
# MAGIC The answer is empty, because we never explicitly added any product as affected. We only marked a part as recalled.

# COMMAND ----------

query = """
SELECT ?product WHERE {
  ?product <http://factory.local/affected_by_recall> ?status .
}
"""

results = g.query(query)
affected_before = [str(row["product"]).split("/")[-1] for row in results]

print(f"Products affected (before inference): {affected_before}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 5, Apply inference
# MAGIC
# MAGIC Use forward chaining to apply the rule. The reasoner looks for all facts matching the rule's premises, and adds new facts (the conclusion) for each match.

# COMMAND ----------

triples_before = len(g)

# Collect all recalled parts (subjects of recalled = true)
recalled_parts = {s for s, o in g.subject_objects(URIRef(FACTORY.recalled))
                  if o == Literal(True)}

print(f"Found {len(recalled_parts)} recalled parts: {[str(p).split('/')[-1] for p in recalled_parts]}")

# For each product, walk contains* and mark it affected if it reaches a recalled part
def reaches(node, targets, seen=None):
    seen = seen or set()
    for child in g.objects(node, URIRef(FACTORY.contains)):
        if child in targets:
            return True
        if child not in seen:
            seen.add(child)
            if reaches(child, targets, seen):
                return True
    return False

# Iterate over all products and mark affected ones
product_count = 0
for product in g.subjects(URIRef(FACTORY.type), URIRef(FACTORY.Product)):
    product_count += 1
    if reaches(product, recalled_parts):
        g.add((product, URIRef(FACTORY.affected_by_recall), Literal(True)))

triples_after = len(g)
derived = triples_after - triples_before

print(f"Inference applied.")
print(f"  Checked {product_count} products")
print(f"  Derived {derived} new triples.")
print(f"  Graph now has {triples_after} triples (was {triples_before}).")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 6, Query for affected products AFTER inference
# MAGIC
# MAGIC Ask the same question again: "which products are affected?"
# MAGIC
# MAGIC Now the answer is populated with products that contain the recalled part.

# COMMAND ----------

results = g.query(query)
affected_after = [str(row["product"]).split("/")[-1] for row in results]

print(f"Products affected (after inference):")
if affected_after:
    for product in sorted(affected_after):
        print(f"  {product}")
else:
    print("  (no results)")

print(f"\nTotal affected: {len(affected_after)} products derived from the recall of {recalled_part}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## What you learned
# MAGIC
# MAGIC You defined a business rule as a logical implication (if-then), asserted a single fact (a part is recalled), and used forward chaining to derive all consequences. The inference engine automatically found all products containing that part and marked them as affected. In production, this pattern helps you:
# MAGIC
# MAGIC - Keep facts separate from rules. You record what you know (part recalled); the rules compute impact.
# MAGIC - Scale reasoning. One rule can trigger thousands of derived facts from a single assertion.
# MAGIC - Maintain auditability. The derived facts are traceable back to the rule and the assertion.
# MAGIC
# MAGIC For knowledge graphs with deeper rule chains and millions of facts, you would use a purpose-built reasoner like Apache Jena or Stardog. For the workshop, rdflib shows the mechanics directly.
