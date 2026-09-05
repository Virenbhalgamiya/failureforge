"""SQLAlchemy ORM models for FailureForge core domain."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    JSON,
    Enum as SAEnum,
)
from sqlalchemy.orm import DeclarativeBase, relationship
import enum


class Base(DeclarativeBase):
    __allow_unmapped__ = True



def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.utcnow()


# ─── Enums ──────────────────────────────────────────────────────────────────


class TaskCategory(str, enum.Enum):
    CUSTOMER_SUPPORT = "customer_support"
    CODING = "coding"
    REASONING = "reasoning"
    TOOL_USE = "tool_use"


class RunStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    ERROR = "error"


class Verdict(str, enum.Enum):
    PASS = "pass"
    FAIL = "fail"
    SUSPICIOUS = "suspicious"
    PENDING = "pending"


class FailureType(str, enum.Enum):
    PREMATURE_CONFIRMATION = "premature_confirmation"
    WRONG_ENTITY = "wrong_entity"
    DUPLICATE_SIDE_EFFECT = "duplicate_side_effect"
    DIRECT_STATE_MANIPULATION = "direct_state_manipulation"
    TOOL_ORDER_BYPASS = "tool_order_bypass"
    IMPOSSIBLE_TRANSITION = "impossible_transition"
    INVARIANT_VIOLATION = "invariant_violation"
    POLICY_VIOLATION = "policy_violation"
    GRADER_TARGETED_MANIPULATION = "grader_targeted_manipulation"
    MISSING_PREREQUISITE = "missing_prerequisite"
    INCORRECT_OUTCOME = "incorrect_outcome"
    UNKNOWN = "unknown"


class ReviewStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    NEEDS_REVISION = "needs_revision"


class AttackType(str, enum.Enum):
    FINAL_STATE_SPOOFING = "final_state_spoofing"
    DATABASE_MANIPULATION = "database_manipulation"
    WRONG_ENTITY_SUBSTITUTION = "wrong_entity_substitution"
    SKIPPED_PREREQUISITE = "skipped_prerequisite"
    PREMATURE_SIDE_EFFECT = "premature_side_effect"
    DUPLICATE_SIDE_EFFECT = "duplicate_side_effect"
    INCONSISTENT_INTERMEDIATE_STATE = "inconsistent_intermediate_state"
    GRADER_TARGETED_MUTATION = "grader_targeted_mutation"


# ─── Core Domain Models ──────────────────────────────────────────────────────


class Task(Base):
    __tablename__ = "tasks"

    id: str = Column(String(36), primary_key=True, default=_uuid)
    name: str = Column(String(255), nullable=False, index=True)
    description: str = Column(Text, nullable=False)
    category: str = Column(SAEnum(TaskCategory), nullable=False, default=TaskCategory.CUSTOMER_SUPPORT)
    initial_state: dict = Column(JSON, nullable=False, default=dict)
    goal_state: dict = Column(JSON, nullable=False, default=dict)
    allowed_tools: list = Column(JSON, nullable=False, default=list)
    policy_constraints: list = Column(JSON, nullable=False, default=list)
    required_invariants: list = Column(JSON, nullable=False, default=list)
    forbidden_actions: list = Column(JSON, nullable=False, default=list)
    difficulty: str = Column(String(20), nullable=False, default="medium")
    gold_trajectory_properties: dict = Column(JSON, nullable=False, default=dict)
    grader_spec: dict = Column(JSON, nullable=False, default=dict)
    created_at: datetime = Column(DateTime, default=_now)

    runs: list["AgentRun"] = relationship("AgentRun", back_populates="task")


class AgentRun(Base):
    __tablename__ = "agent_runs"

    id: str = Column(String(36), primary_key=True, default=_uuid)
    task_id: str = Column(String(36), ForeignKey("tasks.id"), nullable=False, index=True)
    agent_name: str = Column(String(100), nullable=False)
    started_at: datetime = Column(DateTime, default=_now)
    completed_at: Optional[datetime] = Column(DateTime, nullable=True)
    status: str = Column(SAEnum(RunStatus), nullable=False, default=RunStatus.PENDING)
    final_state: dict = Column(JSON, nullable=True, default=dict)
    score: Optional[float] = Column(Float, nullable=True)
    metadata_: dict = Column("metadata", JSON, nullable=False, default=dict)

    task: Task = relationship("Task", back_populates="runs")
    events: list["TrajectoryEvent"] = relationship("TrajectoryEvent", back_populates="run")
    verification: Optional["VerificationResult"] = relationship(
        "VerificationResult", back_populates="run", uselist=False
    )
    failures: list["Failure"] = relationship("Failure", back_populates="run")


class TrajectoryEvent(Base):
    __tablename__ = "trajectory_events"

    id: str = Column(String(36), primary_key=True, default=_uuid)
    run_id: str = Column(String(36), ForeignKey("agent_runs.id"), nullable=False, index=True)
    sequence_num: int = Column(Integer, nullable=False, default=0)
    timestamp: datetime = Column(DateTime, default=_now)
    event_type: str = Column(String(50), nullable=False)
    tool_name: Optional[str] = Column(String(100), nullable=True)
    arguments: dict = Column(JSON, nullable=False, default=dict)
    result: dict = Column(JSON, nullable=True, default=dict)
    state_before: dict = Column(JSON, nullable=True, default=dict)
    state_after: dict = Column(JSON, nullable=True, default=dict)
    is_suspicious: bool = Column(Boolean, default=False)
    suspicion_reason: Optional[str] = Column(Text, nullable=True)

    run: AgentRun = relationship("AgentRun", back_populates="events")
    transitions: list["StateTransition"] = relationship("StateTransition", back_populates="event")


class StateTransition(Base):
    __tablename__ = "state_transitions"

    id: str = Column(String(36), primary_key=True, default=_uuid)
    event_id: str = Column(String(36), ForeignKey("trajectory_events.id"), nullable=False, index=True)
    run_id: str = Column(String(36), nullable=False, index=True)
    entity: str = Column(String(100), nullable=False)
    entity_id: str = Column(String(100), nullable=False)
    field: str = Column(String(100), nullable=False)
    before: Optional[str] = Column(Text, nullable=True)
    after: Optional[str] = Column(Text, nullable=True)
    source: str = Column(String(50), nullable=False, default="tool_call")
    timestamp: datetime = Column(DateTime, default=_now)

    event: TrajectoryEvent = relationship("TrajectoryEvent", back_populates="transitions")


class VerificationResult(Base):
    __tablename__ = "verification_results"

    id: str = Column(String(36), primary_key=True, default=_uuid)
    run_id: str = Column(String(36), ForeignKey("agent_runs.id"), nullable=False, unique=True)
    final_state_correct: bool = Column(Boolean, nullable=False, default=False)
    causal_path_correct: bool = Column(Boolean, nullable=False, default=False)
    policy_compliant: bool = Column(Boolean, nullable=False, default=False)
    invariants_satisfied: bool = Column(Boolean, nullable=False, default=False)
    reward_hacking_detected: bool = Column(Boolean, nullable=False, default=False)
    confidence: float = Column(Float, nullable=False, default=0.0)
    final_verdict: str = Column(SAEnum(Verdict), nullable=False, default=Verdict.PENDING)
    reasons: list = Column(JSON, nullable=False, default=list)
    invariant_details: list = Column(JSON, nullable=False, default=list)
    reward_hacking_evidence: list = Column(JSON, nullable=False, default=list)
    naive_verdict: str = Column(SAEnum(Verdict), nullable=False, default=Verdict.PENDING)
    created_at: datetime = Column(DateTime, default=_now)

    run: AgentRun = relationship("AgentRun", back_populates="verification")


class Failure(Base):
    __tablename__ = "failures"

    id: str = Column(String(36), primary_key=True, default=_uuid)
    run_id: str = Column(String(36), ForeignKey("agent_runs.id"), nullable=False, index=True)
    failure_type: str = Column(SAEnum(FailureType), nullable=False)
    description: str = Column(Text, nullable=False)
    evidence: dict = Column(JSON, nullable=False, default=dict)
    severity: str = Column(String(20), nullable=False, default="medium")
    failure_pattern: Optional[str] = Column(Text, nullable=True)
    root_cause: Optional[str] = Column(Text, nullable=True)
    cluster_id: Optional[str] = Column(String(36), nullable=True, index=True)
    created_at: datetime = Column(DateTime, default=_now)

    run: AgentRun = relationship("AgentRun", back_populates="failures")
    benchmark_candidate: Optional["BenchmarkCandidate"] = relationship(
        "BenchmarkCandidate", back_populates="source_failure", uselist=False
    )


class BenchmarkCandidate(Base):
    __tablename__ = "benchmark_candidates"

    id: str = Column(String(36), primary_key=True, default=_uuid)
    source_failure_id: str = Column(String(36), ForeignKey("failures.id"), nullable=False, unique=True)
    generated_task: dict = Column(JSON, nullable=False, default=dict)
    generated_invariants: list = Column(JSON, nullable=False, default=list)
    generated_grader: dict = Column(JSON, nullable=False, default=dict)
    known_failure_mode: str = Column(Text, nullable=False)
    review_status: str = Column(SAEnum(ReviewStatus), nullable=False, default=ReviewStatus.PENDING)
    review_notes: Optional[str] = Column(Text, nullable=True)
    created_at: datetime = Column(DateTime, default=_now)

    source_failure: Failure = relationship("Failure", back_populates="benchmark_candidate")
    grader_attacks: list["GraderAttack"] = relationship("GraderAttack", back_populates="benchmark")


class GraderAttack(Base):
    __tablename__ = "grader_attacks"

    id: str = Column(String(36), primary_key=True, default=_uuid)
    benchmark_id: str = Column(String(36), ForeignKey("benchmark_candidates.id"), nullable=False, index=True)
    attack_type: str = Column(SAEnum(AttackType), nullable=False)
    trajectory: list = Column(JSON, nullable=False, default=list)
    expected_verdict: str = Column(SAEnum(Verdict), nullable=False)
    actual_verdict: str = Column(SAEnum(Verdict), nullable=False)
    grader_bypassed: bool = Column(Boolean, nullable=False, default=False)
    evidence: dict = Column(JSON, nullable=False, default=dict)
    created_at: datetime = Column(DateTime, default=_now)

    benchmark: BenchmarkCandidate = relationship("BenchmarkCandidate", back_populates="grader_attacks")


# ─── Environment-specific models (Customer Support) ─────────────────────────


class CustomerStatus(str, enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    BLOCKED = "blocked"


class OrderStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"
    RETURNED = "returned"


class DeliveryStatus(str, enum.Enum):
    PENDING = "pending"
    IN_TRANSIT = "in_transit"
    DELIVERED = "delivered"
    FAILED = "failed"
    PARTIALLY_DELIVERED = "partially_delivered"


class RefundStatus(str, enum.Enum):
    NONE = "none"
    REQUESTED = "requested"
    PROCESSING = "processing"
    COMPLETED = "completed"
    REJECTED = "rejected"


class TicketStatus(str, enum.Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    CLOSED = "closed"


class LedgerEntryType(str, enum.Enum):
    CHARGE = "charge"
    REFUND = "refund"
    ADJUSTMENT = "adjustment"


class Customer(Base):
    __tablename__ = "cs_customers"

    id: str = Column(String(36), primary_key=True, default=_uuid)
    name: str = Column(String(255), nullable=False)
    email: str = Column(String(255), nullable=False, unique=True, index=True)
    status: str = Column(SAEnum(CustomerStatus), nullable=False, default=CustomerStatus.ACTIVE)
    created_at: datetime = Column(DateTime, default=_now)

    orders: list["Order"] = relationship("Order", back_populates="customer")
    tickets: list["SupportTicket"] = relationship("SupportTicket", back_populates="customer")
    emails: list["Email"] = relationship("Email", back_populates="customer")


class Order(Base):
    __tablename__ = "cs_orders"

    id: str = Column(String(36), primary_key=True, default=_uuid)
    customer_id: str = Column(String(36), ForeignKey("cs_customers.id"), nullable=False, index=True)
    product: str = Column(String(255), nullable=False)
    price: float = Column(Float, nullable=False)
    status: str = Column(SAEnum(OrderStatus), nullable=False, default=OrderStatus.PENDING)
    delivery_status: str = Column(SAEnum(DeliveryStatus), nullable=False, default=DeliveryStatus.PENDING)
    refund_status: str = Column(SAEnum(RefundStatus), nullable=False, default=RefundStatus.NONE)
    created_at: datetime = Column(DateTime, default=_now)

    customer: Customer = relationship("Customer", back_populates="orders")
    refunds: list["Refund"] = relationship("Refund", back_populates="order")
    tickets: list["SupportTicket"] = relationship("SupportTicket", back_populates="order")
    ledger_entries: list["LedgerEntry"] = relationship("LedgerEntry", back_populates="order")


class Refund(Base):
    __tablename__ = "cs_refunds"

    id: str = Column(String(36), primary_key=True, default=_uuid)
    order_id: str = Column(String(36), ForeignKey("cs_orders.id"), nullable=False, index=True)
    amount: float = Column(Float, nullable=False)
    status: str = Column(SAEnum(RefundStatus), nullable=False, default=RefundStatus.REQUESTED)
    created_at: datetime = Column(DateTime, default=_now)
    completed_at: Optional[datetime] = Column(DateTime, nullable=True)

    order: Order = relationship("Order", back_populates="refunds")


class SupportTicket(Base):
    __tablename__ = "cs_tickets"

    id: str = Column(String(36), primary_key=True, default=_uuid)
    customer_id: str = Column(String(36), ForeignKey("cs_customers.id"), nullable=False, index=True)
    order_id: Optional[str] = Column(String(36), ForeignKey("cs_orders.id"), nullable=True, index=True)
    status: str = Column(SAEnum(TicketStatus), nullable=False, default=TicketStatus.OPEN)
    resolution: Optional[str] = Column(Text, nullable=True)
    notes: Optional[str] = Column(Text, nullable=True)
    created_at: datetime = Column(DateTime, default=_now)
    resolved_at: Optional[datetime] = Column(DateTime, nullable=True)

    customer: Customer = relationship("Customer", back_populates="tickets")
    order: Optional[Order] = relationship("Order", back_populates="tickets")


class Email(Base):
    __tablename__ = "cs_emails"

    id: str = Column(String(36), primary_key=True, default=_uuid)
    customer_id: str = Column(String(36), ForeignKey("cs_customers.id"), nullable=False, index=True)
    subject: str = Column(String(500), nullable=False)
    body: str = Column(Text, nullable=False)
    sent_at: Optional[datetime] = Column(DateTime, nullable=True)
    created_at: datetime = Column(DateTime, default=_now)

    customer: Customer = relationship("Customer", back_populates="emails")


class LedgerEntry(Base):
    __tablename__ = "cs_ledger_entries"

    id: str = Column(String(36), primary_key=True, default=_uuid)
    order_id: str = Column(String(36), ForeignKey("cs_orders.id"), nullable=False, index=True)
    type: str = Column(SAEnum(LedgerEntryType), nullable=False)
    amount: float = Column(Float, nullable=False)
    description: str = Column(String(500), nullable=False, default="")
    created_at: datetime = Column(DateTime, default=_now)

    order: Order = relationship("Order", back_populates="ledger_entries")
