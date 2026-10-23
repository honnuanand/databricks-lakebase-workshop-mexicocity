#!/usr/bin/env python3
"""Agent memory, two agents share one governed Lakebase table.

Demonstrates multi-agent shared state on one database:
  - seed the agent_memory table with a prior fraud note
  - ask the fraud advisor a question; it reads the note, responds, appends the turn
  - ask the ops assistant the same question; it reads BOTH the note AND the advisor's
    response, responds, appends its turn
  - no message queue, no cache, no orchestration, just one table

Usage:
    python agent_memory.py                 # run the whole story
    python agent_memory.py --step seed     # just seed the memory
    python agent_memory.py --step fraud    # ask the fraud advisor
    python agent_memory.py --step ops      # ask the ops assistant

Env: LB_PROFILE, LB_PROJECT, LB_BRANCH, LB_SCHEMA (see 00-setup/).
     FM_ENDPOINT (default: databricks-claude-opus-4-8)
"""
from __future__ import annotations

import argparse
import os
from typing import Optional

import requests

import os, sys
# The shared Lakebase helper lives in common/scripts/. Make it importable
# from this journey folder no matter where you run the script from.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "common", "scripts"))
from lakebase import connect, _env, client

NAMESPACE = "default"
SESSION_ID = "sess-01"
FM_ENDPOINT = os.getenv("FM_ENDPOINT", "databricks-claude-opus-4-8")
TABLE = "bank.agent_memory"

QUESTION = "Is CTA-100240 cleared, or do we freeze it for suspected fraud?"
SEED_NOTE = (
    "CTA-100240: late-night SPEI transfer of MXN 38,500 to a new beneficiary, anomaly score 8.7. "
    "Keep on watch, do not release the hold until the customer is reached."
)


def _fm_call(messages: list[dict], max_tokens: int = 400) -> Optional[str]:
    """Call Foundation Model API (Claude on Model Serving via SP auth).
    Returns the text response, or None if unavailable (fallback to simulation)."""
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
        print(f"  (FM API unavailable: {e}; using fallback simulation)")
        return None


def _call_agent(agent_id: str, question: str) -> str:
    """Call an agent (or simulate it) with access to shared memory context."""
    with connect() as conn:
        with conn.cursor() as cur:
            # Read all prior memory for this session
            cur.execute(
                f"""SELECT agent_id, role, content FROM {TABLE}
                   WHERE namespace=%s AND session_id=%s
                   ORDER BY created_at""",
                [NAMESPACE, SESSION_ID],
            )
            prior_rows = cur.fetchall()

    print(f"Prior memory ({len(prior_rows)} row{'s' if len(prior_rows) != 1 else ''}):")
    if prior_rows:
        for r in prior_rows:
            print(f"  - {r[0]} ({r[1]}): {r[2][:100]}")
    else:
        print("  (empty)")

    # Build the system prompt based on agent
    if agent_id == "fraud_advisor":
        sys_prompt = (
            "You are a fraud advisor at a retail bank. You read overnight alerts and prior "
            "notes about account risk, including transaction anomaly scores (0-10, higher is "
            "riskier). Decide whether an account should be cleared or kept on a hold / frozen "
            "for suspected fraud, grounded in the notes you are given. Keep answers to 1-2 "
            "sentences."
        )
    else:  # ops_assistant
        sys_prompt = (
            "You are an operations assistant at a retail bank branch. You service accounts: "
            "release or keep holds, answer servicing questions. You defer to the fraud "
            "advisor's determination when it is present in the shared notes. Answer whether "
            "an account hold stays or can be released, grounded in the notes. Keep answers to "
            "1-2 sentences."
        )

    messages = [{"role": "system", "content": sys_prompt}]
    if prior_rows:
        prior_context = "\n".join([f"{r[0]} ({r[1]}): {r[2]}" for r in prior_rows])
        messages.append(
            {"role": "system", "content": f"Prior context from shared memory:\n{prior_context}"}
        )
    messages.append({"role": "user", "content": question})

    # Try FM API; fall back to simulation
    response = _fm_call(messages)
    if response is None:
        if agent_id == "fraud_advisor":
            response = (
                "CTA-100240 is not cleared. An anomaly score of 8.7 on a late-night SPEI "
                "transfer to a new beneficiary is a strong fraud signal. Keep the hold in place "
                "and verify the transfer with the customer before releasing any funds."
            )
        else:  # ops_assistant
            response = (
                "I will keep the hold on CTA-100240 in place and not release funds, in line "
                "with the fraud advisor's determination. I will contact the customer to "
                "confirm the late-night transfer before any further action."
            )

    print(f"Response:\n  {response}\n")

    # Append both the user question and the assistant response to memory
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"""INSERT INTO {TABLE} (namespace, session_id, agent_id, role, content)
                   VALUES (%s, %s, %s, %s, %s)""",
                [NAMESPACE, SESSION_ID, agent_id, "user", question],
            )
            cur.execute(
                f"""INSERT INTO {TABLE} (namespace, session_id, agent_id, role, content)
                   VALUES (%s, %s, %s, %s, %s)""",
                [NAMESPACE, SESSION_ID, agent_id, "assistant", response],
            )
        with conn.cursor() as cur:
            cur.execute(
                f"SELECT count(*) FROM {TABLE} WHERE namespace=%s AND session_id=%s",
                [NAMESPACE, SESSION_ID],
            )
            count = cur.fetchone()[0]
    print(f"Memory now: {count} total rows\n")
    return response


def seed():
    """Seed the memory table with a prior fraud note for context."""
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"""INSERT INTO {TABLE} (namespace, session_id, agent_id, role, content)
                   VALUES (%s, %s, %s, %s, %s)""",
                [NAMESPACE, SESSION_ID, "fraud_advisor", "assistant", SEED_NOTE],
            )
            cur.execute(
                f"SELECT * FROM {TABLE} WHERE namespace=%s AND session_id=%s",
                [NAMESPACE, SESSION_ID],
            )
            rows = cur.fetchall()
    print("Seeding shared memory with a fraud note...")
    print(f"  Seed row: {rows[0] if rows else '(none)'}\n")


def fraud():
    """Ask the fraud advisor a question."""
    print("1. Fraud Advisor turn:")
    _call_agent("fraud_advisor", QUESTION)


def ops():
    """Ask the ops assistant a question."""
    print("2. Ops Assistant turn:")
    _call_agent("ops_assistant", QUESTION)


def main():
    ap = argparse.ArgumentParser(
        description="Agent memory, two agents share one governed Lakebase table"
    )
    ap.add_argument(
        "--step",
        choices=["seed", "fraud", "ops"],
        help="Run just one step (default: run all)",
    )
    args = ap.parse_args()

    if args.step == "seed":
        seed()
        return
    if args.step == "fraud":
        fraud()
        return
    if args.step == "ops":
        ops()
        return

    # Full story
    seed()
    fraud()
    ops()
    print("Done. Both agents wrote to and read from the same governed table.")


if __name__ == "__main__":
    main()
