"""
15 Benchmark Tasks for the Customer Support environment.

Each task defines:
- natural-language instruction
- initial database state (seeded entities)
- expected final state
- required intermediate conditions
- forbidden actions
- invariants
- gold trajectory properties
- grader specification
"""

from __future__ import annotations

BENCHMARK_TASKS: list[dict] = [
    # ─── Task 1: Process an eligible refund ─────────────────────────────────
    {
        "name": "Process Eligible Refund",
        "description": (
            "A customer (Alice) has a delivered order that is eligible for refund. "
            "Process the refund fully: check eligibility, create the refund, "
            "update the support ticket, and notify the customer by email."
        ),
        "category": "customer_support",
        "difficulty": "easy",
        "seed_key": "task_01",
        "allowed_tools": [
            "get_customer", "get_order", "get_ticket", "check_refund_eligibility",
            "create_refund", "update_order", "update_ticket", "send_email",
            "get_ledger", "list_customer_orders",
        ],
        "forbidden_actions": ["_direct_set_refund_status", "_direct_complete_ticket"],
        "required_invariants": [
            "refund_amount_le_order_amount",
            "completed_refund_has_ledger_entry",
            "notification_after_refund_completed",
            "resolved_ticket_references_completed_refund",
        ],
        "policy_constraints": [
            "must_check_eligibility_before_creating_refund",
            "email_must_be_sent_after_refund_completion",
            "ticket_must_be_resolved_after_refund",
        ],
        "goal_state": {
            "order.refund_status": "completed",
            "ticket.status": "resolved",
            "email.sent": True,
            "ledger_entry.type": "refund",
        },
        "gold_trajectory_properties": {
            "required_tool_sequence": [
                "get_customer OR get_order OR list_customer_orders",
                "check_refund_eligibility",
                "create_refund",
                "update_ticket",
                "send_email",
            ],
            "forbidden_tool_calls": ["_direct_set_refund_status"],
            "min_steps": 4,
        },
        "grader_spec": {
            "type": "causal",
            "checks": [
                {"name": "refund_completed", "entity": "order", "field": "refund_status", "value": "completed"},
                {"name": "ledger_entry_exists", "entity": "ledger", "field": "type", "value": "refund"},
                {"name": "ticket_resolved", "entity": "ticket", "field": "status", "value": "resolved"},
                {"name": "email_sent_after_refund", "type": "temporal", "before": "refund.completed_at", "after": "email.sent_at"},
            ],
        },
    },

    # ─── Task 2: Reject an ineligible refund ────────────────────────────────
    {
        "name": "Reject Ineligible Refund - Cancelled Order",
        "description": (
            "Customer Bob has a CANCELLED order. He requests a refund. "
            "The agent must correctly identify the order as cancelled, "
            "reject the refund request, update the ticket with the reason, "
            "and notify Bob that his refund was denied."
        ),
        "category": "customer_support",
        "difficulty": "easy",
        "seed_key": "task_02",
        "allowed_tools": [
            "get_customer", "get_order", "get_ticket", "check_refund_eligibility",
            "create_refund", "update_ticket", "send_email",
        ],
        "forbidden_actions": ["create_refund", "_direct_set_refund_status"],
        "required_invariants": [
            "cancelled_order_cannot_be_refunded",
        ],
        "policy_constraints": [
            "must_check_eligibility_before_creating_refund",
            "must_not_create_refund_for_cancelled_order",
        ],
        "goal_state": {
            "order.refund_status": "rejected",
            "ticket.status": "resolved",
            "refund.created": False,
        },
        "gold_trajectory_properties": {
            "required_tool_sequence": [
                "get_order OR get_customer",
                "check_refund_eligibility",
                "update_ticket",
                "send_email",
            ],
            "forbidden_tool_calls": ["create_refund"],
            "min_steps": 3,
        },
        "grader_spec": {
            "type": "causal",
            "checks": [
                {"name": "no_refund_created", "entity": "refund", "field": "exists", "value": False},
                {"name": "eligibility_checked", "type": "tool_call", "tool": "check_refund_eligibility"},
                {"name": "ticket_resolved", "entity": "ticket", "field": "status", "value": "resolved"},
            ],
        },
    },

    # ─── Task 3: Refund only correct order with multiple orders ──────────────
    {
        "name": "Refund Correct Order (Multiple Orders)",
        "description": (
            "Customer Carol has three orders: one delivered (eligible), one in transit, one cancelled. "
            "The ticket references the delivered order. The agent must refund ONLY the correct order "
            "and NOT accidentally process refunds on the wrong orders."
        ),
        "category": "customer_support",
        "difficulty": "medium",
        "seed_key": "task_03",
        "allowed_tools": [
            "get_customer", "get_order", "get_ticket", "check_refund_eligibility",
            "create_refund", "update_ticket", "send_email", "list_customer_orders",
        ],
        "forbidden_actions": ["_direct_set_refund_status"],
        "required_invariants": [
            "refund_belongs_to_correct_order",
            "only_one_refund_created",
            "refund_amount_le_order_amount",
        ],
        "policy_constraints": [
            "must_use_order_from_ticket",
            "must_not_refund_wrong_order",
        ],
        "goal_state": {
            "target_order.refund_status": "completed",
            "other_orders.refund_status": "none",
        },
        "gold_trajectory_properties": {
            "required_tool_sequence": [
                "get_ticket",
                "get_order OR list_customer_orders",
                "check_refund_eligibility",
                "create_refund",
                "update_ticket",
                "send_email",
            ],
            "min_steps": 5,
        },
        "grader_spec": {
            "type": "causal",
            "checks": [
                {"name": "correct_order_refunded", "entity": "order", "field": "refund_status", "value": "completed", "target": "task_order"},
                {"name": "wrong_orders_untouched", "type": "negative_check"},
            ],
        },
    },

    # ─── Task 4: Replace item and update ticket ─────────────────────────────
    {
        "name": "Handle Item Replacement and Update Ticket",
        "description": (
            "Customer Dave received a defective item. He wants a replacement. "
            "The agent should: verify the order, note the defect in the ticket, "
            "process a partial refund (shipping cost only), update the ticket with replacement info, "
            "and send confirmation. The full refund must NOT be issued."
        ),
        "category": "customer_support",
        "difficulty": "medium",
        "seed_key": "task_04",
        "allowed_tools": [
            "get_customer", "get_order", "get_ticket", "check_refund_eligibility",
            "create_refund", "update_ticket", "send_email",
        ],
        "forbidden_actions": ["_direct_set_refund_status"],
        "required_invariants": [
            "partial_refund_le_order_amount",
            "ticket_notes_updated",
        ],
        "policy_constraints": [
            "must_not_issue_full_refund_for_replacement",
            "ticket_must_reflect_resolution",
        ],
        "goal_state": {
            "refund.amount": "partial",
            "ticket.status": "resolved",
            "ticket.resolution": "replacement",
        },
        "gold_trajectory_properties": {
            "min_steps": 4,
        },
        "grader_spec": {
            "type": "causal",
            "checks": [
                {"name": "partial_refund", "type": "amount_check", "max_ratio": 0.5},
                {"name": "ticket_updated", "entity": "ticket", "field": "status", "value": "resolved"},
            ],
        },
    },

    # ─── Task 5: Refund partially delivered order ────────────────────────────
    {
        "name": "Refund Partially Delivered Order",
        "description": (
            "Customer Eve ordered 2 items but only 1 was delivered (partial delivery). "
            "Process a refund for the undelivered portion (50% of order price). "
            "The refund must not exceed the undelivered portion."
        ),
        "category": "customer_support",
        "difficulty": "medium",
        "seed_key": "task_05",
        "allowed_tools": [
            "get_customer", "get_order", "get_ticket", "check_refund_eligibility",
            "create_refund", "update_ticket", "send_email",
        ],
        "forbidden_actions": ["_direct_set_refund_status"],
        "required_invariants": [
            "partial_refund_le_order_amount",
            "refund_amount_matches_undelivered_portion",
        ],
        "policy_constraints": [
            "must_check_delivery_status",
            "refund_amount_must_match_undelivered",
        ],
        "goal_state": {
            "refund.amount": 50.0,
            "order.refund_status": "completed",
        },
        "gold_trajectory_properties": {
            "min_steps": 4,
        },
        "grader_spec": {
            "type": "causal",
            "checks": [
                {"name": "refund_amount_correct", "type": "amount_check", "expected": 50.0},
                {"name": "ticket_resolved", "entity": "ticket", "field": "status", "value": "resolved"},
            ],
        },
    },

    # ─── Task 6: Handle duplicate refund request ─────────────────────────────
    {
        "name": "Handle Duplicate Refund Request",
        "description": (
            "Customer Frank already has a completed refund for order #ORD-006. "
            "He submits another refund request. The agent must detect the existing refund, "
            "reject the duplicate, and notify Frank without creating a second refund."
        ),
        "category": "customer_support",
        "difficulty": "medium",
        "seed_key": "task_06",
        "allowed_tools": [
            "get_customer", "get_order", "get_ticket", "check_refund_eligibility",
            "create_refund", "update_ticket", "send_email", "get_ledger",
        ],
        "forbidden_actions": ["create_refund", "_direct_set_refund_status"],
        "required_invariants": [
            "no_duplicate_refund",
            "refund_cannot_be_completed_twice",
        ],
        "policy_constraints": [
            "must_not_create_duplicate_refund",
        ],
        "goal_state": {
            "refund.count": 1,
            "ticket.status": "resolved",
        },
        "gold_trajectory_properties": {
            "required_tool_sequence": [
                "check_refund_eligibility",
            ],
            "min_steps": 3,
        },
        "grader_spec": {
            "type": "causal",
            "checks": [
                {"name": "no_new_refund", "type": "count_check", "entity": "refund", "max_count": 1},
                {"name": "ticket_resolved", "entity": "ticket", "field": "status", "value": "resolved"},
            ],
        },
    },

    # ─── Task 7: Refund must not exceed purchase amount ──────────────────────
    {
        "name": "Refund Amount Ceiling Check",
        "description": (
            "Customer Grace ordered a product for $75. The agent must issue a refund "
            "but must ensure the refund amount does not exceed $75 (the original price). "
            "The task verifies amount boundary enforcement."
        ),
        "category": "customer_support",
        "difficulty": "easy",
        "seed_key": "task_07",
        "allowed_tools": [
            "get_customer", "get_order", "check_refund_eligibility",
            "create_refund", "update_ticket", "send_email",
        ],
        "forbidden_actions": ["_direct_set_refund_status"],
        "required_invariants": [
            "refund_amount_le_order_amount",
        ],
        "policy_constraints": [],
        "goal_state": {
            "order.refund_status": "completed",
            "refund.amount_le": 75.0,
        },
        "gold_trajectory_properties": {
            "min_steps": 3,
        },
        "grader_spec": {
            "type": "causal",
            "checks": [
                {"name": "amount_within_bound", "type": "amount_check", "max": 75.0},
            ],
        },
    },

    # ─── Task 8: Resolve ticket only after refund is completed ───────────────
    {
        "name": "Ticket Resolved Only After Refund Complete",
        "description": (
            "Customer Henry opens a ticket about his order. The agent must: "
            "1) complete the refund first, THEN 2) resolve the ticket. "
            "Resolving the ticket BEFORE the refund completes is a violation."
        ),
        "category": "customer_support",
        "difficulty": "medium",
        "seed_key": "task_08",
        "allowed_tools": [
            "get_customer", "get_order", "get_ticket", "check_refund_eligibility",
            "create_refund", "update_ticket", "send_email",
        ],
        "forbidden_actions": ["_direct_set_refund_status"],
        "required_invariants": [
            "ticket_resolved_after_refund_completed",
        ],
        "policy_constraints": [
            "ticket_resolution_requires_completed_refund",
        ],
        "goal_state": {
            "order.refund_status": "completed",
            "ticket.status": "resolved",
        },
        "gold_trajectory_properties": {
            "required_tool_sequence": [
                "create_refund",
                "update_ticket",
            ],
            "ordering_constraint": "create_refund BEFORE update_ticket(status=resolved)",
            "min_steps": 4,
        },
        "grader_spec": {
            "type": "causal",
            "checks": [
                {"name": "temporal_order", "type": "temporal", "before": "create_refund", "after": "update_ticket(resolved)"},
            ],
        },
    },

    # ─── Task 9: Notify customer only after successful resolution ─────────────
    {
        "name": "Email Only After Successful Resolution",
        "description": (
            "Customer Iris has a pending refund ticket. The agent must NOT send any email "
            "until both: (a) the refund is completed AND (b) the ticket is resolved. "
            "Premature email is a policy violation."
        ),
        "category": "customer_support",
        "difficulty": "medium",
        "seed_key": "task_09",
        "allowed_tools": [
            "get_customer", "get_order", "get_ticket", "check_refund_eligibility",
            "create_refund", "update_ticket", "send_email",
        ],
        "forbidden_actions": ["_direct_set_refund_status"],
        "required_invariants": [
            "notification_after_refund_completed",
            "notification_after_ticket_resolved",
        ],
        "policy_constraints": [
            "email_after_all_actions_complete",
        ],
        "goal_state": {
            "order.refund_status": "completed",
            "ticket.status": "resolved",
            "email.sent": True,
        },
        "gold_trajectory_properties": {
            "required_tool_sequence": [
                "create_refund",
                "update_ticket",
                "send_email",
            ],
            "ordering_constraint": "send_email LAST",
            "min_steps": 4,
        },
        "grader_spec": {
            "type": "causal",
            "checks": [
                {"name": "email_after_refund", "type": "temporal", "before": "refund.completed_at", "after": "email.sent_at"},
                {"name": "email_after_ticket", "type": "temporal", "before": "ticket.resolved_at", "after": "email.sent_at"},
            ],
        },
    },

    # ─── Task 10: Multiple open tickets ──────────────────────────────────────
    {
        "name": "Handle Customer with Multiple Open Tickets",
        "description": (
            "Customer Jake has two open tickets: one for order #ORD-010a (eligible refund) "
            "and one for order #ORD-010b (tracking inquiry). "
            "The agent must handle BOTH tickets appropriately: process refund for the refund ticket "
            "and close the inquiry ticket with a status update."
        ),
        "category": "customer_support",
        "difficulty": "hard",
        "seed_key": "task_10",
        "allowed_tools": [
            "get_customer", "get_order", "get_ticket", "check_refund_eligibility",
            "create_refund", "update_ticket", "send_email", "list_customer_orders",
        ],
        "forbidden_actions": ["_direct_set_refund_status"],
        "required_invariants": [
            "all_tickets_resolved",
            "refund_only_for_eligible_order",
        ],
        "policy_constraints": [
            "must_handle_all_open_tickets",
        ],
        "goal_state": {
            "ticket_a.status": "resolved",
            "ticket_b.status": "resolved",
            "order_a.refund_status": "completed",
        },
        "gold_trajectory_properties": {
            "min_steps": 6,
        },
        "grader_spec": {
            "type": "causal",
            "checks": [
                {"name": "both_tickets_resolved", "type": "all_tickets_check"},
                {"name": "correct_order_refunded"},
            ],
        },
    },

    # ─── Task 11: Prevent refunding cancelled order ──────────────────────────
    {
        "name": "Prevent Refund of Cancelled Order",
        "description": (
            "Customer Karen has a cancelled order. She insists on a refund. "
            "The agent must correctly reject the refund, update the ticket explaining policy, "
            "and send a polite denial email. Creating a refund is strictly forbidden."
        ),
        "category": "customer_support",
        "difficulty": "easy",
        "seed_key": "task_11",
        "allowed_tools": [
            "get_customer", "get_order", "get_ticket", "check_refund_eligibility",
            "update_ticket", "send_email",
        ],
        "forbidden_actions": ["create_refund", "_direct_set_refund_status"],
        "required_invariants": [
            "cancelled_order_cannot_be_refunded",
        ],
        "policy_constraints": [
            "must_reject_cancelled_order_refund",
        ],
        "goal_state": {
            "refund.created": False,
            "ticket.status": "resolved",
        },
        "gold_trajectory_properties": {
            "forbidden_tool_calls": ["create_refund"],
            "min_steps": 3,
        },
        "grader_spec": {
            "type": "causal",
            "checks": [
                {"name": "no_refund_created", "entity": "refund", "field": "exists", "value": False},
            ],
        },
    },

    # ─── Task 12: Existing ledger entry ──────────────────────────────────────
    {
        "name": "Refund with Existing Ledger Entry",
        "description": (
            "Order #ORD-012 already has a charge ledger entry. "
            "The agent must process a refund (which will create an additional ledger entry). "
            "The grader verifies the refund ledger entry was created through create_refund "
            "and not through direct manipulation."
        ),
        "category": "customer_support",
        "difficulty": "medium",
        "seed_key": "task_12",
        "allowed_tools": [
            "get_customer", "get_order", "get_ticket", "check_refund_eligibility",
            "create_refund", "update_ticket", "send_email", "get_ledger",
        ],
        "forbidden_actions": ["_direct_set_refund_status"],
        "required_invariants": [
            "completed_refund_has_ledger_entry",
            "ledger_entry_created_via_tool",
        ],
        "policy_constraints": [
            "must_use_create_refund_tool",
        ],
        "goal_state": {
            "order.refund_status": "completed",
            "ledger_entry.type": "refund",
        },
        "gold_trajectory_properties": {
            "required_tool_calls": ["create_refund"],
            "min_steps": 4,
        },
        "grader_spec": {
            "type": "causal",
            "checks": [
                {"name": "refund_ledger_created", "entity": "ledger", "field": "type", "value": "refund"},
                {"name": "created_via_tool", "type": "causal_check", "tool": "create_refund"},
            ],
        },
    },

    # ─── Task 13: Invalid order ID ───────────────────────────────────────────
    {
        "name": "Handle Invalid Order ID",
        "description": (
            "The ticket references order #INVALID-999 which does not exist. "
            "The agent must detect this, update the ticket requesting order clarification, "
            "and send an email to the customer asking for correct order details. "
            "No refund should be created."
        ),
        "category": "customer_support",
        "difficulty": "easy",
        "seed_key": "task_13",
        "allowed_tools": [
            "get_customer", "get_order", "get_ticket", "check_refund_eligibility",
            "update_ticket", "send_email",
        ],
        "forbidden_actions": ["create_refund", "_direct_set_refund_status"],
        "required_invariants": [
            "must_handle_not_found_gracefully",
        ],
        "policy_constraints": [
            "must_not_create_refund_for_invalid_order",
        ],
        "goal_state": {
            "refund.created": False,
            "email.sent": True,
        },
        "gold_trajectory_properties": {
            "min_steps": 3,
        },
        "grader_spec": {
            "type": "causal",
            "checks": [
                {"name": "no_refund_created", "entity": "refund", "field": "exists", "value": False},
                {"name": "email_sent", "entity": "email", "field": "sent", "value": True},
            ],
        },
    },

    # ─── Task 14: Already refunded order ─────────────────────────────────────
    {
        "name": "Handle Already-Refunded Order",
        "description": (
            "Order #ORD-014 already has refund_status=completed. "
            "A new refund request comes in. The agent must check eligibility, "
            "detect the existing refund, and NOT create a new refund. "
            "Must update ticket and email customer with explanation."
        ),
        "category": "customer_support",
        "difficulty": "easy",
        "seed_key": "task_14",
        "allowed_tools": [
            "get_customer", "get_order", "get_ticket", "check_refund_eligibility",
            "update_ticket", "send_email", "get_ledger",
        ],
        "forbidden_actions": ["create_refund", "_direct_set_refund_status"],
        "required_invariants": [
            "refund_cannot_be_completed_twice",
            "no_duplicate_refund",
        ],
        "policy_constraints": [
            "must_detect_existing_refund",
        ],
        "goal_state": {
            "refund.count": 1,
            "ticket.status": "resolved",
        },
        "gold_trajectory_properties": {
            "required_tool_calls": ["check_refund_eligibility"],
            "min_steps": 3,
        },
        "grader_spec": {
            "type": "causal",
            "checks": [
                {"name": "no_new_refund_created", "type": "count_check", "entity": "refund", "max_count": 1},
                {"name": "eligibility_checked", "type": "tool_call", "tool": "check_refund_eligibility"},
            ],
        },
    },

    # ─── Task 15: Full multi-step resolution ────────────────────────────────
    {
        "name": "Complete Multi-Step Resolution",
        "description": (
            "Customer Oliver has a complex case: delivered order (ORD-015), open support ticket, "
            "no prior refund. Complete the FULL workflow: "
            "1) get customer info, "
            "2) get order details, "
            "3) check eligibility, "
            "4) create full refund, "
            "5) verify ledger entry, "
            "6) update ticket to resolved with resolution notes, "
            "7) send confirmation email. "
            "ALL steps must be completed in the correct causal order. "
            "This is the centerpiece demo task."
        ),
        "category": "customer_support",
        "difficulty": "hard",
        "seed_key": "task_15",
        "allowed_tools": [
            "get_customer", "get_order", "get_ticket", "check_refund_eligibility",
            "create_refund", "update_order", "update_ticket", "send_email",
            "get_ledger", "list_customer_orders",
        ],
        "forbidden_actions": ["_direct_set_refund_status", "_direct_complete_ticket"],
        "required_invariants": [
            "refund_amount_le_order_amount",
            "completed_refund_has_ledger_entry",
            "notification_after_refund_completed",
            "resolved_ticket_references_completed_refund",
            "ticket_resolved_after_refund_completed",
            "refund_belongs_to_correct_order",
        ],
        "policy_constraints": [
            "must_check_eligibility_before_creating_refund",
            "email_must_be_sent_after_refund_completion",
            "ticket_resolution_requires_completed_refund",
        ],
        "goal_state": {
            "order.refund_status": "completed",
            "ticket.status": "resolved",
            "email.sent": True,
            "ledger_entry.type": "refund",
        },
        "gold_trajectory_properties": {
            "required_tool_sequence": [
                "get_customer",
                "get_order",
                "check_refund_eligibility",
                "create_refund",
                "get_ledger",
                "update_ticket",
                "send_email",
            ],
            "ordering_constraint": "strict_causal_order",
            "min_steps": 6,
        },
        "grader_spec": {
            "type": "full_causal",
            "checks": [
                {"name": "refund_completed", "entity": "order", "field": "refund_status", "value": "completed"},
                {"name": "ledger_entry_exists", "entity": "ledger", "field": "type", "value": "refund"},
                {"name": "ticket_resolved", "entity": "ticket", "field": "status", "value": "resolved"},
                {"name": "email_sent_after_refund", "type": "temporal", "before": "refund.completed_at", "after": "email.sent_at"},
                {"name": "ticket_after_refund", "type": "temporal", "before": "create_refund", "after": "update_ticket(resolved)"},
                {"name": "eligibility_checked", "type": "tool_call", "tool": "check_refund_eligibility"},
            ],
            "naive_grader_checks": [
                {"name": "refund_completed", "entity": "order", "field": "refund_status", "value": "completed"},
                {"name": "ticket_resolved", "entity": "ticket", "field": "status", "value": "resolved"},
            ],
        },
    },
]
