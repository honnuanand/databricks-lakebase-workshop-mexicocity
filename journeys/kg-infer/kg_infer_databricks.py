# Databricks notebook source
# MAGIC %md
# MAGIC # Infer and derive facts, step by step
# MAGIC
# MAGIC A hands-on lab. Run one cell at a time, read what happened, then move on. You will define business logic as forward-chaining inference rules on a knowledge graph, then apply entailment to derive new facts automatically. This is how you express "if this instrument is distressed, then any fund holding it is exposed", and let the graph reason about the consequences, following holdings through sleeves transitively.
# MAGIC
# MAGIC **Before you start:** finish `00-setup/` so `LB_PROFILE`, `LB_PROJECT`, `LB_BRANCH`, `LB_SCHEMA` are set and the bank is loaded on your branch.

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
# MAGIC ## Step 1, Load the graph from the bank
# MAGIC
# MAGIC Funds and instruments become typed nodes; each `holding` row becomes a `contains` edge. A
# MAGIC sleeve is an instrument that itself holds other instruments, so `contains` forms a tree.

# COMMAND ----------

g = Graph()
BANK = Namespace("http://bank.local/")

with connect() as conn:
    with conn.cursor() as cur:
        cur.execute("SELECT fund_id, name FROM bank.fund")
        for fund_id, name in cur.fetchall():
            g.add((URIRef(BANK[fund_id]), URIRef(BANK.type), URIRef(BANK.Fund)))
            g.add((URIRef(BANK[fund_id]), URIRef(BANK.name), Literal(name)))

        cur.execute("SELECT instrument_id, name FROM bank.instrument")
        for instrument_id, name in cur.fetchall():
            g.add((URIRef(BANK[instrument_id]), URIRef(BANK.type), URIRef(BANK.Instrument)))
            g.add((URIRef(BANK[instrument_id]), URIRef(BANK.name), Literal(name)))

        cur.execute("SELECT parent_id, instrument_id FROM bank.holding LIMIT 1000")
        for parent_id, instrument_id in cur.fetchall():
            g.add((URIRef(BANK[parent_id]), URIRef(BANK.contains), URIRef(BANK[instrument_id])))

print(f"Graph loaded: {len(g)} triples")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 2, Define a business rule: if an instrument is distressed, funds holding it are exposed

# COMMAND ----------

# The rule expressed in natural language:
# "If a fund holds an instrument, and that instrument is distressed, then the fund is exposed."
# 'contains' is transitive, so the rule chains down through sleeves.

rule_text = """
(?fund <http://bank.local/contains> ?instrument)
(?instrument <http://bank.local/distressed> true)
-> (?fund <http://bank.local/exposed> true)
"""

print("Rule defined:")
print("  If (fund holds instrument) AND (instrument is distressed)")
print("  Then (fund is exposed)")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 3, Mark an instrument as distressed
# MAGIC
# MAGIC Add a fact to the graph: INS-AAPL is distressed. Note that no fund holds INS-AAPL *directly*,
# MAGIC only through INS-SLEEVE-EQ, so a naive one-hop lookup would miss the exposure.

# COMMAND ----------

distressed_instrument = "INS-AAPL"
g.add((URIRef(BANK[distressed_instrument]), URIRef(BANK.distressed), Literal(True)))

print(f"Marked {distressed_instrument} as distressed.")
print(f"Graph now has {len(g)} triples.")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 4, Query for exposed funds BEFORE inference
# MAGIC
# MAGIC Ask: "which funds are marked as exposed?"
# MAGIC
# MAGIC The answer is empty, because we never explicitly added any fund as exposed. We only marked an instrument as distressed.

# COMMAND ----------

query = """
SELECT ?fund WHERE {
  ?fund <http://bank.local/exposed> ?status .
}
"""

results = g.query(query)
exposed_before = [str(row["fund"]).split("/")[-1] for row in results]

print(f"Funds exposed (before inference): {exposed_before}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 5, Apply inference
# MAGIC
# MAGIC Use forward chaining to apply the rule. The reasoner walks `contains` transitively from each fund and marks it exposed if it reaches a distressed instrument anywhere in its holdings tree.

# COMMAND ----------

triples_before = len(g)

# Collect all distressed instruments (subjects of distressed = true)
distressed = {s for s, o in g.subject_objects(URIRef(BANK.distressed))
              if o == Literal(True)}

print(f"Found {len(distressed)} distressed instruments: {[str(p).split('/')[-1] for p in distressed]}")

# For each fund, walk contains* and mark it exposed if it reaches a distressed instrument
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

# Iterate over all funds and mark exposed ones
fund_count = 0
for fund in g.subjects(URIRef(BANK.type), URIRef(BANK.Fund)):
    fund_count += 1
    if reaches(fund, distressed):
        g.add((fund, URIRef(BANK.exposed), Literal(True)))

triples_after = len(g)
derived = triples_after - triples_before

print(f"Inference applied.")
print(f"  Checked {fund_count} funds")
print(f"  Derived {derived} new triples.")
print(f"  Graph now has {triples_after} triples (was {triples_before}).")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 6, Query for exposed funds AFTER inference
# MAGIC
# MAGIC Ask the same question again: "which funds are exposed?"
# MAGIC
# MAGIC Now the answer is populated with funds that hold the distressed instrument, directly or through a sleeve.

# COMMAND ----------

results = g.query(query)
exposed_after = [str(row["fund"]).split("/")[-1] for row in results]

print(f"Funds exposed (after inference):")
if exposed_after:
    for fund in sorted(exposed_after):
        print(f"  {fund}")
else:
    print("  (no results)")

print(f"\nTotal exposed: {len(exposed_after)} funds derived from the distress of {distressed_instrument}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## What you learned
# MAGIC
# MAGIC You defined a business rule as a logical implication (if-then), asserted a single fact (an instrument is distressed), and used forward chaining to derive all consequences. The inference engine automatically found every fund holding that instrument, even two hops down through a sleeve, and marked it exposed. In production, this pattern helps you:
# MAGIC
# MAGIC - Keep facts separate from rules. You record what you know (instrument distressed); the rules compute exposure.
# MAGIC - Scale reasoning. One rule can trigger thousands of derived facts from a single assertion.
# MAGIC - Maintain auditability. The derived facts are traceable back to the rule and the assertion.
# MAGIC
# MAGIC For knowledge graphs with deeper rule chains and millions of facts, you would use a purpose-built reasoner like Apache Jena or Stardog. For the workshop, rdflib shows the mechanics directly.
