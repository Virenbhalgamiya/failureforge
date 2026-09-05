"""Runs API endpoints."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from failureforge.database import get_db
from failureforge.models import AgentRun, TrajectoryEvent, VerificationResult, Failure, RunStatus
from failureforge.schemas import RunCreate, RunOut, TrajectoryEventOut, VerificationResultOut, FailureOut, OverviewOut

router = APIRouter(tags=["runs"])


@router.get("", response_model=list[RunOut])
async def list_runs(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(AgentRun).order_by(AgentRun.started_at.desc()))
    return result.scalars().all()


@router.get("/overview", response_model=OverviewOut)
async def get_overview(db: AsyncSession = Depends(get_db)):
    from failureforge.models import Task, BenchmarkCandidate, GraderAttack, Verdict
    from sqlalchemy import func

    runs_result = await db.execute(select(AgentRun))
    runs = runs_result.scalars().all()

    tasks_result = await db.execute(select(Task))
    total_tasks = len(tasks_result.scalars().all())

    verifs_result = await db.execute(select(VerificationResult))
    verifs = verifs_result.scalars().all()

    failures_result = await db.execute(select(Failure))
    total_failures = len(failures_result.scalars().all())

    benchmarks_result = await db.execute(select(BenchmarkCandidate))
    total_benchmarks = len(benchmarks_result.scalars().all())

    attacks_result = await db.execute(select(GraderAttack))
    grader_fp = sum(1 for a in attacks_result.scalars().all() if a.grader_bypassed)

    completed = [r for r in runs if r.status == RunStatus.COMPLETED]
    pass_count = sum(1 for v in verifs if v.final_verdict == "pass")
    fail_count = sum(1 for v in verifs if v.final_verdict == "fail")
    susp_count = sum(1 for v in verifs if v.final_verdict == "suspicious")
    rh_incidents = sum(1 for v in verifs if v.reward_hacking_detected)

    total = len(verifs) or 1
    return OverviewOut(
        total_tasks=total_tasks,
        total_runs=len(runs),
        pass_count=pass_count,
        fail_count=fail_count,
        suspicious_count=susp_count,
        pass_rate=pass_count / total,
        fail_rate=fail_count / total,
        suspicious_rate=susp_count / total,
        reward_hacking_incidents=rh_incidents,
        grader_false_positives=grader_fp,
        total_failures=total_failures,
        total_benchmarks=total_benchmarks,
    )


@router.get("/{run_id}", response_model=RunOut)
async def get_run(run_id: str, db: AsyncSession = Depends(get_db)):
    run = await db.get(AgentRun, run_id)
    if not run:
        raise HTTPException(status_code=404, detail=f"Run {run_id} not found")
    return run


@router.get("/{run_id}/trajectory", response_model=list[TrajectoryEventOut])
async def get_trajectory(run_id: str, db: AsyncSession = Depends(get_db)):
    run = await db.get(AgentRun, run_id)
    if not run:
        raise HTTPException(status_code=404, detail=f"Run {run_id} not found")
    result = await db.execute(
        select(TrajectoryEvent)
        .where(TrajectoryEvent.run_id == run_id)
        .order_by(TrajectoryEvent.sequence_num)
    )
    return result.scalars().all()


@router.get("/{run_id}/verification", response_model=VerificationResultOut)
async def get_verification(run_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(VerificationResult).where(VerificationResult.run_id == run_id)
    )
    verif = result.scalar_one_or_none()
    if not verif:
        raise HTTPException(status_code=404, detail=f"Verification for run {run_id} not found")
    return verif


@router.get("/{run_id}/failures", response_model=list[FailureOut])
async def get_failures(run_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Failure).where(Failure.run_id == run_id))
    return result.scalars().all()


@router.post("", response_model=RunOut, status_code=201)
async def create_run(run_in: RunCreate, db: AsyncSession = Depends(get_db)):
    """Create a run record (actual execution happens via CLI/engine)."""
    from failureforge.models import Task
    task = await db.get(Task, run_in.task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"Task {run_in.task_id} not found")

    run = AgentRun(
        task_id=run_in.task_id,
        agent_name=run_in.agent_name,
        status=RunStatus.PENDING,
        metadata_=run_in.metadata_,
    )
    db.add(run)
    await db.flush()
    return run


@router.get("/clusters/all")
async def get_failure_clusters(db: AsyncSession = Depends(get_db)) -> list[dict]:
    """Get failure clusters."""
    from failureforge.failure_analysis.analyzer import cluster_failures

    result = await db.execute(select(Failure))
    all_failures = result.scalars().all()

    # Group by run_id
    by_run: dict[str, list[dict]] = {}
    for f in all_failures:
        by_run.setdefault(f.run_id, []).append({
            "failure_type": str(f.failure_type),
            "failure_pattern": f.failure_pattern,
            "description": f.description,
            "severity": f.severity,
        })

    clusters = cluster_failures([(run_id, failures) for run_id, failures in by_run.items()])

    return [c.to_dict() for c in clusters]
