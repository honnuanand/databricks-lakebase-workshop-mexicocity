# Databricks notebook source
# MAGIC %md
# MAGIC # Learning loop - step by step
# MAGIC
# MAGIC A hands-on lab. Run one cell at a time, read what happened, then move on. You will demonstrate a closed-loop learning system: seed analyst case notes, extract structured data with AI, route by confidence (high=auto, low=review), simulate human correction, and analyze accuracy and drift.
# MAGIC
# MAGIC **Before you start:** run `00-setup/setup_databricks` once to create your branch, then run the setup cells below. The extraction step calls a Foundation Model endpoint (FM_ENDPOINT, default: databricks-claude-opus-4-8); if it is unavailable, the notebook uses fixed extractions instead.

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
# MAGIC ## Setup - initialize

# COMMAND ----------

import os, sys, json
import requests
sys.path.insert(0, os.path.join(os.getcwd(), "..", "..", "common", "scripts"))
from lakebase import connect, _env, client

FM_ENDPOINT = os.getenv("FM_ENDPOINT", "databricks-claude-opus-4-8")
CONF_THRESHOLD = 0.75
TABLE = "bank.case_note"

def fm_call(messages, max_tokens=300):
    """Call the Foundation Model API; return text, or None to use the fallback."""
    try:
        w = client()
        tok = w.config.authenticate()["Authorization"][len("Bearer "):]
        r = requests.post(
            f"{w.config.host}/serving-endpoints/{FM_ENDPOINT}/invocations",
            headers={"Authorization": f"Bearer {tok}", "Content-Type": "application/json"},
            json={"messages": messages, "max_tokens": max_tokens},
            timeout=60,
        )
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"]
    except Exception as e:
        print(f"  (FM API unavailable: {e}; using fallback)")
        return None

print("Learning loop: seed -> extract -> route -> correct -> analyze")
print(f"FM endpoint: {FM_ENDPOINT}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 1 - Seed analyst case notes
# MAGIC
# MAGIC Load real-world messy fraud/AML case notes. Some clear, some ambiguous. The SQL:
# MAGIC
# MAGIC ```sql
# MAGIC INSERT INTO bank.case_note (account_id, writeup)
# MAGIC VALUES ('CTA-100240', 'Three card-not-present charges overnight to a foreign merchant the customer does not recognize, velocity spike. Froze the card and opened a reissue.');
# MAGIC ```

# COMMAND ----------

# Add the status column if it is not there yet (idempotent).
with connect() as conn:
    with conn.cursor() as cur:
        cur.execute(f"ALTER TABLE {TABLE} ADD COLUMN IF NOT EXISTS status TEXT")

# Real accounts and their analyst case notes.
writeups = [
    ("CTA-100240", "Three card-not-present charges overnight to a foreign merchant the customer does not recognize, velocity spike. Froze the card and opened a reissue."),
    ("CTA-300421", "Four outbound SPEI transfers in two days to a CLABE registered yesterday, each just under the reporting threshold. Possible structuring, referred to the PLD (AML) team."),
    ("CTA-200311", "Customer disputes a CoDi payment they say was charged twice at a Monterrey store; the merchant's receipt is ambiguous. Needs a closer look at the settlement records."),
    ("CTA-100235", "A few small USD charges followed by a larger one, same online merchant. Could be card testing, or the customer is traveling in the US. Hold for review."),
    ("CTA-100240", "Something looked off on the account this morning, maybe a login from another city? not sure, flagging it."),
]

with connect() as conn:
    with conn.cursor() as cur:
        cur.execute(f"DELETE FROM {TABLE}")
        for mid, writeup in writeups:
            cur.execute(f"INSERT INTO {TABLE} (account_id, writeup) VALUES (%s, %s)", [mid, writeup])

print(f"Seeded {len(writeups)} analyst case notes")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 2 - Show the case notes
# MAGIC
# MAGIC Query the seeded data. The SQL:
# MAGIC
# MAGIC ```sql
# MAGIC SELECT note_id, account_id, writeup FROM bank.case_note ORDER BY note_id;
# MAGIC ```

# COMMAND ----------

with connect() as conn:
    with conn.cursor() as cur:
        cur.execute(f"SELECT note_id, account_id, writeup FROM {TABLE} ORDER BY note_id")
        rows = cur.fetchall()

print(f"Analyst case notes ({len(rows)} total):")
for note_id, mid, writeup in rows:
    short = writeup[:70] + "..." if len(writeup) > 70 else writeup
    print(f"  {note_id} {mid}: {short}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 3 - Extraction with confidence routing
# MAGIC
# MAGIC Extract structured data (category, finding, action, confidence) from each case note, then write
# MAGIC the extraction and routing status back to the same table. The model
# MAGIC (`FM_ENDPOINT`, default `databricks-claude-opus-4-8`) reads each note and returns JSON with its
# MAGIC own confidence, so your counts can differ slightly from run to run. If the endpoint is
# MAGIC unavailable, a fixed set of extractions is used instead. High confidence auto-accepts; low
# MAGIC confidence routes to review.

# COMMAND ----------

EXTRACT_PROMPT = (
    "You are a fraud/AML triage assistant. From a free-text analyst case note, "
    "extract category (fraud, AML, dispute, or other), finding (the specific issue, as a short "
    "snake_case label such as card_compromise or possible_structuring), "
    "action (what was done), and confidence (0-1, how certain you are the extraction "
    "is correct and unambiguous). "
    "Respond with ONLY a JSON object: {\"category\": \"...\", \"finding\": \"...\", "
    "\"action\": \"...\", \"confidence\": 0.X}"
)

# Fallback, one per case note in note_id order, used only if the model call fails. These mirror
# what the model returns for notes this clear and this vague: the card-fraud and AML notes are
# unambiguous, the rest are not.
fallback = [
    {"category": "fraud",   "finding": "card_compromise",       "action": "froze_and_reissued", "confidence": 0.93},
    {"category": "AML",     "finding": "possible_structuring",  "action": "referred_to_aml",    "confidence": 0.88},
    {"category": "dispute", "finding": "double_charge_claim",   "action": "review_settlement",  "confidence": 0.64},
    {"category": "fraud",   "finding": "possible_card_testing", "action": "hold_for_review",    "confidence": 0.66},
    {"category": "fraud",   "finding": "unclear",               "action": "investigate",        "confidence": 0.28},
]

def extract(writeup, i):
    """Ask the model for an extraction; parse its JSON, or use the fallback."""
    response = fm_call([{"role": "system", "content": EXTRACT_PROMPT},
                        {"role": "user", "content": writeup}])
    if response is None:
        return dict(fallback[i])
    try:
        e = json.loads(response[response.find("{"):response.rfind("}") + 1])
    except Exception:
        e = {"category": "?", "finding": "(parse failed)", "action": "?", "confidence": 0.3}
    e["confidence"] = max(0.0, min(1.0, float(e.get("confidence", 0.5))))
    return e

with connect() as conn:
    with conn.cursor() as cur:
        cur.execute(f"SELECT note_id, writeup FROM {TABLE} ORDER BY note_id")
        notes = cur.fetchall()

extractions = [extract(writeup, i) for i, (_, writeup) in enumerate(notes)]

with connect() as conn:
    with conn.cursor() as cur:
        for (note_id, _), e in zip(notes, extractions):
            status = "auto_accepted" if e["confidence"] >= CONF_THRESHOLD else "needs_review"
            e["status"] = status
            cur.execute(
                f"UPDATE {TABLE} SET category=%s, finding=%s, action=%s, confidence=%s, status=%s WHERE note_id=%s",
                [e["category"], e["finding"], e["action"], e["confidence"], status, note_id])

auto_count = sum(1 for e in extractions if e["status"] == "auto_accepted")
review_count = sum(1 for e in extractions if e["status"] == "needs_review")

print(f"Extraction results:")
print(f"  Auto-accepted (conf >= {CONF_THRESHOLD}): {auto_count}")
print(f"  Needs review   (conf <  {CONF_THRESHOLD}): {review_count}")

print(f"\nAuto-accepted entries:")
for e in extractions:
    if e["status"] == "auto_accepted":
        print(f"  {e['category']}/{e['finding']}: conf={e['confidence']:.2f}")

print(f"\nNeeds review:")
for e in extractions:
    if e["status"] == "needs_review":
        print(f"  {e['category']}/{e['finding']}: conf={e['confidence']:.2f}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 4 - Human correction on an uncertain entry
# MAGIC
# MAGIC An analyst reviews the lowest-confidence `needs_review` note and makes its extraction specific.
# MAGIC The correction writes back to the same row with `status='corrected'`; the AI's original
# MAGIC extraction and the human's correction live in one place.

# COMMAND ----------

with connect() as conn:
    with conn.cursor() as cur:
        cur.execute(
            f"SELECT note_id FROM {TABLE} WHERE status='needs_review' ORDER BY confidence ASC NULLS FIRST LIMIT 1")
        row = cur.fetchone()
        if row:
            note_id = row[0]
            cur.execute(
                f"UPDATE {TABLE} SET category=%s, finding=%s, status=%s WHERE note_id=%s",
                ["fraud", "account_takeover_suspected", "corrected", note_id])
            print(f"Analyst corrected note_id={note_id}: category=fraud, finding=account_takeover_suspected, status=corrected")
        else:
            print("No needs_review entries to correct")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 5 - Analytics: accuracy and confidence distribution
# MAGIC
# MAGIC Query the same `case_note` table to compute routing counts and confidence stats. No separate
# MAGIC analytics store: the operational table *is* the analytics source.

# COMMAND ----------

with connect() as conn:
    with conn.cursor() as cur:
        cur.execute(f"SELECT status, COUNT(*) FROM {TABLE} WHERE status IS NOT NULL GROUP BY status")
        by_status = {r[0]: r[1] for r in cur.fetchall()}
        cur.execute(f"SELECT AVG(confidence) FROM {TABLE} WHERE status='auto_accepted'")
        avg_auto = cur.fetchone()[0]
        cur.execute(f"SELECT AVG(confidence) FROM {TABLE} WHERE status='needs_review'")
        avg_review = cur.fetchone()[0]
        cur.execute(f"SELECT COUNT(*) FROM {TABLE} WHERE status IS NOT NULL")
        total = cur.fetchone()[0]

print("=== Learning Loop Analytics ===")
print(f"\nProcessed: {total}")
print(f"  Auto-accepted: {by_status.get('auto_accepted', 0)}")
print(f"  Needs review:  {by_status.get('needs_review', 0)}")
print(f"  Corrected:     {by_status.get('corrected', 0)}")
if avg_auto is not None:
    print(f"\nAvg confidence (auto-accepted): {float(avg_auto):.3f}")
if avg_review is not None:
    print(f"Avg confidence (needs review):  {float(avg_review):.3f}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## What you learned
# MAGIC
# MAGIC A closed-loop learning system: seed messy case notes, extract with AI, route by confidence, correct, and analyze. All on one table. As analysts correct low-confidence extractions, the system improves: confidence grows, more auto-accepts, fewer reviews. Monitor drift (accuracy over time) to catch model decay.

# COMMAND ----------

# MAGIC %md
# MAGIC ---
# MAGIC **Next in the Agent developers track:** <a href="$../pg-vector/pg_vector_databricks">Vector Similarity Search →</a>
# MAGIC
# MAGIC <a href="$../../START_HERE">← Back to the table of contents</a>
