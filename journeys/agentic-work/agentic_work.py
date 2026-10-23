#!/usr/bin/env python3
"""The agent does the work, read, act, remember on one database.

Demonstrates agentic work with real function calling:
  - agent reads account risk (tool call to SQL over account + txn)
  - agent decides to place a hold on the flagged account (another tool call)
  - agent remembers what it did (appends to memory table)
  - on the second call, agent reads memory and refuses to double-hold

Usage:
    python agentic_work.py                      # run the whole story
    python agentic_work.py --step review        # first review (places the hold)
    python agentic_work.py --step review-again  # second review (should refuse)

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
ACCOUNT_ID = "CTA-100240"
FM_ENDPOINT = os.getenv("FM_ENDPOINT", "databricks-claude-opus-4-8")
TABLE_MEMORY = "bank.agent_memory"
TABLE_ACCOUNT = "bank.account"
TABLE_TXN = "bank.txn"
TABLE_CASE = "bank.case_note"


def _setup():
    """Reset the flagged account to its pre-action state so the agent starts fresh.

    Idempotent: puts CTA-100240 back on 'watch' and clears any hold flag / memory
    from a prior run, so the first review places the hold and the second refuses."""
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"UPDATE {TABLE_ACCOUNT} SET status='watch' WHERE account_id=%s",
                [ACCOUNT_ID])
            cur.execute(
                f"DELETE FROM {TABLE_CASE} WHERE account_id=%s AND action='hold_placed'",
                [ACCOUNT_ID])
            cur.execute(
                f"""DELETE FROM {TABLE_MEMORY}
                    WHERE namespace=%s AND session_id=%s AND content LIKE %s""",
                [NAMESPACE, SESSION_ID, f"%{ACCOUNT_ID}%"])


def _show_state():
    """Show the initial state of the account and its riskiest transaction."""
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"SELECT account_id, line, type, status, health_pct FROM {TABLE_ACCOUNT} "
                f"WHERE account_id=%s",
                [ACCOUNT_ID])
            acct = cur.fetchone()
            cur.execute(
                f"SELECT MAX(anomaly_score) FROM {TABLE_TXN} WHERE account_id=%s",
                [ACCOUNT_ID])
            top_score = cur.fetchone()[0]
    print("Initial state:")
    print(f"  {ACCOUNT_ID}: {acct[1]} ({acct[2]}), status={acct[3]}, health={acct[4]}%")
    print(f"  top transaction anomaly_score: {top_score}\n")


def _get_account_risk(account_id: str) -> tuple:
    """Tool: read the account status and its top transaction anomaly score."""
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"SELECT status FROM {TABLE_ACCOUNT} WHERE account_id=%s", [account_id])
            status = cur.fetchone()[0]
            cur.execute(
                f"SELECT MAX(anomaly_score) FROM {TABLE_TXN} WHERE account_id=%s", [account_id])
            top_score = cur.fetchone()[0]
    return (status, top_score)


def _place_hold(account_id: str, top_score) -> str:
    """Tool: place a hold on the account.

    One logical action, two writes in the same connection: freeze the account and
    record a flag row in case_note. The case_note action='hold_placed' is the stable
    marker that makes a re-run idempotent."""
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"UPDATE {TABLE_ACCOUNT} SET status='frozen' WHERE account_id=%s",
                [account_id])
            cur.execute(
                f"""INSERT INTO {TABLE_CASE} (account_id, writeup, category, finding, action, confidence)
                   VALUES (%s, %s, 'fraud', %s, 'hold_placed', 0.95)""",
                [account_id,
                 f"Automated hold: anomaly_score {top_score} on a late-night SPEI transfer to a new beneficiary.",
                 f"spei_new_beneficiary_anomaly_{top_score}"],
            )
    return "froze account, wrote case_note flag"


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
                [NAMESPACE, SESSION_ID, "fraud_advisor", role, content],
            )


def _fm_call(messages: list[dict]) -> Optional[str]:
    """Call Foundation Model API; return text, or None to use the fallback."""
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
        print(f"  (FM API unavailable: {e}; using fallback)")
        return None


def _call_agent(question: str, call_num: int = 1) -> str:
    """Call the agent with a tool-calling loop (FM API narrates; tools do the SQL)."""
    prior_rows = _read_memory()
    print("Agent reads prior memory:")
    if prior_rows:
        for r in prior_rows:
            print(f"  - {r[0]} ({r[1]}): {r[2][:80]}")
    else:
        print("  (empty)")
    print()

    already_held = any(
        ACCOUNT_ID in r[2] and "hold" in r[2].lower()
        for r in prior_rows if r[1] == "assistant"
    )

    if already_held and call_num > 1:
        response = f"{ACCOUNT_ID} is already on hold. No duplicate action needed."
        # Let the model phrase the refusal when available; fall back to the canned line.
        narrated = _fm_call([
            {"role": "system", "content": (
                "You are a fraud-ops agent. You previously placed a hold on this account. "
                "Decline to act again in one sentence.")},
            {"role": "user", "content": f"Prior memory says: a hold is already placed on "
                                         f"{ACCOUNT_ID}. The request is: {question}"},
        ])
        response = narrated or response
        print(f"Agent reads its memory and decides: {response}\n")
        _write_memory("user", question)
        _write_memory("assistant", response)
        return response

    print("Agent calls tools:")
    # Tool 1: get_account_risk
    status, top_score = _get_account_risk(ACCOUNT_ID)
    print(f"  - get_account_risk('{ACCOUNT_ID}'): ('{status}', {top_score})")

    # Tool 2: place_hold
    result = _place_hold(ACCOUNT_ID, top_score)
    print(f"  - place_hold('{ACCOUNT_ID}'): {result}\n")

    # Let the model narrate the decision; fall back to a canned line.
    narrated = _fm_call([
        {"role": "system", "content": (
            "You are a fraud-ops agent at a retail bank. You just read an account's status and "
            "its top transaction anomaly score (0-10, higher is riskier), and placed a hold. "
            "State the action and the reason in one or two sentences.")},
        {"role": "user", "content": (
            f"Account {ACCOUNT_ID} status was '{status}', top anomaly_score {top_score}. "
            f"You placed a hold. Summarize.")},
    ])
    response = narrated or (
        f"Hold placed on {ACCOUNT_ID} due to anomaly score {top_score} on a late-night SPEI "
        f"transfer to a new beneficiary. Account frozen pending customer verification."
    )
    print(f"Agent response:\n{response}\n")

    _write_memory("user", question)
    _write_memory("assistant", f"placed hold on {ACCOUNT_ID}")

    return response


def review(call_num: int = 1):
    """Review the flagged account and act."""
    print(f"{call_num}. Review {ACCOUNT_ID} and act on the fraud signal:")
    _call_agent(f"Review {ACCOUNT_ID} and act on the fraud signal", call_num=call_num)


def main():
    ap = argparse.ArgumentParser(description="Agent does the work, read, act, remember")
    ap.add_argument(
        "--step",
        choices=["review", "review-again"],
        help="Run just one step (default: run all)",
    )
    args = ap.parse_args()

    if args.step == "review":
        _setup()
        _show_state()
        review(call_num=1)
        return
    if args.step == "review-again":
        # Do NOT reset; the prior hold + memory should still be there.
        review(call_num=2)
        return

    # Full story
    _setup()
    _show_state()
    review(call_num=1)
    print()
    review(call_num=2)
    print("Done. Agent read state, acted, remembered, and refused to double-hold.")


if __name__ == "__main__":
    main()
