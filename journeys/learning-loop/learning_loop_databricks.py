# Databricks notebook source
# MAGIC %md
# MAGIC # Learning loop - step by step
# MAGIC
# MAGIC A hands-on lab. Run one cell at a time, read what happened, then move on. You will demonstrate a closed-loop learning system: seed maintenance write-ups, extract structured data with AI, route by confidence (high=auto, low=review), simulate human correction, and analyze accuracy and drift.
# MAGIC
# MAGIC **Before you start:** finish `00-setup/` so `LB_PROFILE`, `LB_PROJECT`, `LB_BRANCH`, `LB_SCHEMA` are set and the factory is loaded on your branch.

# COMMAND ----------

# MAGIC %md
# MAGIC ## Setup - initialize

# COMMAND ----------

import os, sys
sys.path.insert(0, os.path.join(os.getcwd(), "..", "..", "common", "scripts"))
from lakebase import connect, _env, client

CONF_THRESHOLD = 0.75
TABLE = "bank.case_note"
print("Learning loop: seed -> extract -> route -> correct -> analyze")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 1 - Seed maintenance write-ups
# MAGIC
# MAGIC Load real-world messy maintenance notes. Some clear, some ambiguous. The SQL:
# MAGIC
# MAGIC ```sql
# MAGIC INSERT INTO bank.case_note (account_id, writeup)
# MAGIC VALUES ('ACCT-100240', 'Hydraulic line on leg B leaking, found ice on exterior, isolated line, monitor pressure.');
# MAGIC ```

# COMMAND ----------

# Add the ALTER TABLE statement to ensure status column exists
with connect() as conn:
    with conn.cursor() as cur:
        cur.execute(f"ALTER TABLE {TABLE} ADD COLUMN IF NOT EXISTS status TEXT")

# Real factory machines and their maintenance notes
writeups = [
    ("ACCT-100240", "Hydraulic line to the bearing housing leaking on the press downstroke, isolated the line, monitor pressure."),
    ("ACCT-300421", "CNC spindle running hot, thermal alarm at 71C, coolant flow low, replace pump at next PM."),
    ("ACCT-200311", "Tool changer intermittent on the CNC, last 3 cycles hung; swap the actuator?"),
    ("ACCT-100235", "Robot arm slow to home, ~40s hesitation on startup x2, investigate the drive."),
    ("ACCT-100240", "Something off with the thing on the right side of the press, maybe hydraulics? not sure"),
]

with connect() as conn:
    with conn.cursor() as cur:
        cur.execute(f"DELETE FROM {TABLE}")
        for mid, writeup in writeups:
            cur.execute(f"INSERT INTO {TABLE} (account_id, writeup) VALUES (%s, %s)", [mid, writeup])

print(f"Seeded {len(writeups)} maintenance write-ups from factory machines")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 2 - Show the write-ups
# MAGIC
# MAGIC Query the seeded data. The SQL:
# MAGIC
# MAGIC ```sql
# MAGIC SELECT account_id, writeup FROM bank.case_note ORDER BY note_id;
# MAGIC ```

# COMMAND ----------

with connect() as conn:
    with conn.cursor() as cur:
        cur.execute(f"SELECT account_id, writeup FROM {TABLE} ORDER BY note_id")
        rows = cur.fetchall()

print(f"Maintenance write-ups ({len(rows)} total):")
for mid, writeup in rows:
    print(f"  {mid}: {writeup[:70]}..." if len(writeup) > 70 else f"  {mid}: {writeup}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 3 - Simulate extraction with confidence routing
# MAGIC
# MAGIC Extract structured data (system, defect, action, confidence) from each write-up. Route high-confidence to auto-accept, low-confidence to manual review.

# COMMAND ----------

extractions = [
    {"system": "hydraulics", "defect": "line_leak", "action": "isolated", "confidence": 0.95, "status": "auto_accepted"},
    {"system": "cnc_spindle", "defect": "overheating", "action": "schedule_pump_replace", "confidence": 0.89, "status": "auto_accepted"},
    {"system": "tool_changer", "defect": "intermittent_actuator", "action": "investigate", "confidence": 0.68, "status": "needs_review"},
    {"system": "robot_arm", "defect": "slow_homing", "action": "investigate_drive", "confidence": 0.80, "status": "auto_accepted"},
    {"system": "unknown", "defect": "unknown", "action": "investigate", "confidence": 0.38, "status": "needs_review"},
]

auto_count = sum(1 for e in extractions if e["status"] == "auto_accepted")
review_count = sum(1 for e in extractions if e["status"] == "needs_review")

print(f"Extraction results:")
print(f"  Auto-accepted (conf > {CONF_THRESHOLD}): {auto_count}")
print(f"  Needs review (conf <= {CONF_THRESHOLD}): {review_count}")

print(f"\nAuto-accepted entries:")
for e in extractions:
    if e["status"] == "auto_accepted":
        print(f"  {e['system']}/{e['defect']}: conf={e['confidence']:.2f}")

print(f"\nNeeds review:")
for e in extractions:
    if e["status"] == "needs_review":
        print(f"  {e['system']}/{e['defect']}: conf={e['confidence']:.2f}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 4 - Simulate human correction on uncertain entries
# MAGIC
# MAGIC For entries marked 'needs_review', a human corrects them. Update the table with corrected values.

# COMMAND ----------

corrections = [
    {"note_id": 3, "correct_system": "avionics", "correct_defect": "radio_failure", "status": "human_corrected", "confidence": 0.95},
    {"note_id": 5, "correct_system": "hydraulic", "correct_defect": "unknown_leak", "status": "human_corrected", "confidence": 0.65},
]

print(f"Human corrections applied ({len(corrections)} entries):")
for corr in corrections:
    print(f"  note_id={corr['note_id']}: {corr['correct_system']}/{corr['correct_defect']}, status={corr['status']}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 5 - Analytics: accuracy and confidence distribution
# MAGIC
# MAGIC Query the maintenance_log to compute accuracy metrics and confidence distribution.

# COMMAND ----------

total_entries = len(extractions)
auto_entries = sum(1 for e in extractions if e["status"] == "auto_accepted")
review_entries = sum(1 for e in extractions if e["status"] == "needs_review")
corrected_entries = len(corrections)

avg_confidence = sum(e["confidence"] for e in extractions) / len(extractions)
high_conf = sum(1 for e in extractions if e["confidence"] >= CONF_THRESHOLD)
low_conf = sum(1 for e in extractions if e["confidence"] < CONF_THRESHOLD)

print(f"=== Learning Loop Analytics ===")
print(f"\nProcessed: {total_entries}")
print(f"  Auto-accepted: {auto_entries}")
print(f"  Needs review: {review_entries}")
print(f"  Human-corrected: {corrected_entries}")
print(f"\nConfidence Distribution:")
print(f"  High (>= {CONF_THRESHOLD}): {high_conf} ({100*high_conf/total_entries:.0f}%)")
print(f"  Low (< {CONF_THRESHOLD}): {low_conf} ({100*low_conf/total_entries:.0f}%)")
print(f"  Average: {avg_confidence:.2f}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## What you learned
# MAGIC
# MAGIC A closed-loop learning system: seed messy data, extract with AI, route by confidence, correct, and analyze. All on one table. As humans correct low-confidence extractions, the system improves: confidence grows, more auto-accepts, fewer reviews. Monitor drift (accuracy over time) to catch model decay.
# MAGIC
# MAGIC **Next:** PG vector - operational vectors for similarity search on live data.
