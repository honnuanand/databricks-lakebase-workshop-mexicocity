# Databricks notebook source
# MAGIC %md
# MAGIC # Agentic work - step by step
# MAGIC
# MAGIC A hands-on lab. Run one cell at a time, read what happened, then move on. You will demonstrate an agent with real function calling that reads machine state, decides to assign work, and remembers what it did in a table. On the second call, the agent refuses to double-assign based on memory.
# MAGIC
# MAGIC **Before you start:** finish `00-setup/` so `LB_PROFILE`, `LB_PROJECT`, `LB_BRANCH`, `LB_SCHEMA` are set and the factory is loaded on your branch.

# COMMAND ----------

# MAGIC %md
# MAGIC ## Setup - initialize

# COMMAND ----------

import os, sys
sys.path.insert(0, os.path.join(os.getcwd(), "..", "..", "common", "scripts"))
from lakebase import connect, _env, client

NAMESPACE = "default"
SESSION_ID = "shift-001"
WO_ID = "WO-1001"
MACHINE_ID = "M-204"
TABLE_MEMORY = "factory.agent_memory"
TABLE_MACHINE = "factory.machine"
TABLE_OPERATION = "factory.operation"

print(f"Work order: {WO_ID}, Machine: {MACHINE_ID}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 0 - Setup: create work order

# COMMAND ----------

with connect() as conn:
    with conn.cursor() as cur:
        # Get a product from the factory
        cur.execute("SELECT product_id FROM factory.product ORDER BY product_id LIMIT 1")
        product = cur.fetchone()[0]
        
        # Clear prior operations for this work order
        cur.execute("DELETE FROM factory.operation WHERE wo_id = %s", [WO_ID])
        
        # Create or ensure the work order exists
        cur.execute(
            '''INSERT INTO factory.work_order (wo_id, plant_id, product_id, qty, status, due_ts)
               VALUES (%s, 'PL-DETROIT', %s, 20, 'released', now() + interval '1 day')
               ON CONFLICT (wo_id) DO UPDATE SET status = 'released' ''',
            [WO_ID, product]
        )

print(f"Prepared: {WO_ID} ready for assignment")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 1 - Show initial state
# MAGIC
# MAGIC Check the machine status and work order status. The SQL:
# MAGIC
# MAGIC ```sql
# MAGIC SELECT machine_id, status, health_pct FROM factory.machine WHERE machine_id='M-204';
# MAGIC SELECT wo_id, product_id, qty, status FROM factory.work_order WHERE wo_id='WO-1001';
# MAGIC ```

# COMMAND ----------

with connect() as conn:
    with conn.cursor() as cur:
        cur.execute(f"SELECT machine_id, status, health_pct FROM {TABLE_MACHINE} WHERE machine_id=%s", [MACHINE_ID])
        mach = cur.fetchone()
        cur.execute(f"SELECT wo_id, product_id, qty, status FROM factory.work_order WHERE wo_id=%s", [WO_ID])
        wo = cur.fetchone()

print(f"Initial state:")
print(f"  {MACHINE_ID}: {mach[1]}, {mach[2]}%")
print(f"  {WO_ID}: {wo[3]}, {wo[2]} units")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 2 - Agent's function call 1: read available machines
# MAGIC
# MAGIC The agent queries for machines that are healthy and ready for work. The SQL:
# MAGIC
# MAGIC ```sql
# MAGIC SELECT machine_id, status, health_pct FROM factory.machine
# MAGIC WHERE status='healthy' AND health_pct >= 90.0 LIMIT 10;
# MAGIC ```

# COMMAND ----------

with connect() as conn:
    with conn.cursor() as cur:
        cur.execute(
            f"SELECT machine_id, status, health_pct FROM {TABLE_MACHINE} "
            f"WHERE status='healthy' AND health_pct >= 90.0 LIMIT 10"
        )
        available = cur.fetchall()

print(f"Available machines:")
for row in available:
    print(f"  {row[0]}: {row[1]}, {row[2]}%")

if any(m[0] == MACHINE_ID for m in available):
    print(f"\n{MACHINE_ID} is available.")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 3 - Agent's function call 2: assign work order
# MAGIC
# MAGIC The agent assigns the work order to the machine by creating an operation. The SQL:
# MAGIC
# MAGIC ```sql
# MAGIC INSERT INTO factory.operation (op_id, wo_id, machine_id, seq, status)
# MAGIC VALUES (gen_random_uuid()::text, 'WO-1001', 'M-204', 1, 'pending');
# MAGIC ```

# COMMAND ----------

with connect() as conn:
    with conn.cursor() as cur:
        cur.execute(
            f"""INSERT INTO {TABLE_OPERATION}
                    (op_id, wo_id, machine_id, seq, status, starts_at, ends_at)
               VALUES (%s, %s, %s, 1, 'pending',
                       now() + interval '7 days', now() + interval '7 days' + interval '2 hours')
               ON CONFLICT (op_id) DO NOTHING""",
            [f"OP-{WO_ID}", WO_ID, MACHINE_ID]
        )

print(f"Assigned {WO_ID} to {MACHINE_ID}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 4 - Agent remembers what it did
# MAGIC
# MAGIC The agent appends to the memory table. The SQL:
# MAGIC
# MAGIC ```sql
# MAGIC INSERT INTO factory.agent_memory (namespace, session_id, agent_id, role, content)
# MAGIC VALUES ('default', 'shift-001', 'mes_agent', 'assistant', 'Assigned WO-1001 to M-204');
# MAGIC ```

# COMMAND ----------

with connect() as conn:
    with conn.cursor() as cur:
        cur.execute(
            f"INSERT INTO {TABLE_MEMORY} (namespace, session_id, agent_id, role, content) "
            f"VALUES (%s, %s, %s, %s, %s)",
            [NAMESPACE, SESSION_ID, "mes_agent", "assistant", f"Assigned {WO_ID} to {MACHINE_ID}"]
        )

print(f"Remembered assignment in agent_memory")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 5 - Agent called again: refuses duplicate
# MAGIC
# MAGIC On a second call, the agent reads memory, finds the assignment already exists, and refuses to double-assign.

# COMMAND ----------

with connect() as conn:
    with conn.cursor() as cur:
        cur.execute(
            f"SELECT content FROM {TABLE_MEMORY} "
            f"WHERE namespace=%s AND session_id=%s AND agent_id='mes_agent' "
            f"AND content LIKE %s",
            [NAMESPACE, SESSION_ID, f"%{WO_ID}%"]
        )
        prior_assignment = cur.fetchone()

if prior_assignment:
    print(f"Agent reads memory: \"{prior_assignment[0]}\"")
    print(f"REFUSE: {WO_ID} is already assigned. No double-assign.")
else:
    print(f"No prior assignment found")

# COMMAND ----------

# MAGIC %md
# MAGIC ## What you learned
# MAGIC
# MAGIC An agent with function calling used a Lakebase table as its memory: query machines, assign work, remember the assignment. On the second call, it read its prior memory and refused to double-assign. This pattern scales to complex workflows: maintenance, quality control, scheduling - all agents consulting the same table for idempotent, coordinated work.
# MAGIC
# MAGIC **Next:** Learning loop - extract, route by confidence, correct, and analyze on one table.
