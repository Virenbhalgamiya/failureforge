"""Pydantic schemas for API request/response validation."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional
from pydantic import BaseModel, Field, ConfigDict

from failureforge.models import (
    TaskCategory,
    RunStatus,
    Verdict,
    FailureType,
    ReviewStatus,
    AttackType,
    CustomerStatus,
    OrderStatus,
    DeliveryStatus,
    RefundStatus,
    TicketStatus,
    LedgerEntryType,
)


# ─── Task Schemas ─────────────────────────────────────────────────────────────


class TaskCreate(BaseModel):
    name: str
    description: str
    category: TaskCategory = TaskCategory.CUSTOMER_SUPPORT
    initial_state: dict[str, Any] = Field(default_factory=dict)
    goal_state: dict[str, Any] = Field(default_factory=dict)
    allowed_tools: list[str] = Field(default_factory=list)
    policy_constraints: list[str] = Field(default_factory=list)
    required_invariants: list[str] = Field(default_factory=list)
    forbidden_actions: list[str] = Field(default_factory=list)
    difficulty: str = "medium"
    gold_trajectory_properties: dict[str, Any] = Field(default_factory=dict)
    grader_spec: dict[str, Any] = Field(default_factory=dict)


class TaskOut(TaskCreate):
    model_config = ConfigDict(from_attributes=True)

    id: str
    created_at: datetime


# ─── Run Schemas ─────────────────────────────────────────────────────────────


class RunCreate(BaseModel):
    task_id: str
    agent_name: str
    metadata_: dict[str, Any] = Field(default_factory=dict, alias="metadata")

    model_config = ConfigDict(populate_by_name=True)


class RunOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    task_id: str
    agent_name: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    status: RunStatus
    final_state: Optional[dict[str, Any]] = None
    score: Optional[float] = None
    metadata_: dict[str, Any] = Field(default_factory=dict, alias="metadata")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


# ─── Trajectory Schemas ───────────────────────────────────────────────────────


class TrajectoryEventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    run_id: str
    sequence_num: int
    timestamp: datetime
    event_type: str
    tool_name: Optional[str] = None
    arguments: dict[str, Any] = Field(default_factory=dict)
    result: dict[str, Any] = Field(default_factory=dict)
    state_before: dict[str, Any] = Field(default_factory=dict)
    state_after: dict[str, Any] = Field(default_factory=dict)
    is_suspicious: bool = False
    suspicion_reason: Optional[str] = None


class StateTransitionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    event_id: str
    run_id: str
    entity: str
    entity_id: str
    field: str
    before: Optional[str] = None
    after: Optional[str] = None
    source: str
    timestamp: datetime


# ─── Verification Schemas ─────────────────────────────────────────────────────


class VerificationResultOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    run_id: str
    final_state_correct: bool
    causal_path_correct: bool
    policy_compliant: bool
    invariants_satisfied: bool
    reward_hacking_detected: bool
    confidence: float
    final_verdict: Verdict
    naive_verdict: Verdict
    reasons: list[str] = Field(default_factory=list)
    invariant_details: list[dict[str, Any]] = Field(default_factory=list)
    reward_hacking_evidence: list[dict[str, Any]] = Field(default_factory=list)
    created_at: datetime


# ─── Failure Schemas ──────────────────────────────────────────────────────────


class FailureOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    run_id: str
    failure_type: FailureType
    description: str
    evidence: dict[str, Any] = Field(default_factory=dict)
    severity: str
    failure_pattern: Optional[str] = None
    root_cause: Optional[str] = None
    cluster_id: Optional[str] = None
    created_at: datetime


# ─── Benchmark Schemas ────────────────────────────────────────────────────────


class BenchmarkCandidateOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    source_failure_id: str
    generated_task: dict[str, Any]
    generated_invariants: list[str]
    generated_grader: dict[str, Any]
    known_failure_mode: str
    review_status: ReviewStatus
    review_notes: Optional[str] = None
    created_at: datetime


class GraderAttackOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    benchmark_id: str
    attack_type: AttackType
    trajectory: list[dict[str, Any]]
    expected_verdict: Verdict
    actual_verdict: Verdict
    grader_bypassed: bool
    evidence: dict[str, Any]
    created_at: datetime


class GraderReportOut(BaseModel):
    benchmark_id: str
    total_attacks: int
    true_positives: int
    true_negatives: int
    false_positives: int
    false_negatives: int
    precision: float
    recall: float
    f1: float
    reward_hacking_resistance: float
    attacks: list[GraderAttackOut]


# ─── Overview Schema ──────────────────────────────────────────────────────────


class OverviewOut(BaseModel):
    total_tasks: int
    total_runs: int
    pass_count: int
    fail_count: int
    suspicious_count: int
    pass_rate: float
    fail_rate: float
    suspicious_rate: float
    reward_hacking_incidents: int
    grader_false_positives: int
    total_failures: int
    total_benchmarks: int


# ─── Cluster Schema ───────────────────────────────────────────────────────────


class FailureClusterOut(BaseModel):
    cluster_id: str
    failure_type: str
    count: int
    severity: str
    run_ids: list[str]
    representative_description: str


# ─── Environment Entity Schemas ───────────────────────────────────────────────


class CustomerOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    email: str
    status: CustomerStatus
    created_at: datetime


class OrderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    customer_id: str
    product: str
    price: float
    status: OrderStatus
    delivery_status: DeliveryStatus
    refund_status: RefundStatus
    created_at: datetime


class RefundOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    order_id: str
    amount: float
    status: RefundStatus
    created_at: datetime
    completed_at: Optional[datetime] = None


class SupportTicketOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    customer_id: str
    order_id: Optional[str] = None
    status: TicketStatus
    resolution: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime
    resolved_at: Optional[datetime] = None
