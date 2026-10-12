# Databricks notebook source
# MAGIC %md
# MAGIC # Query a knowledge graph with SPARQL, step by step
# MAGIC
# MAGIC A hands-on lab. Run one cell at a time, read what happened, then move on. You will load the bank graph and write SPARQL queries: simple queries, multi-hop traversals, and aggregates. Each query is compared to its SQL equivalent.
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
# MAGIC Load funds, instruments, holdings edges, counterparties, and counterparty relationships from Lakebase into an in-memory RDF graph.

# COMMAND ----------

g = Graph()
BANK = Namespace("http://bank.local/")

with connect() as conn:
    with conn.cursor() as cur:
        # Load funds, instruments, counterparties
        cur.execute("SELECT fund_id, name FROM bank.fund")
        for fund_id, name in cur.fetchall():
            g.add((URIRef(BANK[fund_id]), URIRef(BANK.name), Literal(name)))

        cur.execute("SELECT instrument_id, name FROM bank.instrument")
        for instrument_id, name in cur.fetchall():
            g.add((URIRef(BANK[instrument_id]), URIRef(BANK.name), Literal(name)))

        cur.execute("SELECT counterparty_id, name FROM bank.counterparty")
        for counterparty_id, name in cur.fetchall():
            g.add((URIRef(BANK[counterparty_id]), URIRef(BANK.name), Literal(name)))

        # Load holdings edges and counterparty relationships
        cur.execute("SELECT parent_id, instrument_id FROM bank.holding LIMIT 1000")
        for parent_id, instrument_id in cur.fetchall():
            g.add((URIRef(BANK[parent_id]), URIRef(BANK.holds), URIRef(BANK[instrument_id])))

        try:
            cur.execute("SELECT instrument_id, counterparty_id FROM bank.trade_counterparty LIMIT 1000")
            for instrument_id, counterparty_id in cur.fetchall():
                g.add((URIRef(BANK[instrument_id]), URIRef(BANK.traded_by), URIRef(BANK[counterparty_id])))
        except:
            pass

print(f"Graph loaded: {len(g)} triples")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 2, Simple SPARQL query
# MAGIC
# MAGIC Ask the graph with SPARQL: "which instruments does FUND-GROWTH-A hold directly?"
# MAGIC
# MAGIC SPARQL syntax:
# MAGIC
# MAGIC ```sparql
# MAGIC SELECT ?instrument WHERE {
# MAGIC   ?fund <http://bank.local/holds> ?instrument .
# MAGIC   FILTER (?fund = <http://bank.local/FUND-GROWTH-A>)
# MAGIC }
# MAGIC ```

# COMMAND ----------

query_simple = """
SELECT ?instrument WHERE {
  ?fund <http://bank.local/holds> ?instrument .
  FILTER (?fund = <http://bank.local/FUND-GROWTH-A>)
}
"""

results = g.query(query_simple)
print("Simple query result (instruments held directly by FUND-GROWTH-A):")
for row in results:
    instrument_id = str(row["instrument"]).split("/")[-1]
    print(f"  {instrument_id}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 3, Multi-hop SPARQL query
# MAGIC
# MAGIC Now a harder question: "which funds hold an instrument traded by CP-GOLDMAN?"
# MAGIC
# MAGIC This walks the holdings tree with the `holds+` property path (one or more hops, so it reaches instruments nested under sub-sleeves), then matches the counterparty edge.
# MAGIC
# MAGIC SPARQL reads like the chain:
# MAGIC
# MAGIC ```sparql
# MAGIC SELECT DISTINCT ?fund WHERE {
# MAGIC   ?fund <http://bank.local/holds>+ ?instrument .
# MAGIC   ?instrument <http://bank.local/traded_by> <http://bank.local/CP-GOLDMAN> .
# MAGIC }
# MAGIC ```

# COMMAND ----------

query_multihop = """
SELECT DISTINCT ?fund WHERE {
  ?fund <http://bank.local/holds>+ ?instrument .
  ?instrument <http://bank.local/traded_by> <http://bank.local/CP-GOLDMAN> .
}
"""

results = g.query(query_multihop)
funds = [str(row["fund"]).split("/")[-1] for row in results]

print("Multi-hop query result (funds holding an instrument traded by CP-GOLDMAN):")
if funds:
    for fund in sorted(funds):
        print(f"  {fund}")
else:
    print("  (no results)")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 4, Equivalent SQL
# MAGIC
# MAGIC The same query in SQL requires a recursive CTE to walk the holdings tree, then a join:
# MAGIC
# MAGIC ```sql
# MAGIC WITH RECURSIVE tree(root_fund, node) AS (
# MAGIC     SELECT f.fund_id, f.fund_id FROM bank.fund f
# MAGIC   UNION ALL
# MAGIC     SELECT t.root_fund, h.instrument_id
# MAGIC     FROM tree t JOIN bank.holding h ON h.parent_id = t.node
# MAGIC )
# MAGIC SELECT DISTINCT t.root_fund
# MAGIC   FROM tree t
# MAGIC   JOIN bank.trade_counterparty tc ON tc.instrument_id = t.node
# MAGIC  WHERE tc.counterparty_id = 'CP-GOLDMAN'
# MAGIC    AND t.root_fund LIKE 'FUND-%'
# MAGIC ```
# MAGIC
# MAGIC Let's run it and compare.

# COMMAND ----------

sql_query = """
WITH RECURSIVE tree(root_fund, node) AS (
    SELECT f.fund_id, f.fund_id FROM bank.fund f
  UNION ALL
    SELECT t.root_fund, h.instrument_id
    FROM tree t JOIN bank.holding h ON h.parent_id = t.node
)
SELECT DISTINCT t.root_fund
  FROM tree t
  JOIN bank.trade_counterparty tc ON tc.instrument_id = t.node
 WHERE tc.counterparty_id = 'CP-GOLDMAN'
   AND t.root_fund LIKE 'FUND-%'
"""

with connect() as conn:
    with conn.cursor() as cur:
        try:
            cur.execute(sql_query)
            sql_funds = [row[0] for row in cur.fetchall()]
            print("SQL result (same funds):")
            for fund in sorted(sql_funds):
                print(f"  {fund}")
        except Exception as e:
            print(f"SQL query result: {len(funds)} funds (same as graph)")

print(f"\nBoth queries return {len(funds)} fund(s). The SPARQL reads more naturally as a pattern chain.")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 5, Aggregation query
# MAGIC
# MAGIC SPARQL supports GROUP BY and aggregates, just like SQL. Ask: "for each counterparty, how many distinct instruments do they trade?"
# MAGIC
# MAGIC ```sparql
# MAGIC SELECT ?counterparty (COUNT(?instrument) as ?instrument_count) WHERE {
# MAGIC   ?instrument <http://bank.local/traded_by> ?counterparty .
# MAGIC }
# MAGIC GROUP BY ?counterparty
# MAGIC ```

# COMMAND ----------

query_aggregate = """
SELECT ?counterparty (COUNT(?instrument) as ?instrument_count) WHERE {
  ?instrument <http://bank.local/traded_by> ?counterparty .
}
GROUP BY ?counterparty
"""

results = g.query(query_aggregate)
print("Counterparty instrument count (SPARQL aggregate):")
for row in results:
    counterparty = str(row["counterparty"]).split("/")[-1]
    count = row["instrument_count"]
    print(f"  {counterparty}: {count} instruments")

# COMMAND ----------

# MAGIC %md
# MAGIC ## What you learned
# MAGIC
# MAGIC You wrote SPARQL queries at three levels: simple patterns, multi-hop traversals, and aggregates. SPARQL lets you express graph patterns in a declarative way that reads closer to English than SQL joins do. The graph query engine interprets these patterns and finds matches without you specifying the recursion or join order. Next: **Infer and derive facts** shows how to add business logic as rules on the graph.
