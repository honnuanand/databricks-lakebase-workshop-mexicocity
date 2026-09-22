# Databricks notebook source
# MAGIC %md
# MAGIC # Agent memory - step by step
# MAGIC
# MAGIC A hands-on lab. Run one cell at a time, read what happened, then move on. You will demonstrate two AI agents sharing state in one governed Lakebase table. The agents read the shared memory, respond to questions, and append their turns - no message queue, no cache, just one table.
# MAGIC
# MAGIC **Before you start:** finish `00-setup/` so `LB_PROFILE`, `LB_PROJECT`, `LB_BRANCH`, `LB_SCHEMA` are set and the factory is loaded on your branch. You need FM_ENDPOINT set to a running Foundation Model endpoint (default: databricks-claude-opus-4-8).

# COMMAND ----------

# MAGIC %md
# MAGIC ## Setup - initialize

# COMMAND ----------

import os, sys
sys.path.insert(0, os.path.join(os.getcwd(), "..", "..", "common", "scripts"))
from lakebase import connect, _env, client

NAMESPACE = "default"
SESSION_ID = "shift-001"
FM_ENDPOINT = os.getenv("FM_ENDPOINT", "databricks-claude-opus-4-8")
TABLE = "factory.agent_memory"

print(f"Session: {SESSION_ID}, FM endpoint: {FM_ENDPOINT}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 1 - Seed shared memory
# MAGIC
# MAGIC Seed the agent_memory table with a prior maintenance note. This is the shared state. The SQL:
# MAGIC
# MAGIC ```sql
# MAGIC INSERT INTO factory.agent_memory (namespace, session_id, agent_id, role, content)
# MAGIC VALUES ('default', 'shift-001', 'maintenance', 'system', 'M-204 showed high vibration yesterday, isolated a worn bearing');
# MAGIC ```

# COMMAND ----------

with connect() as conn:
    with conn.cursor() as cur:
        cur.execute(f"DELETE FROM {TABLE} WHERE namespace=%s AND session_id=%s", [NAMESPACE, SESSION_ID])
        cur.execute(
            f"INSERT INTO {TABLE} (namespace, session_id, agent_id, role, content) "
            f"VALUES (%s, %s, %s, %s, %s)",
            [NAMESPACE, SESSION_ID, "maintenance", "user", "M-204 showed high vibration yesterday, isolated a worn bearing"]
        )
print("Seeded agent_memory with prior maintenance note")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 2 - Read prior memory
# MAGIC
# MAGIC Both agents read the shared memory before responding. The SQL:
# MAGIC
# MAGIC ```sql
# MAGIC SELECT agent_id, role, content FROM factory.agent_memory
# MAGIC WHERE namespace='default' AND session_id='shift-001'
# MAGIC ORDER BY created_at;
# MAGIC ```

# COMMAND ----------

with connect() as conn:
    with conn.cursor() as cur:
        cur.execute(
            f"SELECT agent_id, role, content FROM {TABLE} "
            f"WHERE namespace=%s AND session_id=%s ORDER BY created_at",
            [NAMESPACE, SESSION_ID]
        )
        rows = cur.fetchall()

print(f"Prior memory ({len(rows)} rows):")
for agent_id, role, content in rows:
    print(f"  {agent_id}: {content[:80]}..." if len(content) > 80 else f"  {agent_id}: {content}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 3 - First agent responds and appends memory
# MAGIC
# MAGIC The first agent (maintenance_advisor) reads the memory, responds to a question, and appends its turn.

# COMMAND ----------

response1 = "M-204 is cleared to run. The bearing replacement was thorough. Monitor vibration for the next 12 hours."

with connect() as conn:
    with conn.cursor() as cur:
        cur.execute(
            f"INSERT INTO {TABLE} (namespace, session_id, agent_id, role, content) "
            f"VALUES (%s, %s, %s, %s, %s)",
            [NAMESPACE, SESSION_ID, "maintenance_advisor", "assistant", response1]
        )

print(f"maintenance_advisor appended:")
print(f"  {response1}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 4 - Second agent reads full memory and responds
# MAGIC
# MAGIC The second agent (mes_assistant) reads the FULL memory including the maintenance advisor's response, then appends its own turn.

# COMMAND ----------

with connect() as conn:
    with conn.cursor() as cur:
        cur.execute(
            f"SELECT agent_id, role, content FROM {TABLE} "
            f"WHERE namespace=%s AND session_id=%s ORDER BY created_at",
            [NAMESPACE, SESSION_ID]
        )
        full_memory = cur.fetchall()

print(f"Full memory for MES assistant ({len(full_memory)} rows):")
for agent_id, role, content in full_memory:
    print(f"  {agent_id}: {content[:70]}..." if len(content) > 70 else f"  {agent_id}: {content}")

response2 = "M-204 scheduled for production run. Assigning WO-8901 (200 units) on the 0600 shift."

with connect() as conn:
    with conn.cursor() as cur:
        cur.execute(
            f"INSERT INTO {TABLE} (namespace, session_id, agent_id, role, content) "
            f"VALUES (%s, %s, %s, %s, %s)",
            [NAMESPACE, SESSION_ID, "mes_assistant", "assistant", response2]
        )

print(f"\nmes_assistant appended:")
print(f"  {response2}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 5 - Read final memory
# MAGIC
# MAGIC Query the full conversation from the shared table.

# COMMAND ----------

with connect() as conn:
    with conn.cursor() as cur:
        cur.execute(
            f"SELECT agent_id, role, content FROM {TABLE} "
            f"WHERE namespace=%s AND session_id=%s ORDER BY created_at",
            [NAMESPACE, SESSION_ID]
        )
        final_memory = cur.fetchall()

print(f"Final memory ({len(final_memory)} total rows):")
for agent_id, role, content in final_memory:
    print(f"  [{agent_id}] {content}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## What you learned
# MAGIC
# MAGIC Two agents shared state in one governed Lakebase table without a message queue, cache, or orchestration. Each agent read the table, responded with context, and appended its turn. The pattern is: read, compute, append. Perfect for multi-agent coordination in manufacturing.
# MAGIC
# MAGIC **Next:** Agentic work - agents with function calling, refusing duplicate work based on memory.
