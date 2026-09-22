#!/usr/bin/env python3
"""Agent memory — two agents share one governed Lakebase table.

Demonstrates multi-agent shared state on one database:
  - seed the agent_memory table with a prior maintenance note
  - ask the maintenance advisor a question; it reads the note, responds, appends the turn
  - ask the MES assistant the same question; it reads BOTH the note AND the advisor's
    response, responds, appends its turn
  - no message queue, no cache, no orchestration — just one table

Usage:
    python agent_memory.py                    # run the whole story
    python agent_memory.py --step seed        # just seed the memory
    python agent_memory.py --step maintenance # ask the maintenance advisor
    python agent_memory.py --step mes         # ask the MES assistant

Env: LB_PROFILE, LB_PROJECT, LB_BRANCH, LB_SCHEMA (see 00-setup/).
     FM_ENDPOINT (default: databricks-claude-opus-4-8)
"""
from __future__ import annotations

import argparse
import json
import os
import time
from typing import Optional

import psycopg
import requests
from databricks.sdk import WorkspaceClient

from lakebase import connect, _env, client

NAMESPACE = "default"
SESSION_ID = "shift-001"
FM_ENDPOINT = os.getenv("FM_ENDPOINT", "databricks-claude-opus-4-8")
TABLE = "factory.agent_memory"


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

    prior_text = "\n  - ".join(
        [f"{r[0]} ({r[1]}): {r[2][:100]}" if r[1] != "assistant" else r[2][:100]]
        for r in prior_rows
    )
    if prior_text:
        prior_text = "  - " + prior_text

    print(f"Prior memory ({len(prior_rows)} row{'s' if len(prior_rows) != 1 else ''}):")
    if prior_rows:
        for r in prior_rows:
            print(f"  - {r[0]} ({r[1]}): {r[2][:100]}")
    else:
        print("  (empty)")

    # Build the system prompt based on agent
    if agent_id == "maintenance_advisor":
        sys_prompt = (
            "You are a maintenance advisor for a smart factory. You read free-text notes and "
            "recommendations from prior shifts about machine health. Answer questions about "
            "whether machines are cleared to run, based on the maintenance history. Keep "
            "answers to 1-2 sentences."
        )
    else:  # mes_assistant
        sys_prompt = (
            "You are an MES (Manufacturing Execution System) assistant. You read maintenance "
            "notes and machine status to allocate machines to work orders. Answer questions "
            "about whether machines are ready, based on maintenance history and scheduling. "
            "Keep answers to 1-2 sentences."
        )

    messages = [
        {"role": "system", "content": sys_prompt},
    ]
    if prior_rows:
        prior_context = "\n".join(
            [f"{r[0]} ({r[1]}): {r[2]}" for r in prior_rows]
        )
        messages.append(
            {"role": "system", "content": f"Prior context from shared memory:\n{prior_context}"}
        )
    messages.append({"role": "user", "content": question})

    # Try FM API; fall back to simulation
    response = _fm_call(messages)
    if response is None:
        # Fallback: simulate agent response
        if agent_id == "maintenance_advisor":
            response = (
                f"M-204 is in good operational status. Based on the maintenance note, the bearing "
                f"replacement was successful and the machine is cleared for 72 hours. No additional "
                f"maintenance is needed before then."
            )
        else:  # mes_assistant
            response = (
                f"M-204 is ready to schedule. Given the recent bearing replacement and 72-hour "
                f"clearance window, I can allocate it for the next production run."
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
        # Read back the count to confirm
        with conn.cursor() as cur:
            cur.execute(
                f"SELECT count(*) FROM {TABLE} WHERE namespace=%s AND session_id=%s",
                [NAMESPACE, SESSION_ID],
            )
            count = cur.fetchone()[0]
    print(f"Memory now: {count} total rows\n")
    return response


def seed():
    """Seed the memory table with a prior maintenance note for context."""
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"""INSERT INTO {TABLE} (namespace, session_id, agent_id, role, content)
                   VALUES (%s, %s, %s, %s, %s)""",
                [
                    NAMESPACE,
                    SESSION_ID,
                    "maintenance_advisor",
                    "assistant",
                    "M-204: bearing replaced at 08:15. Cleared for 72 hours, then re-inspect.",
                ],
            )
            cur.execute(
                f"SELECT * FROM {TABLE} WHERE namespace=%s AND session_id=%s",
                [NAMESPACE, SESSION_ID],
            )
            rows = cur.fetchall()
    print(f"Seeding shared memory with a maintenance note...")
    print(f"  Seed row: {rows[0] if rows else '(none)'}\n")


def maintenance():
    """Ask the maintenance advisor a question."""
    print("1. Maintenance Advisor turn:")
    _call_agent("maintenance_advisor", "Is M-204 cleared to run the next shift?")


def mes():
    """Ask the MES assistant a question."""
    print("2. MES Assistant turn:")
    _call_agent("mes_assistant", "Is M-204 cleared to run the next shift?")


def main():
    ap = argparse.ArgumentParser(
        description="Agent memory — two agents share one governed Lakebase table"
    )
    ap.add_argument(
        "--step",
        choices=["seed", "maintenance", "mes"],
        help="Run just one step (default: run all)",
    )
    args = ap.parse_args()

    if args.step == "seed":
        seed()
        return
    if args.step == "maintenance":
        maintenance()
        return
    if args.step == "mes":
        mes()
        return

    # Full story
    seed()
    maintenance()
    mes()
    print("Done. Both agents wrote to and read from the same governed table.")


if __name__ == "__main__":
    main()
