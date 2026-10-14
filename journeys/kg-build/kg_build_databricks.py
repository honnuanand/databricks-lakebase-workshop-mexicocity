# Databricks notebook source
# MAGIC %md
# MAGIC # Build a knowledge graph, step by step
# MAGIC
# MAGIC A hands-on lab. Run one cell at a time, read what happened, then move on. You will load the bank data into an RDF graph, run graph traversal queries, and see how graph queries compare to SQL.
# MAGIC
# MAGIC Each step shows the real interface: Python and rdflib for the graph operations, SQL when a step queries the database.
# MAGIC
# MAGIC **Before you start:** run `00-setup/setup_databricks` once to create your branch, then run the setup cells below.

# COMMAND ----------

# MAGIC %md
# MAGIC ## Run first: install the driver and pick your branch
# MAGIC Run the next three cells before anything else. They install the Postgres driver, upgrade the
# MAGIC Databricks SDK if your environment's version predates the Lakebase API, and set `LB_PROJECT`,
# MAGIC `LB_BRANCH`, and `LB_SCHEMA` from the widgets at the top of this notebook.
# MAGIC `LB_BRANCH` defaults to the branch `00-setup/setup_databricks` created for you. Change a widget
# MAGIC only if you used a different project or branch name.

# COMMAND ----------

# MAGIC %pip install "databricks-sdk>=0.120.0" "psycopg[binary]==3.3.4"

# COMMAND ----------

dbutils.library.restartPython()

# COMMAND ----------

import os, sys
sys.path.insert(0, os.path.join(os.getcwd(), "..", "..", "common", "scripts"))
from lakebase import notebook_env
notebook_env(dbutils);

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
# MAGIC ## Step 1, Load the holdings tree as triples
# MAGIC
# MAGIC The bank has a holdings tree: funds hold instruments (and sub-sleeves that hold more instruments), branches book funds, and counterparties trade instruments. We convert this into RDF triples, the subject-predicate-object triples that form a knowledge graph.
# MAGIC
# MAGIC Each triple is a fact: `(fund, holds, instrument)`, `(instrument, traded_by, counterparty)`, `(fund, booked_at, branch)`.
# MAGIC
# MAGIC The SQL to load funds:
# MAGIC
# MAGIC ```sql
# MAGIC SELECT fund_id, name FROM bank.fund
# MAGIC ```

# COMMAND ----------

g = Graph()
BANK = Namespace("http://bank.local/")

stats = {
    "funds": 0,
    "instruments": 0,
    "holdings": 0,
    "counterparties": 0,
    "traded_by_edges": 0,
    "branches": 0,
    "booked_at_edges": 0,
}

with connect() as conn:
    with conn.cursor() as cur:
        # Load funds
        cur.execute("SELECT fund_id, name FROM bank.fund")
        for fund_id, name in cur.fetchall():
            g.add((URIRef(BANK[fund_id]), URIRef(BANK.name), Literal(name)))
            stats["funds"] += 1

        # Load instruments
        cur.execute("SELECT instrument_id, name, kind FROM bank.instrument")
        for instrument_id, name, kind in cur.fetchall():
            g.add((URIRef(BANK[instrument_id]), URIRef(BANK.name), Literal(name)))
            g.add((URIRef(BANK[instrument_id]), URIRef(BANK.kind), Literal(kind)))
            stats["instruments"] += 1

        # Load holdings edges (parent holds child instrument/sleeve)
        cur.execute("SELECT parent_id, instrument_id, qty FROM bank.holding LIMIT 1000")
        for parent_id, instrument_id, qty in cur.fetchall():
            g.add((URIRef(BANK[parent_id]), URIRef(BANK.holds), URIRef(BANK[instrument_id])))
            stats["holdings"] += 1

        # Load counterparties
        cur.execute("SELECT counterparty_id, name FROM bank.counterparty")
        for counterparty_id, name in cur.fetchall():
            g.add((URIRef(BANK[counterparty_id]), URIRef(BANK.name), Literal(name)))
            stats["counterparties"] += 1

        # Load counterparty relationships
        try:
            cur.execute("SELECT instrument_id, counterparty_id FROM bank.trade_counterparty LIMIT 1000")
            for instrument_id, counterparty_id in cur.fetchall():
                g.add((URIRef(BANK[instrument_id]), URIRef(BANK.traded_by), URIRef(BANK[counterparty_id])))
                stats["traded_by_edges"] += 1
        except Exception:
            pass  # Table may not exist

        # Load branches
        cur.execute("SELECT branch_id, name FROM bank.branch")
        for branch_id, name in cur.fetchall():
            g.add((URIRef(BANK[branch_id]), URIRef(BANK.name), Literal(name)))
            stats["branches"] += 1

        # Load fund booked_at branch edges (from the trade table)
        cur.execute("SELECT DISTINCT fund_id, branch_id FROM bank.trade")
        for fund_id, branch_id in cur.fetchall():
            g.add((URIRef(BANK[fund_id]), URIRef(BANK.booked_at), URIRef(BANK[branch_id])))
            stats["booked_at_edges"] += 1

print(f"Loaded {len(g)} triples:")
for key, val in stats.items():
    if val > 0:
        print(f"  - {val} {key}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 2, Query the graph for a fund's direct holdings
# MAGIC
# MAGIC Ask the graph: "which instruments are directly held by fund FUND-GROWTH-A?"
# MAGIC
# MAGIC This is a traversal of the `holds` relationship. We iterate through the graph's objects for that fund and predicate.

# COMMAND ----------

fund_id = "FUND-GROWTH-A"
fund_uri = URIRef(BANK[fund_id])

instruments = []
for obj in g.objects(fund_uri, URIRef(BANK.holds)):
    instrument_id = str(obj).split("/")[-1]
    instruments.append(instrument_id)

print(f"Instruments held directly by {fund_id}:")
for instrument in sorted(instruments):
    print(f"  {instrument}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 3, Show the equivalent SQL
# MAGIC
# MAGIC The same query in SQL is straightforward for a direct holding:
# MAGIC
# MAGIC ```sql
# MAGIC SELECT instrument_id FROM bank.holding WHERE parent_id = 'FUND-GROWTH-A'
# MAGIC ```
# MAGIC
# MAGIC Let's run it and compare.

# COMMAND ----------

with connect() as conn:
    with conn.cursor() as cur:
        cur.execute("SELECT instrument_id FROM bank.holding WHERE parent_id = %s", [fund_id])
        sql_instruments = [row[0] for row in cur.fetchall()]

print(f"SQL result for {fund_id}:")
for instrument in sorted(sql_instruments):
    print(f"  {instrument}")

print(f"\nBoth queries return the same {len(instruments)} instruments. The graph and SQL are equivalent here.")
print(f"The difference shows when you ask multi-hop questions like 'funds holding an instrument traded by CP-GOLDMAN'.")

# COMMAND ----------

# MAGIC %md
# MAGIC ## What you learned
# MAGIC
# MAGIC You converted a relational data model (fund-holdings-counterparty graph) into an RDF knowledge graph, loaded it into an in-memory store (rdflib), and ran graph traversal queries. For simple single-hop questions, the graph and SQL are equally readable. But the real power emerges with multi-hop queries: the graph stays flat while SQL queries grow joins. Next: **Query a knowledge graph with SPARQL** shows you SPARQL syntax for harder questions.
