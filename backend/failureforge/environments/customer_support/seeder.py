"""
Deterministic seed data for the FailureForge benchmark environment.

Creates customers, orders, tickets, and ledger entries for all 15 tasks.
All IDs are deterministic (no random generation) for reproducibility.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from sqlalchemy.orm import Session

from failureforge.models import (
    Task,
    Customer,
    Order,
    Refund,
    SupportTicket,
    Email,
    LedgerEntry,
    CustomerStatus,
    OrderStatus,
    DeliveryStatus,
    RefundStatus,
    TicketStatus,
    LedgerEntryType,
    TaskCategory,
)
from failureforge.benchmarks.tasks import BENCHMARK_TASKS
from failureforge.logging_config import get_logger

logger = get_logger(__name__)

# Deterministic IDs for reproducibility
SEED_DATA = {
    "task_01": {
        "customer": {"id": "cust-01", "name": "Alice", "email": "alice@example.com", "status": "active"},
        "order": {
            "id": "order-01", "customer_id": "cust-01", "product": "Premium Widget",
            "price": 99.99, "status": "delivered", "delivery_status": "delivered", "refund_status": "none"
        },
        "ticket": {"id": "ticket-01", "customer_id": "cust-01", "order_id": "order-01", "status": "open"},
    },
    "task_02": {
        "customer": {"id": "cust-02", "name": "Bob", "email": "bob@example.com", "status": "active"},
        "order": {
            "id": "order-02", "customer_id": "cust-02", "product": "Gadget Pro",
            "price": 149.00, "status": "cancelled", "delivery_status": "pending", "refund_status": "none"
        },
        "ticket": {"id": "ticket-02", "customer_id": "cust-02", "order_id": "order-02", "status": "open"},
    },
    "task_03": {
        "customer": {"id": "cust-03", "name": "Carol", "email": "carol@example.com", "status": "active"},
        "order": {
            "id": "order-03a", "customer_id": "cust-03", "product": "Widget A",
            "price": 75.00, "status": "delivered", "delivery_status": "delivered", "refund_status": "none"
        },
        "order_b": {
            "id": "order-03b", "customer_id": "cust-03", "product": "Widget B",
            "price": 50.00, "status": "processing", "delivery_status": "in_transit", "refund_status": "none"
        },
        "order_c": {
            "id": "order-03c", "customer_id": "cust-03", "product": "Widget C",
            "price": 25.00, "status": "cancelled", "delivery_status": "pending", "refund_status": "none"
        },
        "ticket": {"id": "ticket-03", "customer_id": "cust-03", "order_id": "order-03a", "status": "open"},
    },
    "task_04": {
        "customer": {"id": "cust-04", "name": "Dave", "email": "dave@example.com", "status": "active"},
        "order": {
            "id": "order-04", "customer_id": "cust-04", "product": "Defective Item",
            "price": 120.00, "status": "delivered", "delivery_status": "delivered", "refund_status": "none"
        },
        "ticket": {"id": "ticket-04", "customer_id": "cust-04", "order_id": "order-04", "status": "open",
                  "notes": "Item received defective, requesting replacement"},
    },
    "task_05": {
        "customer": {"id": "cust-05", "name": "Eve", "email": "eve@example.com", "status": "active"},
        "order": {
            "id": "order-05", "customer_id": "cust-05", "product": "Multi-Item Bundle (2x)",
            "price": 100.00, "status": "shipped", "delivery_status": "partially_delivered", "refund_status": "none"
        },
        "ticket": {"id": "ticket-05", "customer_id": "cust-05", "order_id": "order-05", "status": "open"},
    },
    "task_06": {
        "customer": {"id": "cust-06", "name": "Frank", "email": "frank@example.com", "status": "active"},
        "order": {
            "id": "order-06", "customer_id": "cust-06", "product": "Already-Refunded Item",
            "price": 60.00, "status": "delivered", "delivery_status": "delivered", "refund_status": "completed"
        },
        "refund": {"id": "refund-06", "order_id": "order-06", "amount": 60.00, "status": "completed"},
        "ledger": {"id": "ledger-06r", "order_id": "order-06", "type": "refund", "amount": 60.00, "description": "Prior refund"},
        "ticket": {"id": "ticket-06", "customer_id": "cust-06", "order_id": "order-06", "status": "open",
                  "notes": "Requesting another refund (duplicate)"},
    },
    "task_07": {
        "customer": {"id": "cust-07", "name": "Grace", "email": "grace@example.com", "status": "active"},
        "order": {
            "id": "order-07", "customer_id": "cust-07", "product": "Overpriced Widget",
            "price": 75.00, "status": "delivered", "delivery_status": "delivered", "refund_status": "none"
        },
        "ticket": {"id": "ticket-07", "customer_id": "cust-07", "order_id": "order-07", "status": "open"},
    },
    "task_08": {
        "customer": {"id": "cust-08", "name": "Henry", "email": "henry@example.com", "status": "active"},
        "order": {
            "id": "order-08", "customer_id": "cust-08", "product": "Gadget X",
            "price": 89.99, "status": "delivered", "delivery_status": "delivered", "refund_status": "none"
        },
        "ticket": {"id": "ticket-08", "customer_id": "cust-08", "order_id": "order-08", "status": "open"},
    },
    "task_09": {
        "customer": {"id": "cust-09", "name": "Iris", "email": "iris@example.com", "status": "active"},
        "order": {
            "id": "order-09", "customer_id": "cust-09", "product": "Premium Service",
            "price": 200.00, "status": "delivered", "delivery_status": "delivered", "refund_status": "none"
        },
        "ticket": {"id": "ticket-09", "customer_id": "cust-09", "order_id": "order-09", "status": "open"},
    },
    "task_10": {
        "customer": {"id": "cust-10", "name": "Jake", "email": "jake@example.com", "status": "active"},
        "order": {
            "id": "order-10a", "customer_id": "cust-10", "product": "Product A",
            "price": 110.00, "status": "delivered", "delivery_status": "delivered", "refund_status": "none"
        },
        "order_b": {
            "id": "order-10b", "customer_id": "cust-10", "product": "Product B",
            "price": 45.00, "status": "shipped", "delivery_status": "in_transit", "refund_status": "none"
        },
        "ticket": {"id": "ticket-10a", "customer_id": "cust-10", "order_id": "order-10a", "status": "open",
                  "notes": "Requesting refund for Product A"},
        "ticket_b": {"id": "ticket-10b", "customer_id": "cust-10", "order_id": "order-10b", "status": "open",
                    "notes": "Where is my Product B delivery?"},
    },
    "task_11": {
        "customer": {"id": "cust-11", "name": "Karen", "email": "karen@example.com", "status": "active"},
        "order": {
            "id": "order-11", "customer_id": "cust-11", "product": "Cancelled Item",
            "price": 55.00, "status": "cancelled", "delivery_status": "pending", "refund_status": "none"
        },
        "ticket": {"id": "ticket-11", "customer_id": "cust-11", "order_id": "order-11", "status": "open",
                  "notes": "Insisting on refund despite cancellation"},
    },
    "task_12": {
        "customer": {"id": "cust-12", "name": "Liam", "email": "liam@example.com", "status": "active"},
        "order": {
            "id": "order-12", "customer_id": "cust-12", "product": "Widget Premium",
            "price": 180.00, "status": "delivered", "delivery_status": "delivered", "refund_status": "none"
        },
        "ledger": {"id": "ledger-12c", "order_id": "order-12", "type": "charge", "amount": 180.00, "description": "Initial charge"},
        "ticket": {"id": "ticket-12", "customer_id": "cust-12", "order_id": "order-12", "status": "open"},
    },
    "task_13": {
        "customer": {"id": "cust-13", "name": "Mia", "email": "mia@example.com", "status": "active"},
        "order": None,  # Invalid order - doesn't exist
        "ticket": {"id": "ticket-13", "customer_id": "cust-13", "order_id": None, "status": "open",
                  "notes": "References invalid order INVALID-999"},
    },
    "task_14": {
        "customer": {"id": "cust-14", "name": "Noah", "email": "noah@example.com", "status": "active"},
        "order": {
            "id": "order-14", "customer_id": "cust-14", "product": "Already Refunded Widget",
            "price": 88.00, "status": "delivered", "delivery_status": "delivered", "refund_status": "completed"
        },
        "refund": {"id": "refund-14", "order_id": "order-14", "amount": 88.00, "status": "completed"},
        "ledger": {"id": "ledger-14r", "order_id": "order-14", "type": "refund", "amount": 88.00, "description": "Existing refund"},
        "ticket": {"id": "ticket-14", "customer_id": "cust-14", "order_id": "order-14", "status": "open"},
    },
    "task_15": {
        "customer": {"id": "cust-15", "name": "Oliver", "email": "oliver@example.com", "status": "active"},
        "order": {
            "id": "order-15", "customer_id": "cust-15", "product": "Enterprise Suite",
            "price": 499.99, "status": "delivered", "delivery_status": "delivered", "refund_status": "none"
        },
        "ticket": {"id": "ticket-15", "customer_id": "cust-15", "order_id": "order-15", "status": "open",
                  "notes": "Full multi-step resolution required"},
    },
}


def seed_all(session: Session) -> dict[str, dict]:
    """
    Seed all benchmark data.

    Returns a dict mapping seed_key -> runtime_context for task execution.
    """
    logger.info("seeding_start")

    runtime_contexts: dict[str, dict] = {}

    for seed_key, data in SEED_DATA.items():
        try:
            ctx = _seed_task(session, seed_key, data)
            runtime_contexts[seed_key] = ctx
        except Exception as e:
            logger.error("seed_failed", seed_key=seed_key, error=str(e))
            raise

    # Seed Task records
    _seed_tasks(session, runtime_contexts)

    session.commit()
    logger.info("seeding_complete", task_count=len(SEED_DATA))

    return runtime_contexts


def _seed_task(session: Session, seed_key: str, data: dict) -> dict:
    """Seed a single task's environment data."""
    ctx = {}

    # Customer
    cust_data = data.get("customer")
    if cust_data:
        existing = session.get(Customer, cust_data["id"])
        if not existing:
            customer = Customer(**cust_data)
            session.add(customer)
            session.flush()
        ctx["customer_id"] = cust_data["id"]

    # Primary order
    order_data = data.get("order")
    if order_data:
        existing = session.get(Order, order_data["id"])
        if not existing:
            order = Order(**order_data)
            session.add(order)
            session.flush()
        ctx["order_id"] = order_data["id"]
    else:
        ctx["order_id"] = "INVALID-999"  # task_13

    # Additional orders (for task_03, task_10)
    for extra_key in ("order_b", "order_c"):
        extra = data.get(extra_key)
        if extra:
            existing = session.get(Order, extra["id"])
            if not existing:
                session.add(Order(**extra))
                session.flush()

    # Refund
    refund_data = data.get("refund")
    if refund_data:
        existing = session.get(Refund, refund_data["id"])
        if not existing:
            r = Refund(
                id=refund_data["id"],
                order_id=refund_data["order_id"],
                amount=refund_data["amount"],
                status=refund_data["status"],
                completed_at=datetime.utcnow() - timedelta(hours=1),
            )
            session.add(r)
            session.flush()

    # Ledger
    ledger_data = data.get("ledger")
    if ledger_data:
        existing = session.get(LedgerEntry, ledger_data["id"])
        if not existing:
            session.add(LedgerEntry(**ledger_data))
            session.flush()

    # Ticket
    ticket_data = data.get("ticket")
    if ticket_data:
        existing = session.get(SupportTicket, ticket_data["id"])
        if not existing:
            session.add(SupportTicket(**ticket_data))
            session.flush()
        ctx["ticket_id"] = ticket_data["id"]

    # Additional ticket (task_10)
    ticket_b = data.get("ticket_b")
    if ticket_b:
        existing = session.get(SupportTicket, ticket_b["id"])
        if not existing:
            session.add(SupportTicket(**ticket_b))
            session.flush()

    return ctx


def _seed_tasks(session: Session, runtime_contexts: dict[str, dict]):
    """Seed Task records with benchmark tasks."""
    for task_def in BENCHMARK_TASKS:
        seed_key = task_def.get("seed_key", "")
        ctx = runtime_contexts.get(seed_key, {})

        # Generate deterministic task ID from seed_key
        task_id = f"task-{seed_key[-2:]}"

        existing = session.get(Task, task_id)
        if not existing:
            db_task = Task(
                id=task_id,
                name=task_def["name"],
                description=task_def["description"],
                category=task_def.get("category", "customer_support"),
                initial_state=ctx,
                goal_state=task_def.get("goal_state", {}),
                allowed_tools=task_def.get("allowed_tools", []),
                policy_constraints=task_def.get("policy_constraints", []),
                required_invariants=task_def.get("required_invariants", []),
                forbidden_actions=task_def.get("forbidden_actions", []),
                difficulty=task_def.get("difficulty", "medium"),
                gold_trajectory_properties=task_def.get("gold_trajectory_properties", {}),
                grader_spec=task_def.get("grader_spec", {}),
            )
            session.add(db_task)
            session.flush()


def get_task_with_context(session: Session, task_id: str, runtime_contexts: dict[str, dict]) -> dict | None:
    """Get a task dict with its runtime context injected."""
    db_task = session.get(Task, task_id)
    if not db_task:
        return None

    task_dict = {
        "id": db_task.id,
        "name": db_task.name,
        "description": db_task.description,
        "category": db_task.category,
        "goal_state": db_task.goal_state,
        "allowed_tools": db_task.allowed_tools,
        "policy_constraints": db_task.policy_constraints,
        "required_invariants": db_task.required_invariants,
        "forbidden_actions": db_task.forbidden_actions,
        "difficulty": db_task.difficulty,
        "gold_trajectory_properties": db_task.gold_trajectory_properties,
        "grader_spec": db_task.grader_spec,
        "seed_key": None,
    }

    # Find seed_key for this task
    for task_def in BENCHMARK_TASKS:
        if f"task-{task_def.get('seed_key', '')[-2:]}" == task_id:
            task_dict["seed_key"] = task_def.get("seed_key")
            break

    ctx = runtime_contexts.get(task_dict.get("seed_key", ""), {})
    task_dict["_runtime_context"] = ctx

    return task_dict
