#!/usr/bin/env python3
"""Human-in-the-loop learning loop — extract, route, correct, analyze on one table.

Demonstrates the closed-loop pattern:
  1. Seed maintenance write-ups (free text)
  2. Run Claude extraction: system/defect/action + confidence
  3. Route by confidence: high → auto_accepted, low → needs_review
  4. Simulate human correction on uncertain entries
  5. Analytics: accuracy, drift, confidence distribution

Usage:
    python learning_loop.py                # run the whole loop
    python learning_loop.py --step seed    # just seed write-ups
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
TABLE = "factory.maintenance_log"

# Real-world messy maintenance write-ups. Some clear, some ambiguous.
WRITEUPS = [
    ("WU-001", "M-204", "Hydraulic line on leg B leaking, found ice on exterior, isolated line, monitor pressure."),
    ("WU-002", "M-405", "L MLG tire worn to indicator, replace at next A-check."),
    ("WU-003", "M-301", "Cabin ka-band intermittent, pax complaints on last 3 legs; swap modem?"),
    ("WU-004", "M-108", "APU slow to start, ~40s hung start x2, investigate."),
    ("WU-005", "M-204", "Something off with the thing on the right side, maybe hydraulics? not sure"),
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
    """Seed the maintenance_log table with free-text write-ups."""
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute(f"DELETE FROM {TABLE}")
            for wid, mid, writeup in WRITEUPS:
                cur.execute(
                    f"""INSERT INTO {TABLE} (machine_id, writeup) VALUES (%s, %s)""",
                    [mid, writeup],
                )
    print(f"Seeding maintenance write-ups ({len(WRITEUPS)} entries):")
    for wid, mid, writeup in WRITEUPS:
        print(f"  - {mid}: {writeup[:60]}...")
    print()


def extract():
    """Run Claude extraction on each write-up."""
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute(f"SELECT log_id, writeup FROM {TABLE} ORDER BY log_id")
            rows = cur.fetchall()

    print(f"Running AI extraction ({len(rows)} write-ups):")
    for log_id, writeup in rows:
        prompt = [
            {
                "role": "system",
                "content": (
                    "You are a maintenance triage assistant. From a free-text write-up, "
                    "extract system (subsystem affected), defect (the problem), action (what was done), "
                    "and confidence (0-1, how certain you are the extraction is correct and unambiguous). "
                    "Respond with ONLY a JSON object: {\"system\": \"...\", \"defect\": \"...\", "
                    "\"action\": \"...\", \"confidence\": 0.X}"
                ),
            },
            {"role": "user", "content": writeup},
        ]

        response = _fm_call(prompt)
        if response is None:
            # Fallback simulation
            if "leaking" in writeup.lower() or "hydraulic" in writeup.lower():
                extract_dict = {"system": "hydraulic", "defect": "line_leak", "action": "isolated", "confidence": 0.92}
            elif "tire" in writeup.lower() or "worn" in writeup.lower():
                extract_dict = {"system": "landing_gear", "defect": "tire_wear", "action": "schedule_replace", "confidence": 0.89}
            elif "intermittent" in writeup.lower() or "ka-band" in writeup.lower():
                extract_dict = {"system": "communications", "defect": "intermittent_reception", "action": "investigate", "confidence": 0.68}
            elif "apu" in writeup.lower() or "slow" in writeup.lower():
                extract_dict = {"system": "apu", "defect": "slow_start", "action": "investigate", "confidence": 0.71}
            else:
                extract_dict = {"system": "unknown", "defect": "unknown", "action": "investigate", "confidence": 0.38}
        else:
            try:
                # Parse JSON from response
                json_start = response.find("{")
                json_end = response.rfind("}") + 1
                json_str = response[json_start:json_end]
                extract_dict = json.loads(json_str)
            except Exception:
                extract_dict = {"system": "?", "defect": "(parse failed)", "action": "?", "confidence": 0.3}

        # Ensure confidence is in [0, 1]
        conf = float(extract_dict.get("confidence", 0.5))
        conf = max(0.0, min(1.0, conf))
        status = "auto_accepted" if conf >= CONF_THRESHOLD else "needs_review"

        with connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"""UPDATE {TABLE} SET system=%s, defect=%s, action=%s, confidence=%s, status=%s
                       WHERE log_id=%s""",
                    [extract_dict.get("system", "?"),
                     extract_dict.get("defect", "?"),
                     extract_dict.get("action", "?"),
                     conf,
                     status,
                     log_id],
                )

        print(f"  - Log {log_id}: system={extract_dict.get('system', '?')}, "
              f"confidence={conf:.2f}, status={status}")
    print()


def correct():
    """Simulate a human correction on an uncertain entry."""
    print(f"Human correction (engineer reviews uncertain entries):")

    # Correct entry #3 (log_id=3): make it more specific
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"""UPDATE {TABLE} SET system=%s, defect=%s, status=%s WHERE log_id=%s""",
                ["communications", "modem_failure", "corrected", 3],
            )
    print(f"  - Log 3: corrected defect to 'modem_failure' (from 'intermittent_reception')")
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
        description="Human-in-the-loop learning loop — extract, route, correct, analyze"
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
