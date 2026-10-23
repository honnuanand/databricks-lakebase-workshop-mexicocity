# Databricks notebook source
# MAGIC %md-sandbox
# MAGIC <div style="display:flex; align-items:center; gap:10px; padding:8px 16px; background:#F9F7F4; border-bottom:2px solid #E0E0E0; font-family:sans-serif; line-height:1;">
# MAGIC   <span style="display:inline-block; width:12px; height:12px; border-radius:2px; background:#FF3621;"></span>
# MAGIC   <span style="font-weight:bold; color:#0b2026;">Lakebase workshop</span>
# MAGIC   <span style="color:#999;">|</span>
# MAGIC   <span style="color:#5A6F77;">Part 2 · Agent developers · Journey 3 of 5 · Human Review of AI Output</span>
# MAGIC </div>

# COMMAND ----------

# MAGIC %md
# MAGIC # Human Review of AI Output
# MAGIC #### Duration: about 25 minutes
# MAGIC
# MAGIC *Journey 3 of 5. In Tool-Calling Agents the agent was sure of itself. Here the model says how sure it is, and the unsure answers go to a person.*
# MAGIC
# MAGIC ## Overview
# MAGIC
# MAGIC Fraud and AML (PLD) analysts write case notes in a hurry: free text, abbreviations, half-finished
# MAGIC thoughts. The investigations team wants structured facts from each note (category, finding, action)
# MAGIC so they can count and route cases. A model can extract them, but nobody will trust it on the vague
# MAGIC notes, and nobody wants to re-check the obvious ones.
# MAGIC
# MAGIC In this lab a model reads five case notes and returns an extraction with a confidence score. Clear
# MAGIC notes are accepted automatically; uncertain ones are routed to an analyst, who corrects one. The
# MAGIC notes, the AI's output, the routing, and the correction all live in one table on your branch, and
# MAGIC the same table answers the accuracy questions afterwards.
# MAGIC
# MAGIC ## Learning objectives
# MAGIC
# MAGIC By the end of this lab, you will be able to:
# MAGIC
# MAGIC 1. **Store AI output next to its source** by writing a model's extraction back to the row it came from.
# MAGIC 2. **Route by confidence:** accept clear extractions automatically and send uncertain ones to review.
# MAGIC 3. **Record a human correction** in the same row, with a status that shows a person changed it.
# MAGIC 4. **Measure the loop with SQL** on the operational table, with no separate analytics copy.

# COMMAND ----------

# MAGIC %md
# MAGIC ## Key concepts
# MAGIC
# MAGIC - **Extraction:** turning free text into fields. Here, `category`, `finding`, `action`, and `confidence` from each `writeup`.
# MAGIC - **Confidence threshold:** the score above which an extraction is trusted without review. This lab uses **0.75**.
# MAGIC - **Human in the loop:** a person reviews what the model isn't sure about, and their correction is kept.
# MAGIC - **Status:** `auto_accepted`, `needs_review`, or `corrected`. One column turns the table into a review queue and an audit trail.
# MAGIC
# MAGIC More terms are defined in `docs/glossary.md` in the workshop folder.

# COMMAND ----------

# MAGIC %md-sandbox
# MAGIC ## A. Setup
# MAGIC
# MAGIC <div style="border-left:4px solid #1B5162; background:#EEF4F6; padding:12px 16px; border-radius:4px; margin:12px 0; font-family:sans-serif;">
# MAGIC   <strong style="display:block; color:#1B5162; margin-bottom:6px;">Before you start</strong>
# MAGIC   <div style="color:#333;">
# MAGIC     Run <code>00-setup/setup_databricks</code> once to create your branch and load the bank.
# MAGIC     Attach this notebook to <strong>serverless</strong> compute. The extraction step calls the Foundation
# MAGIC     Model endpoint <code>databricks-claude-opus-4-8</code> (left sidebar, <strong>Serving</strong>); if it
# MAGIC     isn't available, the notebook uses fixed extractions instead. This lab <strong>replaces every case
# MAGIC     note on your branch</strong> (see B).
# MAGIC   </div>
# MAGIC </div>
# MAGIC
# MAGIC <div style="max-width:720px; margin:12px auto; font-family:sans-serif;">
# MAGIC <svg viewBox="0 0 720 170" xmlns="http://www.w3.org/2000/svg" style="width:100%; height:auto; display:block;" font-family="sans-serif">
# MAGIC   <rect x="10" y="10" width="700" height="150" rx="10" fill="#F9F7F4" stroke="#E0E0E0"/>
# MAGIC   <rect x="30" y="50" width="120" height="56" rx="8" fill="#FFFFFF" stroke="#1B5162" stroke-width="2"/>
# MAGIC   <text x="90" y="74" text-anchor="middle" font-size="13" font-weight="700" fill="#0b2026">case note</text>
# MAGIC   <text x="90" y="93" text-anchor="middle" font-size="11" fill="#5A6F77">free text</text>
# MAGIC   <rect x="180" y="50" width="120" height="56" rx="8" fill="#FFFFFF" stroke="#5A6F77" stroke-width="2" stroke-dasharray="6 4"/>
# MAGIC   <text x="240" y="74" text-anchor="middle" font-size="13" font-weight="700" fill="#0b2026">model</text>
# MAGIC   <text x="240" y="93" text-anchor="middle" font-size="11" fill="#5A6F77">fields + confidence</text>
# MAGIC   <rect x="340" y="25" width="150" height="46" rx="8" fill="#FFFFFF" stroke="#1B5162" stroke-width="2"/>
# MAGIC   <text x="415" y="53" text-anchor="middle" font-size="13" font-weight="700" fill="#0b2026">auto_accepted</text>
# MAGIC   <rect x="340" y="88" width="150" height="46" rx="8" fill="#FFF3E0" stroke="#FF9800" stroke-width="2"/>
# MAGIC   <text x="415" y="116" text-anchor="middle" font-size="13" font-weight="700" fill="#0b2026">needs_review</text>
# MAGIC   <rect x="530" y="88" width="160" height="46" rx="8" fill="#FFFFFF" stroke="#1B5162" stroke-width="2"/>
# MAGIC   <text x="610" y="110" text-anchor="middle" font-size="13" font-weight="700" fill="#0b2026">corrected</text>
# MAGIC   <text x="610" y="126" text-anchor="middle" font-size="11" fill="#5A6F77">by an analyst</text>
# MAGIC   <line x1="150" y1="78" x2="172" y2="78" stroke="#1B5162" stroke-width="2"/><polygon points="172,72 180,78 172,84" fill="#1B5162"/>
# MAGIC   <line x1="300" y1="70" x2="332" y2="52" stroke="#1B5162" stroke-width="2"/><polygon points="329,46 340,48 334,57" fill="#1B5162"/>
# MAGIC   <line x1="300" y1="86" x2="332" y2="106" stroke="#FF9800" stroke-width="2"/><polygon points="334,100 340,110 329,111" fill="#FF9800"/>
# MAGIC   <line x1="490" y1="111" x2="522" y2="111" stroke="#1B5162" stroke-width="2"/><polygon points="522,105 530,111 522,117" fill="#1B5162"/>
# MAGIC   <text x="316" y="40" text-anchor="middle" font-size="11" fill="#5A6F77">≥ 0.75</text>
# MAGIC   <text x="316" y="140" text-anchor="middle" font-size="11" fill="#5A6F77">&lt; 0.75</text>
# MAGIC   <text x="600" y="50" text-anchor="middle" font-size="11" fill="#5A6F77">all in one row of bank.case_note</text>
# MAGIC </svg>
# MAGIC </div>

# COMMAND ----------

# MAGIC %md
# MAGIC ### A1. Install the driver and pick your branch
# MAGIC
# MAGIC Run the next three cells before anything else. They install the Postgres driver, upgrade the
# MAGIC Databricks SDK if your environment's version predates the Lakebase API, and set `LB_PROJECT`,
# MAGIC `LB_BRANCH`, and `LB_SCHEMA` from the widgets at the top of this notebook. `LB_BRANCH` defaults to
# MAGIC the branch `00-setup/setup_databricks` created for you. Change a widget only if you used a
# MAGIC different project or branch name.

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

# MAGIC %md-sandbox
# MAGIC **Expected result:** `signed in as` your email, followed by your project, branch, and schema:
# MAGIC
# MAGIC ```
# MAGIC signed in as alex.kim@example.com
# MAGIC   LB_PROJECT = bank
# MAGIC   LB_BRANCH = u-alex-kim
# MAGIC   LB_SCHEMA = bank
# MAGIC ```
# MAGIC
# MAGIC <div style="border-left:4px solid #FF9800; background:#FFF3E0; padding:12px 16px; border-radius:4px; margin:12px 0; font-family:sans-serif;">
# MAGIC   <strong style="display:block; color:#E65100; margin-bottom:6px;">Troubleshooting</strong>
# MAGIC   <div style="color:#333;">
# MAGIC     <ul style="margin:0; padding-left:20px;">
# MAGIC       <li><code>databricks-sdk ... predates the Lakebase API</code>: rerun the install cell and the restart cell, then this one.</li>
# MAGIC       <li><code>Fill in LB_BRANCH in the widgets at the top of the notebook</code>: type your branch name in the <code>LB_BRANCH</code> box, then rerun this cell.</li>
# MAGIC       <li>The widgets show an old branch name: run <code>dbutils.widgets.removeAll()</code> in a new cell, then rerun this one.</li>
# MAGIC     </ul>
# MAGIC   </div>
# MAGIC </div>

# COMMAND ----------

# MAGIC %md
# MAGIC ### A2. Connect and define the model call
# MAGIC
# MAGIC This cell loads the shared helper from `common/scripts/` and sets the confidence threshold, 0.75.
# MAGIC
# MAGIC - `connect()` opens a Postgres connection to your branch. Under the hood it asks the Lakebase API
# MAGIC   for the branch's host name, gets a login token from your Databricks identity (valid for about an
# MAGIC   hour), and connects with `psycopg`, a Postgres driver for Python.
# MAGIC - `fm_call()` sends chat messages to the Foundation Model endpoint over HTTPS, signed in as you, and
# MAGIC   returns the model's text, or `None` if the call fails (then the fixed extractions are used).

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

# MAGIC %md-sandbox
# MAGIC **Expected result:**
# MAGIC
# MAGIC ```
# MAGIC Learning loop: seed -> extract -> route -> correct -> analyze
# MAGIC FM endpoint: databricks-claude-opus-4-8
# MAGIC ```
# MAGIC
# MAGIC <div style="border-left:4px solid #FF9800; background:#FFF3E0; padding:12px 16px; border-radius:4px; margin:12px 0; font-family:sans-serif;">
# MAGIC   <strong style="display:block; color:#E65100; margin-bottom:6px;">Troubleshooting</strong>
# MAGIC   <div style="color:#333;">
# MAGIC     <ul style="margin:0; padding-left:20px;">
# MAGIC       <li><code>Missing required env var LB_PROJECT</code> in a later cell: the A1 cells didn't run in this session. Run the three A1 cells, then this one.</li>
# MAGIC       <li>Your workshop uses a different model endpoint: change the default in the <code>FM_ENDPOINT = ...</code> line of this cell, then rerun it.</li>
# MAGIC     </ul>
# MAGIC   </div>
# MAGIC </div>

# COMMAND ----------

# MAGIC %md-sandbox
# MAGIC ## B. Load the case notes
# MAGIC
# MAGIC The cell adds a `status` column to `case_note` if it isn't there yet (the base schema has no routing
# MAGIC column; an app would add one the same way), then replaces the table's rows with five analyst notes:
# MAGIC two clear, three less so. The first one, as SQL:
# MAGIC
# MAGIC ```sql
# MAGIC ALTER TABLE bank.case_note ADD COLUMN IF NOT EXISTS status TEXT;
# MAGIC DELETE FROM bank.case_note;
# MAGIC INSERT INTO bank.case_note (account_id, writeup)
# MAGIC VALUES ('CTA-100240', 'Three card-not-present charges overnight to a foreign merchant the customer does not recognize, velocity spike. Froze the card and opened a reissue.');
# MAGIC ```
# MAGIC
# MAGIC <div style="border-left:4px solid #FF3621; background:#FFF1EE; padding:12px 16px; border-radius:4px; margin:12px 0; font-family:sans-serif;">
# MAGIC   <strong style="display:block; color:#C4200F; margin-bottom:6px;">This deletes every case note on your branch</strong>
# MAGIC   <div style="color:#333;">
# MAGIC     The four case notes from setup, and any hold note from Tool-Calling Agents, are removed. Only your
# MAGIC     branch is affected. The capstone app (App developers track) reads those notes: if you'll run it
# MAGIC     later, rebuild your branch afterwards with <code>branch.reset()</code>,
# MAGIC     as in section E2 of Point-in-Time Restore.
# MAGIC   </div>
# MAGIC </div>

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
# MAGIC **Expected result:** `Seeded 5 analyst case notes`

# COMMAND ----------

# MAGIC %md
# MAGIC ### B1. Read the notes back
# MAGIC
# MAGIC The SQL:
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

# MAGIC %md-sandbox
# MAGIC **Expected result:** five notes. The ids continue after the four notes from setup (and the hold
# MAGIC note, if you ran Tool-Calling Agents first), and keep counting on every rerun.
# MAGIC
# MAGIC ```
# MAGIC Analyst case notes (5 total):
# MAGIC   5 CTA-100240: Three card-not-present charges overnight to a foreign merchant the cus...
# MAGIC   6 CTA-300421: Four outbound SPEI transfers in two days to a CLABE registered yesterd...
# MAGIC   7 CTA-200311: Customer disputes a CoDi payment they say was charged twice at a Monte...
# MAGIC   8 CTA-100235: A few small USD charges followed by a larger one, same online merchant...
# MAGIC   9 CTA-100240: Something looked off on the account this morning, maybe a login from a...
# MAGIC ```
# MAGIC
# MAGIC **What this proves:** the raw input is ordinary rows. The model's output will go into the empty columns of these same rows.

# COMMAND ----------

# MAGIC %md
# MAGIC ## C. Extract and route by confidence
# MAGIC
# MAGIC For each note, the model gets one instruction: return the category (fraud, AML, dispute, or other),
# MAGIC the finding as a short label, the action taken, and how confident it is, as JSON. The cell writes
# MAGIC the extraction and a status back to the note's row: `auto_accepted` at 0.75 or more, `needs_review`
# MAGIC below. The SQL for each note:
# MAGIC
# MAGIC ```sql
# MAGIC UPDATE bank.case_note
# MAGIC SET category = 'fraud', finding = 'card_compromise', action = 'froze_and_reissued',
# MAGIC     confidence = 0.90, status = 'auto_accepted'
# MAGIC WHERE note_id = 5;
# MAGIC ```
# MAGIC
# MAGIC The model sets its own confidence, so your labels and scores can differ a little from run to run.

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

# MAGIC %md-sandbox
# MAGIC **Expected result:** from a test run (labels and scores vary):
# MAGIC
# MAGIC ```
# MAGIC Extraction results:
# MAGIC   Auto-accepted (conf >= 0.75): 3
# MAGIC   Needs review   (conf <  0.75): 2
# MAGIC
# MAGIC Auto-accepted entries:
# MAGIC   fraud/card_compromise: conf=0.90
# MAGIC   AML/possible_structuring: conf=0.90
# MAGIC   dispute/possible_duplicate_charge: conf=0.78
# MAGIC
# MAGIC Needs review:
# MAGIC   fraud/possible_card_testing: conf=0.55
# MAGIC   other/possible_unusual_login: conf=0.30
# MAGIC ```
# MAGIC
# MAGIC In every test run, the card-fraud and structuring notes scored 0.90 or more, the CoDi dispute about
# MAGIC 0.78, and the USD-charges and vague login notes 0.55 or less.
# MAGIC
# MAGIC **What this proves:** the model's confidence does the triage. The clear notes need no one; the vague ones are queued for a person.
# MAGIC
# MAGIC <div style="border-left:4px solid #FF9800; background:#FFF3E0; padding:12px 16px; border-radius:4px; margin:12px 0; font-family:sans-serif;">
# MAGIC   <strong style="display:block; color:#E65100; margin-bottom:6px;">Troubleshooting</strong>
# MAGIC   <div style="color:#333;">
# MAGIC     <ul style="margin:0; padding-left:20px;">
# MAGIC       <li><code>(FM API unavailable: 404 Client Error: Not Found for url: ...; using fallback)</code>, once per note: the endpoint name is wrong or it doesn't exist in this workspace. The fixed extractions are used (2 auto-accepted, 3 needs review). To use a model, fix <code>FM_ENDPOINT</code> in A2.</li>
# MAGIC       <li>An entry like <code>?/(parse failed): conf=0.30</code>: the model didn't return valid JSON for that note. It's routed to review, which is the safe default. Rerun the cell to try again.</li>
# MAGIC     </ul>
# MAGIC   </div>
# MAGIC </div>

# COMMAND ----------

# MAGIC %md
# MAGIC ## D. An analyst corrects an uncertain note
# MAGIC
# MAGIC The analyst takes the `needs_review` note with the lowest confidence, reads it, and sets the
# MAGIC category and finding by hand. The correction overwrites the AI's fields in the same row and sets
# MAGIC `status = 'corrected'`. The SQL:
# MAGIC
# MAGIC ```sql
# MAGIC UPDATE bank.case_note
# MAGIC SET category = 'fraud', finding = 'account_takeover_suspected', status = 'corrected'
# MAGIC WHERE note_id = (SELECT note_id FROM bank.case_note WHERE status = 'needs_review'
# MAGIC                  ORDER BY confidence ASC NULLS FIRST LIMIT 1);
# MAGIC ```

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

# MAGIC %md-sandbox
# MAGIC **Expected result:** `Analyst corrected note_id=9: category=fraud, finding=account_takeover_suspected, status=corrected`
# MAGIC (the vague login note; your id may differ).
# MAGIC
# MAGIC **What this proves:** the person's decision is stored where the AI's was, with a status that says a person made it. The model's confidence stays in the row, so you can see what it was unsure about.
# MAGIC
# MAGIC <div style="border-left:4px solid #1B5162; background:#EEF4F6; padding:12px 16px; border-radius:4px; margin:12px 0; font-family:sans-serif;">
# MAGIC   <strong style="display:block; color:#1B5162; margin-bottom:6px;">See it in the UI (optional)</strong>
# MAGIC   <div style="color:#333;">
# MAGIC     Open the <strong>Lakebase Postgres</strong> app, select your project and your branch, then the
# MAGIC     <strong>Tables</strong> tab, and open <code>case_note</code>. Each row shows the note, the extraction,
# MAGIC     the confidence, and its status.
# MAGIC   </div>
# MAGIC </div>

# COMMAND ----------

# MAGIC %md
# MAGIC ## E. Measure the loop
# MAGIC
# MAGIC The same table answers the questions a team lead asks: how many notes were accepted, reviewed, or
# MAGIC corrected, and how confident the model was in each group. The SQL:
# MAGIC
# MAGIC ```sql
# MAGIC SELECT status, COUNT(*) FROM bank.case_note WHERE status IS NOT NULL GROUP BY status;
# MAGIC SELECT AVG(confidence) FROM bank.case_note WHERE status = 'auto_accepted';
# MAGIC SELECT AVG(confidence) FROM bank.case_note WHERE status = 'needs_review';
# MAGIC ```

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

# MAGIC %md-sandbox
# MAGIC **Expected result:** from the same test run:
# MAGIC
# MAGIC ```
# MAGIC === Learning Loop Analytics ===
# MAGIC
# MAGIC Processed: 5
# MAGIC   Auto-accepted: 3
# MAGIC   Needs review:  1
# MAGIC   Corrected:     1
# MAGIC
# MAGIC Avg confidence (auto-accepted): 0.877
# MAGIC Avg confidence (needs review):  0.550
# MAGIC ```
# MAGIC
# MAGIC **What this proves:** the operational table is also the analytics source. No export, no second store.

# COMMAND ----------

# MAGIC %md-sandbox
# MAGIC ##### EXPAND FOR ADDITIONAL NOTES
# MAGIC
# MAGIC <details>
# MAGIC <summary><strong>Choosing the threshold, and watching for drift</strong></summary>
# MAGIC
# MAGIC The threshold trades analyst time for risk. Raise it and more notes go to review; lower it and more
# MAGIC are trusted as they are. Pick it from data: track how often analysts change an extraction at each
# MAGIC confidence level, and set the threshold where corrections become rare.
# MAGIC
# MAGIC The same queries, grouped by week, show drift: if the share of `needs_review` or `corrected` notes
# MAGIC climbs, the notes have changed or the model has, and it's time to look. Because the corrections are
# MAGIC stored next to the original notes, they are also a ready-made evaluation set for the next model.
# MAGIC
# MAGIC </details>

# COMMAND ----------

# MAGIC %md-sandbox
# MAGIC ##### Check your understanding
# MAGIC
# MAGIC <details>
# MAGIC <summary><strong>1. Why did the vague login note go to review, while the structuring note didn't?</strong></summary>
# MAGIC
# MAGIC The model gave it a low confidence (under 0.75), so the routing rule sent it to a person. The structuring note was clear and scored about 0.90.
# MAGIC
# MAGIC </details>
# MAGIC
# MAGIC <details>
# MAGIC <summary><strong>2. Where is the analyst's correction stored?</strong></summary>
# MAGIC
# MAGIC In the same `case_note` row as the note and the AI's extraction, with `status = 'corrected'`.
# MAGIC
# MAGIC </details>
# MAGIC
# MAGIC <details>
# MAGIC <summary><strong>3. Why can your counts differ from the expected result?</strong></summary>
# MAGIC
# MAGIC The model sets its own confidence on each run. A note near 0.75, like the CoDi dispute, can land on either side.
# MAGIC
# MAGIC </details>

# COMMAND ----------

# MAGIC %md
# MAGIC ## F. Conclusion
# MAGIC
# MAGIC In this lab a model extracted structured findings from five case notes, the confident ones were
# MAGIC accepted, the uncertain ones were queued, and an analyst corrected one, all in one table. Key
# MAGIC takeaways:
# MAGIC
# MAGIC 1. **Keep AI output next to its source:** the note, the extraction, and the confidence in one row.
# MAGIC 2. **Route by confidence** so people only review what the model isn't sure about.
# MAGIC 3. **Store corrections where the AI wrote,** with a status, so you can always tell machine from human.
# MAGIC 4. **Measure with SQL on the same table:** accuracy and drift without moving data.
# MAGIC
# MAGIC The next journey finds similar items by meaning: vector similarity search with `pgvector`, next to
# MAGIC the same bank data.

# COMMAND ----------

# MAGIC %md
# MAGIC ---
# MAGIC **Next in the Agent developers track:** <a href="$../lakebase-search/lakebase_search_databricks">Lakebase Search →</a>
# MAGIC
# MAGIC <a href="$../../START_HERE">← Back to the table of contents</a>
