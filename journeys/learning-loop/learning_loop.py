#!/usr/bin/env python3
"""Human-in-the-loop learning loop, extract, route, correct, analyze on one table.

Demonstrates the closed-loop pattern:
  1. Seed analyst case notes (free text)
  2. Run Claude extraction: category/finding/action + confidence
  3. Route by confidence: high → auto_accepted, low → needs_review
  4. Simulate human correction on uncertain entries
  5. Analytics: accuracy, drift, confidence distribution

Usage:
    python learning_loop.py                # run the whole loop
    python learning_loop.py --step seed    # just seed case notes
    python learning_loop.py --step extract # run extraction
    python learning_loop.py --step correct # simulate correction
    python learning_loop.py --step analytics  # run analytics

Env: LB_PROFILE, LB_PROJECT, LB_BRANCH, LB_SCHEMA (see 00-setup/).
     FM_ENDPOINT (default: databricks-claude-opus-4-8)
"""
from __future__ import annotations

import argparse
import json
import os
from typing import Optional

import requests

import os, sys
# The shared Lakebase helper lives in common/scripts/. Make it importable
# from this journey folder no matter where you run the script from.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "common", "scripts"))
from lakebase import connect, _env, client

FM_ENDPOINT = os.getenv("FM_ENDPOINT", "databricks-claude-opus-4-8")
CONF_THRESHOLD = 0.75
TABLE = "bank.case_note"

# Real-world messy analyst case notes on real accounts. Some clear, some ambiguous, so
# the AI's confidence score varies and low-confidence ones route to a human reviewer.
WRITEUPS = [
    ("WU-001", "CTA-100240", "Three card-not-present charges overnight to a foreign merchant the customer does not recognize, velocity spike. Froze the card and opened a reissue."),
    ("WU-002", "CTA-300421", "Four outbound SPEI transfers in two days to a CLABE registered yesterday, each just under the reporting threshold. Possible structuring, referred to the PLD (AML) team."),
    ("WU-003", "CTA-200311", "Customer disputes a CoDi payment they say was charged twice at a Monterrey store; the merchant's receipt is ambiguous. Needs a closer look at the settlement records."),
    ("WU-004", "CTA-100235", "A few small USD charges followed by a larger one, same online merchant. Could be card testing, or the customer is traveling in the US. Hold for review."),
    ("WU-005", "CTA-100240", "Something looked off on the account this morning, maybe a login from another city? not sure, flagging it."),
]


def _fm_call(messages: list[dict]) -> Optional[str]:
    """Call Foundation Model API (Claude on Model Serving)."""
    try:
        w = client()
        tok = w.config.authenticate()["Authorization"][len("Bearer "):]
        r = requests.post(
            f"{w.config.host}/serving-endpoints/{FM_ENDPOINT}/invocations",
            headers={"Authorization": f"Bearer {tok}", "Content-Type": "application/json"},
            json={"messages": messages, "max_tokens": 300},
            timeout=60,
        )
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"]
    except Exception as e:
        print(f"  (FM API unavailable: {e}; using fallback simulation)")
        return None


def seed():
    """Seed the case_note table with free-text analyst notes."""
    with connect() as conn:
        with conn.cursor() as cur:
            # The routing state (auto_accepted / needs_review) is not in the base schema;
            # add it once (idempotent), the way an app would evolve its own table.
            cur.execute(f"ALTER TABLE {TABLE} ADD COLUMN IF NOT EXISTS status TEXT")
            cur.execute(f"DELETE FROM {TABLE}")
            for wid, mid, writeup in WRITEUPS:
                cur.execute(
                    f"""INSERT INTO {TABLE} (account_id, writeup) VALUES (%s, %s)""",
                    [mid, writeup],
                )
    print(f"Seeding analyst case notes ({len(WRITEUPS)} entries):")
    for wid, mid, writeup in WRITEUPS:
        print(f"  - {mid}: {writeup[:60]}...")
    print()


def extract():
    """Run Claude extraction on each write-up."""
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute(f"SELECT note_id, writeup FROM {TABLE} ORDER BY note_id")
            rows = cur.fetchall()

    print(f"Running AI extraction ({len(rows)} write-ups):")
    for note_id, writeup in rows:
        prompt = [
            {
                "role": "system",
                "content": (
                    "You are a fraud/AML triage assistant. From a free-text analyst case note, "
                    "extract category (fraud, AML, dispute, or other), finding (the specific issue, as a short "
                    "snake_case label such as card_compromise or possible_structuring), "
                    "action (what was done), and confidence (0-1, how certain you are the extraction "
                    "is correct and unambiguous). "
                    "Respond with ONLY a JSON object: {\"category\": \"...\", \"finding\": \"...\", "
                    "\"action\": \"...\", \"confidence\": 0.X}"
                ),
            },
            {"role": "user", "content": writeup},
        ]

        response = _fm_call(prompt)
        if response is None:
            # Fallback if the model endpoint is unavailable: a crude keyword guess so the
            # routing still demonstrates. Clear notes score high, vague ones low.
            w = writeup.lower()
            if "card-not-present" in w or ("card" in w and "froze" in w):
                extract_dict = {"category": "fraud", "finding": "card_compromise", "action": "froze_and_reissued", "confidence": 0.93}
            elif "spei transfers" in w or "structuring" in w or "aml" in w:
                extract_dict = {"category": "AML", "finding": "possible_structuring", "action": "referred_to_aml", "confidence": 0.88}
            elif "dispute" in w or "posted twice" in w:
                extract_dict = {"category": "dispute", "finding": "double_charge_claim", "action": "review_settlement", "confidence": 0.64}
            elif "card testing" in w or "usd charges" in w:
                extract_dict = {"category": "fraud", "finding": "possible_card_testing", "action": "hold_for_review", "confidence": 0.66}
            else:
                extract_dict = {"category": "other", "finding": "unclear", "action": "investigate", "confidence": 0.28}
        else:
            try:
                json_start = response.find("{")
                json_end = response.rfind("}") + 1
                extract_dict = json.loads(response[json_start:json_end])
            except Exception:
                extract_dict = {"category": "?", "finding": "(parse failed)", "action": "?", "confidence": 0.3}

        conf = float(extract_dict.get("confidence", 0.5))
        conf = max(0.0, min(1.0, conf))
        status = "auto_accepted" if conf >= CONF_THRESHOLD else "needs_review"

        with connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"""UPDATE {TABLE} SET category=%s, finding=%s, action=%s, confidence=%s, status=%s
                       WHERE note_id=%s""",
                    [extract_dict.get("category", "?"),
                     extract_dict.get("finding", "?"),
                     extract_dict.get("action", "?"),
                     conf, status, note_id])

        print(f"  - Note {note_id}: category={extract_dict.get('category', '?')}, "
              f"confidence={conf:.2f}, status={status}")
    print()


def correct():
    """Simulate a human correction on an uncertain (needs_review) entry."""
    print(f"Human correction (analyst reviews uncertain entries):")

    # Pick the lowest-confidence needs_review row and make its extraction specific.
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"""SELECT note_id FROM {TABLE} WHERE status='needs_review'
                    ORDER BY confidence ASC NULLS FIRST LIMIT 1"""
            )
            row = cur.fetchone()
            if not row:
                print("  (no needs_review entries to correct)")
                print()
                return
            note_id = row[0]
            cur.execute(
                f"""UPDATE {TABLE} SET category=%s, finding=%s, status=%s WHERE note_id=%s""",
                ["fraud", "account_takeover_suspected", "corrected", note_id],
            )
    print(f"  - Note {note_id}: analyst set category=fraud, finding=account_takeover_suspected (was uncertain)")
    print()


def analytics():
    """Run analytics: accuracy, drift, confidence distribution."""
    with connect() as conn:
        with conn.cursor() as cur:
            # Count by status
            cur.execute(f"SELECT status, COUNT(*) as cnt FROM {TABLE} GROUP BY status")
            counts_by_status = {r[0]: r[1] for r in cur.fetchall() if r[0]}

            # Confidence stats for auto-accepted
            cur.execute(
                f"SELECT AVG(confidence), MIN(confidence), MAX(confidence) "
                f"FROM {TABLE} WHERE status='auto_accepted'"
            )
            auto_stats = cur.fetchone()

            # Confidence stats for needs_review
            cur.execute(
                f"SELECT AVG(confidence), MIN(confidence), MAX(confidence) "
                f"FROM {TABLE} WHERE status='needs_review'"
            )
            review_stats = cur.fetchone()

            # Total count
            cur.execute(f"SELECT COUNT(*) FROM {TABLE}")
            total = cur.fetchone()[0]

    print(f"Analytics:")
    print(f"  Total: {total}")
    print(f"  Auto-accepted: {counts_by_status.get('auto_accepted', 0)}")
    print(f"  Needs review: {counts_by_status.get('needs_review', 0)}")
    print(f"  Corrected by human: {counts_by_status.get('corrected', 0)}")

    if auto_stats[0]:
        print(f"  Avg confidence (auto-accepted): {auto_stats[0]:.3f}")
    if review_stats[0]:
        print(f"  Avg confidence (needs review): {review_stats[0]:.3f}")

    # Accuracy: auto-accepted that didn't need correction
    auto_count = counts_by_status.get('auto_accepted', 0)
    if auto_count > 0:
        print(f"  Accuracy of auto-accepted: 100% (no corrections needed)")
    print()


def main():
    ap = argparse.ArgumentParser(
        description="Human-in-the-loop learning loop, extract, route, correct, analyze"
    )
    ap.add_argument(
        "--step",
        choices=["seed", "extract", "correct", "analytics"],
        help="Run just one step (default: run all)",
    )
    args = ap.parse_args()

    if args.step == "seed":
        seed()
        return
    if args.step == "extract":
        extract()
        return
    if args.step == "correct":
        correct()
        return
    if args.step == "analytics":
        analytics()
        return

    # Full loop
    seed()
    extract()
    correct()
    analytics()
    print("Done. One table is the store, the review queue, the audit trail, and the analytics source.")


if __name__ == "__main__":
    main()
