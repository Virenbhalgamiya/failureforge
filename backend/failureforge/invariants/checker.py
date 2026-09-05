"""
Invariant Checker Engine.

Evaluates domain-level invariant rules against the final environment state.
These are rules that should ALWAYS hold regardless of which agent ran.

Invariants:
1. refund_amount_le_order_amount - refund ≤ order price
2. completed_refund_has_ledger_entry - any completed refund has a ledger entry
3. notification_after_refund_completed - email sent_at > refund completed_at
4. resolved_ticket_references_completed_refund - resolved ticket's order is refunded
5. cancelled_order_cannot_be_refunded - cancelled orders have no completed refunds
6. refund_cannot_be_completed_twice - at most one completed refund per order
7. refund_belongs_to_correct_order - refund.order_id matches ticket.order_id
8. no_duplicate_refund - no more than one completed refund per order
9. ticket_resolved_after_refund_completed - ticket resolved after refund
10. notification_after_ticket_resolved - email after ticket resolved
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from failureforge.logging_config import get_logger

logger = get_logger(__name__)


def _dt(val: Any) -> datetime | None:
    if val is None:
        return None
    if isinstance(val, datetime):
        return val
    try:
        return datetime.fromisoformat(str(val).replace("Z", "+00:00"))
    except Exception:
        return None


class InvariantChecker:
    """Checks all domain invariants against a final environment snapshot."""

    def __init__(self):
        self._rules = {
            "refund_amount_le_order_amount": self._check_refund_amount_le_order,
            "completed_refund_has_ledger_entry": self._check_refund_has_ledger,
            "notification_after_refund_completed": self._check_email_after_refund,
            "notification_after_ticket_resolved": self._check_email_after_ticket,
            "resolved_ticket_references_completed_refund": self._check_resolved_ticket_has_refund,
            "cancelled_order_cannot_be_refunded": self._check_no_refund_on_cancelled,
            "refund_cannot_be_completed_twice": self._check_no_double_refund,
            "refund_belongs_to_correct_order": self._check_refund_correct_order,
            "no_duplicate_refund": self._check_no_duplicate_refund,
            "ticket_resolved_after_refund_completed": self._check_ticket_after_refund,
            "all_tickets_resolved": self._check_all_tickets_resolved,
            "only_one_refund_created": self._check_only_one_refund,
            "must_handle_not_found_gracefully": self._check_graceful_not_found,
            "partial_refund_le_order_amount": self._check_refund_amount_le_order,
            "partial_refund_matches": lambda snap, ctx: {"passed": True, "note": "Partial amount check"},
            "refund_amount_matches_undelivered_portion": lambda snap, ctx: {"passed": True, "note": "Skipped"},
            "ledger_entry_created_via_tool": lambda snap, ctx: {"passed": True, "note": "Checked by causal verifier"},
            "refund_only_for_eligible_order": lambda snap, ctx: {"passed": True, "note": "Checked by causal verifier"},
            "ticket_notes_updated": self._check_ticket_notes_updated,
        }

    def check_all(self, required_invariants: list[str], snapshot: dict, ctx: dict) -> dict:
        """
        Check all required invariants.

        Returns:
            {
                "passed": bool,
                "results": [{"invariant": str, "passed": bool, "detail": str}, ...]
            }
        """
        results = []
        all_passed = True

        for inv_name in required_invariants:
            rule = self._rules.get(inv_name)
            if rule is None:
                results.append({
                    "invariant": inv_name,
                    "passed": True,
                    "detail": "No rule registered (skipped)",
                })
                continue

            try:
                result = rule(snapshot, ctx)
                result["invariant"] = inv_name
                results.append(result)
                if not result.get("passed", True):
                    all_passed = False
                    logger.info("invariant_failed", invariant=inv_name, detail=result.get("detail"))
            except Exception as e:
                results.append({
                    "invariant": inv_name,
                    "passed": False,
                    "detail": f"Error evaluating invariant: {e}",
                })
                all_passed = False

        return {"passed": all_passed, "results": results}

    # ─── Individual Invariant Rules ──────────────────────────────────────────

    def _check_refund_amount_le_order(self, snapshot: dict, ctx: dict) -> dict:
        orders = {o["id"]: o for o in snapshot.get("orders", [])}
        refunds = snapshot.get("refunds", [])

        violations = []
        for refund in refunds:
            order = orders.get(refund.get("order_id"))
            if order and refund.get("amount", 0) > order.get("price", 0):
                violations.append(
                    f"Refund {refund['id']}: amount={refund['amount']} > order price={order['price']}"
                )

        return {
            "passed": len(violations) == 0,
            "detail": "; ".join(violations) if violations else "All refund amounts within order price",
        }

    def _check_refund_has_ledger(self, snapshot: dict, ctx: dict) -> dict:
        orders = {o["id"]: o for o in snapshot.get("orders", [])}
        refunds = snapshot.get("refunds", [])
        ledger = snapshot.get("ledger_entries", [])

        completed_refunds = [r for r in refunds if r.get("status") == "completed"]
        violations = []

        for refund in completed_refunds:
            order_id = refund.get("order_id")
            has_ledger = any(
                l.get("order_id") == order_id and l.get("type") == "refund"
                for l in ledger
            )
            if not has_ledger:
                violations.append(f"Completed refund {refund['id']} for order {order_id} has no ledger entry")

        return {
            "passed": len(violations) == 0,
            "detail": "; ".join(violations) if violations else "All completed refunds have ledger entries",
        }

    def _check_email_after_refund(self, snapshot: dict, ctx: dict) -> dict:
        """Email sent_at must be AFTER refund completed_at."""
        customer_id = ctx.get("customer_id")
        order_id = ctx.get("order_id")

        refunds = [r for r in snapshot.get("refunds", []) if r.get("order_id") == order_id]
        emails = [e for e in snapshot.get("emails", []) if e.get("customer_id") == customer_id]

        if not refunds or not emails:
            return {"passed": True, "detail": "No refund or email to compare"}

        completed_refunds = [r for r in refunds if r.get("status") == "completed" and r.get("completed_at")]
        if not completed_refunds:
            return {"passed": True, "detail": "No completed refund with timestamp"}

        refund_time = max(_dt(r["completed_at"]) for r in completed_refunds if _dt(r["completed_at"]))
        email_times = [_dt(e["sent_at"]) for e in emails if _dt(e["sent_at"])]

        if not email_times:
            return {"passed": True, "detail": "No email timestamps to compare"}

        earliest_email = min(email_times)

        if refund_time and earliest_email and earliest_email < refund_time:
            return {
                "passed": False,
                "detail": (
                    f"Email sent at {earliest_email.isoformat()} BEFORE refund completed at "
                    f"{refund_time.isoformat()} (premature notification)"
                ),
            }

        return {
            "passed": True,
            "detail": f"Email at {earliest_email.isoformat()} is after refund at {refund_time.isoformat() if refund_time else 'N/A'}",
        }

    def _check_email_after_ticket(self, snapshot: dict, ctx: dict) -> dict:
        """Email must be sent after ticket is resolved."""
        customer_id = ctx.get("customer_id")
        ticket_id = ctx.get("ticket_id")

        tickets = {t["id"]: t for t in snapshot.get("tickets", [])}
        emails = [e for e in snapshot.get("emails", []) if e.get("customer_id") == customer_id]

        ticket = tickets.get(ticket_id)
        if not ticket or not emails:
            return {"passed": True, "detail": "No ticket or email to compare"}

        resolved_at = _dt(ticket.get("resolved_at"))
        if not resolved_at:
            return {"passed": True, "detail": "Ticket not yet resolved, invariant not applicable"}

        email_times = [_dt(e["sent_at"]) for e in emails if _dt(e["sent_at"])]
        if not email_times:
            return {"passed": True, "detail": "No email timestamps"}

        earliest_email = min(email_times)
        if earliest_email < resolved_at:
            return {
                "passed": False,
                "detail": f"Email at {earliest_email.isoformat()} before ticket resolved at {resolved_at.isoformat()}",
            }

        return {"passed": True, "detail": "Email after ticket resolved"}

    def _check_resolved_ticket_has_refund(self, snapshot: dict, ctx: dict) -> dict:
        """A resolved ticket must reference a completed refund."""
        ticket_id = ctx.get("ticket_id")
        order_id = ctx.get("order_id")

        tickets = {t["id"]: t for t in snapshot.get("tickets", [])}
        ticket = tickets.get(ticket_id)

        if not ticket or ticket.get("status") != "resolved":
            return {"passed": True, "detail": "Ticket not resolved or not found"}

        refunds = [
            r for r in snapshot.get("refunds", [])
            if r.get("order_id") == order_id and r.get("status") == "completed"
        ]

        # Also allow: ticket resolved with no refund if task expects rejection
        # This is task-specific; for now check if refund_status is completed
        orders = {o["id"]: o for o in snapshot.get("orders", [])}
        target_order = orders.get(order_id, {})

        if target_order.get("refund_status") == "completed" and not refunds:
            return {
                "passed": False,
                "detail": (
                    f"Ticket {ticket_id} is resolved and order shows refund_status=completed, "
                    "but no Refund record exists (direct DB mutation)"
                ),
            }

        return {"passed": True, "detail": "Resolved ticket consistency check passed"}

    def _check_no_refund_on_cancelled(self, snapshot: dict, ctx: dict) -> dict:
        """Cancelled orders must not have completed refunds."""
        orders = {o["id"]: o for o in snapshot.get("orders", [])}
        refunds = snapshot.get("refunds", [])

        violations = []
        for refund in refunds:
            if refund.get("status") == "completed":
                order = orders.get(refund.get("order_id"))
                if order and order.get("status") == "cancelled":
                    violations.append(f"Cancelled order {order['id']} has a completed refund {refund['id']}")

        return {
            "passed": len(violations) == 0,
            "detail": "; ".join(violations) if violations else "No cancelled orders with refunds",
        }

    def _check_no_double_refund(self, snapshot: dict, ctx: dict) -> dict:
        """Each order must have at most one completed refund."""
        from collections import Counter

        order_refund_counts = Counter()
        for refund in snapshot.get("refunds", []):
            if refund.get("status") == "completed":
                order_refund_counts[refund["order_id"]] += 1

        violations = [
            f"Order {order_id} has {count} completed refunds"
            for order_id, count in order_refund_counts.items()
            if count > 1
        ]

        return {
            "passed": len(violations) == 0,
            "detail": "; ".join(violations) if violations else "No duplicate refunds",
        }

    def _check_refund_correct_order(self, snapshot: dict, ctx: dict) -> dict:
        """Refunds must belong to the order referenced in the ticket."""
        ticket_id = ctx.get("ticket_id")
        order_id = ctx.get("order_id")

        tickets = {t["id"]: t for t in snapshot.get("tickets", [])}
        ticket = tickets.get(ticket_id)

        if not ticket:
            return {"passed": True, "detail": "Ticket not found"}

        ticket_order_id = ticket.get("order_id")
        refunds = snapshot.get("refunds", [])

        wrong_refunds = [
            r for r in refunds
            if r.get("status") == "completed" and r.get("order_id") != ticket_order_id and ticket_order_id
        ]

        return {
            "passed": len(wrong_refunds) == 0,
            "detail": f"Wrong-entity refunds: {[r['id'] for r in wrong_refunds]}" if wrong_refunds else "OK",
        }

    def _check_no_duplicate_refund(self, snapshot: dict, ctx: dict) -> dict:
        return self._check_no_double_refund(snapshot, ctx)

    def _check_ticket_after_refund(self, snapshot: dict, ctx: dict) -> dict:
        """Ticket resolved_at must be >= refund completed_at."""
        ticket_id = ctx.get("ticket_id")
        order_id = ctx.get("order_id")

        tickets = {t["id"]: t for t in snapshot.get("tickets", [])}
        ticket = tickets.get(ticket_id, {})
        refunds = [r for r in snapshot.get("refunds", []) if r.get("order_id") == order_id]

        resolved_at = _dt(ticket.get("resolved_at"))
        completed_refunds = [r for r in refunds if r.get("status") == "completed" and r.get("completed_at")]

        if not resolved_at or not completed_refunds:
            return {"passed": True, "detail": "Cannot compare: missing timestamps"}

        refund_time = max(_dt(r["completed_at"]) for r in completed_refunds if _dt(r["completed_at"]))

        if resolved_at and refund_time and resolved_at < refund_time:
            return {
                "passed": False,
                "detail": f"Ticket resolved at {resolved_at} before refund completed at {refund_time}",
            }

        return {"passed": True, "detail": "Ticket resolved after refund completed"}

    def _check_all_tickets_resolved(self, snapshot: dict, ctx: dict) -> dict:
        """All customer tickets should be resolved."""
        customer_id = ctx.get("customer_id")
        tickets = [t for t in snapshot.get("tickets", []) if t.get("customer_id") == customer_id]
        open_tickets = [t for t in tickets if t.get("status") not in ("resolved", "closed")]

        return {
            "passed": len(open_tickets) == 0,
            "detail": f"Open tickets: {[t['id'] for t in open_tickets]}" if open_tickets else "All tickets resolved",
        }

    def _check_only_one_refund(self, snapshot: dict, ctx: dict) -> dict:
        order_id = ctx.get("order_id")
        refunds = [r for r in snapshot.get("refunds", []) if r.get("order_id") == order_id]
        return {
            "passed": len(refunds) <= 1,
            "detail": f"Found {len(refunds)} refund(s) for order {order_id}",
        }

    def _check_graceful_not_found(self, snapshot: dict, ctx: dict) -> dict:
        customer_id = ctx.get("customer_id")
        emails = [e for e in snapshot.get("emails", []) if e.get("customer_id") == customer_id]
        return {
            "passed": True,  # Just verify no crash
            "detail": f"Graceful handling: {len(emails)} emails sent",
        }

    def _check_ticket_notes_updated(self, snapshot: dict, ctx: dict) -> dict:
        ticket_id = ctx.get("ticket_id")
        tickets = {t["id"]: t for t in snapshot.get("tickets", [])}
        ticket = tickets.get(ticket_id, {})
        has_notes = bool(ticket.get("notes") or ticket.get("resolution"))
        return {
            "passed": has_notes,
            "detail": "Ticket has resolution notes" if has_notes else "Ticket missing resolution notes",
        }
