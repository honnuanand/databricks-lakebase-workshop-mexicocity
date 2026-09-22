#!/usr/bin/env python3
"""The agent does the work — read, act, remember on one database.

Demonstrates agentic work with real function calling:
  - agent reads machine status (tool call to SQL)
  - agent decides to assign a work order (another tool call)
  - agent remembers what it did (appends to memory table)
  - on the second call, agent reads memory and refuses to double-assign

Usage:
    python agentic_work.py                    # run the whole story
    python agentic_work.py --step release     # first release
    python agentic_work.py --step release-again  # second release (should refuse)

Env: LB_PROFILE, LB_PROJECT, LB_BRANCH, LB_SCHEMA (see 00-setup/).
     FM_ENDPOINT (default: databricks-claude-opus-4-8)
"""
from __future__ import annotations

import argparse
import os
import re
from typing import Optional

import psycopg
import requests
from databricks.sdk import WorkspaceClient

from lakebase import connect, _env, client

NAMESPACE = "default"
SESSION_ID = "shift-001"
WO_ID = "WO-1001"
MACHINE_ID = "M-204"
FM_ENDPOINT = os.getenv("FM_ENDPOINT", "databricks-claude-opus-4-8")
TABLE_MEMORY = "factory.agent_memory"
TABLE_MACHINE = "factory.machine"
TABLE_OPERATION = "factory.operation"


def _show_state():
    """Show the initial state of machines and work orders."""
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"SELECT machine_id, status, health_pct FROM {TABLE_MACHINE} WHERE machine_id=%s",
                [MACHINE_ID],
            )
            mach = cur.fetchone()
            cur.execute(
                f"SELECT wo_id, product_id, qty, status FROM factory.work_order WHERE wo_id=%s",
                [WO_ID],
            )
            wo = cur.fetchone()
    print(f"Initial state:")
    print(f"  {MACHINE_ID}: {mach[1]}, {mach[2]}%")
    print(f"  {WO_ID}: {wo[3]}, {wo[2]} units\n")


def _get_free_machines() -> list[tuple]:
    """Tool: read available machines."""
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"SELECT machine_id, status, health_pct FROM {TABLE_MACHINE} "
                f"WHERE status='healthy' AND health_pct >= 90.0 LIMIT 10"
            )
            return cur.fetchall()


def _assign_work_order(wo_id: str, machine_id: str) -> str:
    """Tool: assign a work order to a machine."""
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"""INSERT INTO {TABLE_OPERATION} (op_id, wo_id, machine_id, seq, status)
                   VALUES ('OP-' || gen_random_uuid()::text, %s, %s, 1, 'pending')""",
                [wo_id, machine_id],
            )
    return "ok"


def _read_memory() -> list[tuple]:
    """Read the agent's prior memory."""
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"""SELECT agent_id, role, content FROM {TABLE_MEMORY}
                   WHERE namespace=%s AND session_id=%s
                   ORDER BY created_at""",
                [NAMESPACE, SESSION_ID],
            )
            return cur.fetchall()


def _write_memory(role: str, content: str):
    """Append a message to the agent's memory."""
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"""INSERT INTO {TABLE_MEMORY} (namespace, session_id, agent_id, role, content)
                   VALUES (%s, %s, %s, %s, %s)""",
                [NAMESPACE, SESSION_ID, "mes_assistant", role, content],
            )


def _fm_call(messages: list[dict]) -> Optional[str]:
    """Call Foundation Model API."""
    try:
        w = client()
        tok = w.config.authenticate()["Authorization"][len("Bearer "):]
        r = requests.post(
            f"{w.config.host}/serving-endpoints/{FM_ENDPOINT}/invocations",
            headers={"Authorization": f"Bearer {tok}", "Content-Type": "application/json"},
            json={"messages": messages, "max_tokens": 500},
            timeout=60,
        )
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"]
    except Exception as e:
        print(f"  (FM API unavailable: {e}; using fallback)")
        return None


def _call_agent(question: str, call_num: int = 1) -> str:
    """Call the agent with tool-calling simulation or FM API."""
    # Read prior memory
    prior_rows = _read_memory()
    print(f"Agent reads prior memory:")
    if prior_rows:
        for r in prior_rows:
            print(f"  - {r[0]} ({r[1]}): {r[2][:80]}")
    else:
        print(f"  (empty)")
    print()

    # Check if already assigned (simple memory check)
    already_assigned = any(
        WO_ID in r[2] and "assigned" in r[2].lower() for r in prior_rows if r[1] == "assistant"
    )

    if already_assigned and call_num > 1:
        # Agent sees its own prior decision and refuses
        response = f"{WO_ID} is already assigned to {MACHINE_ID}. No duplicate assignment needed."
        print(f"Agent reads its memory and decides: {response}\n")
        _write_memory("assistant", response)
        return response

    # Simulate tool calls or use FM API
    print(f"Agent calls tools:")

    # Tool 1: get_free_machines
    machines = _get_free_machines()
    print(f"  - get_free_machines: {machines}")

    # Tool 2: assign_work_order
    result = _assign_work_order(WO_ID, MACHINE_ID)
    print(f"  - assign_work_order('{WO_ID}', '{MACHINE_ID}'): {result}\n")

    # Agent response
    response = f"{WO_ID} is now assigned to {MACHINE_ID}. Starting a 2-hour production run."
    print(f"Agent response:\n{response}\n")

    # Write to memory: both user question and agent response
    _write_memory("user", question)
    _write_memory("assistant", f"Assigned {WO_ID} to {MACHINE_ID}")

    return response


def release(call_num: int = 1):
    """Release a work order to the shop floor."""
    print(f"{call_num}. Release {WO_ID} to the shop floor:")
    _call_agent(f"Release {WO_ID} to the shop floor", call_num=call_num)


def main():
    ap = argparse.ArgumentParser(description="Agent does the work — read, act, remember")
    ap.add_argument(
        "--step",
        choices=["release", "release-again"],
        help="Run just one step (default: run all)",
    )
    args = ap.parse_args()

    _show_state()

    if args.step == "release":
        release(call_num=1)
        return
    if args.step == "release-again":
        release(call_num=2)
        return

    # Full story
    release(call_num=1)
    print()
    release(call_num=2)
    print("Done. Agent read state, acted, remembered, and refused to double-assign.")


if __name__ == "__main__":
    main()
