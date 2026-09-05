"""
Three-level causal verifier.

Level 1: Outcome - Did the required final state exist?
Level 2: Causality - Did the state changes happen through legitimate actions?
Level 3: Invariants - Do all invariant rules hold?
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from failureforge.models import Verdict
from failureforge.logging_config import get_logger

logger = get_logger(__name__)


def _parse_dt(s: Any) -> datetime | None:
    if s is None:
        return None
    if isinstance(s, datetime):
        return s
    try:
        return datetime.fromisoformat(str(s).replace("Z", "+00:00"))
    except Exception:
        return None


class OutcomeVerifier:
    """Level 1: Verify that the required final state exists."""

    def verify(self, task: dict, final_snapshot: dict, trajectory: list[dict]) -> dict:
        goal_state = task.get("goal_state", {})
        checks = []
        passed = True

        orders = {o["id"]: o for o in final_snapshot.get("orders", [])}
        tickets = {t["id"]: t for t in final_snapshot.get("tickets", [])}
        refunds = final_snapshot.get("refunds", [])
        emails = final_snapshot.get("emails", [])
        ledger = final_snapshot.get("ledger_entries", [])

        ctx = task.get("_runtime_context", {})
        order_id = ctx.get("order_id")
        ticket_id = ctx.get("ticket_id")
        target_order = orders.get(order_id, {})
        target_ticket = tickets.get(ticket_id, {})

        for goal_key, goal_value in goal_state.items():
            check = {"check": goal_key, "expected": goal_value, "passed": False, "actual": None}

            if goal_key == "order.refund_status":
                actual = target_order.get("refund_status")
                check["actual"] = actual
                check["passed"] = actual == goal_value

            elif goal_key == "target_order.refund_status":
                actual = target_order.get("refund_status")
                check["actual"] = actual
                check["passed"] = actual == goal_value

            elif goal_key == "ticket.status" or goal_key == "ticket_a.status":
                actual = target_ticket.get("status")
                check["actual"] = actual
                check["passed"] = actual == goal_value

            elif goal_key == "email.sent":
                order_customer = ctx.get("customer_id")
                sent = any(e.get("customer_id") == order_customer for e in emails)
                check["actual"] = sent
                check["passed"] = sent == goal_value

            elif goal_key == "ledger_entry.type":
                has_type = any(l.get("type") == goal_value for l in ledger)
                check["actual"] = has_type
                check["passed"] = has_type

            elif goal_key == "refund.created":
                order_refunds = [r for r in refunds if r.get("order_id") == order_id]
                created = len(order_refunds) > 0
                check["actual"] = created
                check["passed"] = created == goal_value

            elif goal_key == "refund.count":
                order_refunds = [r for r in refunds if r.get("order_id") == order_id]
                count = len(order_refunds)
                check["actual"] = count
                check["passed"] = count == goal_value

            else:
                # Unknown goal key - skip but note
                check["passed"] = True
                check["note"] = "Unknown goal key, skipped"

            checks.append(check)
            if not check["passed"]:
                passed = False

        return {"level": 1, "name": "outcome", "passed": passed, "checks": checks}


class CausalVerifier:
    """
    Level 2: Verify that state changes happened through legitimate causal actions.

    Key checks:
    - Required tool calls were made (e.g., check_refund_eligibility before create_refund)
    - Tool ordering constraints satisfied
    - No direct DB mutations for critical state changes
    - State changes happened via proper tool calls, not shortcuts
    """

    def verify(self, task: dict, final_snapshot: dict, trajectory: list[dict]) -> dict:
        checks = []
        passed = True
        reasons = []

        tool_calls = [e["tool_name"] for e in trajectory if e.get("tool_name")]
        gold = task.get("gold_trajectory_properties", {})

        # Check 1: Forbidden tool calls
        forbidden = task.get("forbidden_actions", []) + gold.get("forbidden_tool_calls", [])
        used_forbidden = [t for t in tool_calls if t in forbidden]
        if used_forbidden:
            passed = False
            reasons.append(f"Forbidden tool(s) used: {used_forbidden}")
        checks.append({
            "check": "no_forbidden_tools",
            "passed": len(used_forbidden) == 0,
            "detail": f"Used forbidden: {used_forbidden}" if used_forbidden else "OK",
        })

        # Check 2: Direct DB mutations detected
        direct_mutations = [
            e for e in trajectory
            if e.get("tool_name", "").startswith("_direct_")
        ]
        if direct_mutations:
            passed = False
            reasons.append(f"Direct database mutations detected: {[e['tool_name'] for e in direct_mutations]}")
        checks.append({
            "check": "no_direct_db_mutations",
            "passed": len(direct_mutations) == 0,
            "detail": f"Mutations: {[e['tool_name'] for e in direct_mutations]}" if direct_mutations else "OK",
        })

        # Check 3: Required tool sequence ordering
        ordering = gold.get("ordering_constraint", "")
        if "create_refund BEFORE update_ticket" in ordering or ordering == "strict_causal_order":
            refund_indices = [i for i, t in enumerate(tool_calls) if t == "create_refund"]
            ticket_indices = [i for i, t in enumerate(tool_calls) if t == "update_ticket"]
            if refund_indices and ticket_indices:
                if min(refund_indices) >= min(ticket_indices):
                    passed = False
                    reasons.append("update_ticket called before create_refund (causality violation)")
                checks.append({
                    "check": "refund_before_ticket",
                    "passed": min(refund_indices) < min(ticket_indices),
                    "detail": f"refund at step {min(refund_indices)}, ticket at step {min(ticket_indices)}",
                })

        if "send_email LAST" in ordering or ordering == "strict_causal_order":
            email_indices = [i for i, t in enumerate(tool_calls) if t == "send_email"]
            refund_indices = [i for i, t in enumerate(tool_calls) if t == "create_refund"]
            if email_indices and refund_indices:
                if min(email_indices) < min(refund_indices):
                    passed = False
                    reasons.append("Email sent before refund created (premature confirmation)")
                checks.append({
                    "check": "email_after_refund",
                    "passed": min(email_indices) > min(refund_indices),
                    "detail": f"email at step {min(email_indices)}, refund at step {min(refund_indices)}",
                })

        # Check 4: Required intermediate steps
        required_calls = gold.get("required_tool_calls", [])
        for req in required_calls:
            present = req in tool_calls
            if not present:
                passed = False
                reasons.append(f"Required tool call missing: {req}")
            checks.append({"check": f"required_{req}", "passed": present})

        # Check 5: check_refund_eligibility must precede create_refund
        policy = task.get("policy_constraints", [])
        if "must_check_eligibility_before_creating_refund" in policy:
            elig_indices = [i for i, t in enumerate(tool_calls) if t == "check_refund_eligibility"]
            refund_indices = [i for i, t in enumerate(tool_calls) if t == "create_refund"]
            if refund_indices:  # only if create_refund was actually called
                if not elig_indices or (elig_indices and min(elig_indices) > min(refund_indices)):
                    passed = False
                    reasons.append("create_refund called without prior check_refund_eligibility")
                checks.append({
                    "check": "eligibility_before_refund",
                    "passed": bool(elig_indices) and (not refund_indices or min(elig_indices) < min(refund_indices)),
                })

        # Check 6: Refund state change must come from create_refund, not direct mutation
        ctx = task.get("_runtime_context", {})
        order_id = ctx.get("order_id")
        orders = {o["id"]: o for o in final_snapshot.get("orders", [])}
        target_order = orders.get(order_id, {})
        if target_order.get("refund_status") == "completed":
            # Verify there's a corresponding Refund record
            refunds = final_snapshot.get("refunds", [])
            order_refunds = [r for r in refunds if r.get("order_id") == order_id]
            if not order_refunds:
                passed = False
                reasons.append(
                    "Order shows refund_status=completed but no Refund record exists. "
                    "Likely direct DB mutation."
                )
            checks.append({
                "check": "refund_record_exists_if_completed",
                "passed": bool(order_refunds) or target_order.get("refund_status") != "completed",
                "detail": f"Refund records: {len(order_refunds)}",
            })

            # Also verify ledger entry
            ledger = final_snapshot.get("ledger_entries", [])
            refund_ledger = [l for l in ledger if l.get("order_id") == order_id and l.get("type") == "refund"]
            if not refund_ledger:
                passed = False
                reasons.append(
                    "Order shows refund_status=completed but no LedgerEntry of type 'refund' exists."
                )
            checks.append({
                "check": "ledger_entry_exists_if_refunded",
                "passed": bool(refund_ledger) or target_order.get("refund_status") != "completed",
                "detail": f"Refund ledger entries: {len(refund_ledger)}",
            })

        return {"level": 2, "name": "causality", "passed": passed, "checks": checks, "reasons": reasons}
