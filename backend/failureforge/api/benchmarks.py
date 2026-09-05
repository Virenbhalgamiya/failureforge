"""Benchmarks API endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from failureforge.database import get_db
from failureforge.models import BenchmarkCandidate, GraderAttack, Failure
from failureforge.schemas import BenchmarkCandidateOut, GraderAttackOut, GraderReportOut

router = APIRouter(tags=["benchmarks"])


@router.get("", response_model=list[BenchmarkCandidateOut])
async def list_benchmarks(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(BenchmarkCandidate).order_by(BenchmarkCandidate.created_at.desc()))
    return result.scalars().all()


@router.get("/{benchmark_id}", response_model=BenchmarkCandidateOut)
async def get_benchmark(benchmark_id: str, db: AsyncSession = Depends(get_db)):
    b = await db.get(BenchmarkCandidate, benchmark_id)
    if not b:
        raise HTTPException(status_code=404, detail=f"Benchmark {benchmark_id} not found")
    return b


@router.post("/generate")
async def generate_benchmarks(db: AsyncSession = Depends(get_db)) -> dict:
    """Trigger benchmark generation from all unprocessed failures."""
    from failureforge.models import ReviewStatus
    from failureforge.benchmark_generation.generator import generate_benchmark_from_failure

    # Find failures without benchmark candidates
    all_failures = (await db.execute(select(Failure))).scalars().all()
    existing = {b.source_failure_id for b in (await db.execute(select(BenchmarkCandidate))).scalars().all()}

    generated = 0
    for failure in all_failures:
        if failure.id in existing:
            continue
        try:
            candidate_data = generate_benchmark_from_failure(
                failure={
                    "id": failure.id,
                    "failure_type": failure.failure_type,
                    "failure_pattern": failure.failure_pattern,
                    "description": failure.description,
                    "root_cause": failure.root_cause,
                },
                source_run={"id": failure.run_id},
                task={},
                trajectory=[],
            )
            candidate = BenchmarkCandidate(
                source_failure_id=failure.id,
                generated_task=candidate_data["generated_task"],
                generated_invariants=candidate_data["generated_invariants"],
                generated_grader=candidate_data["generated_grader"],
                known_failure_mode=candidate_data["known_failure_mode"],
            )
            db.add(candidate)
            generated += 1
        except Exception as e:
            pass

    await db.flush()
    return {"generated": generated}


@router.post("/{benchmark_id}/red-team")
async def run_red_team(benchmark_id: str, db: AsyncSession = Depends(get_db)) -> GraderReportOut:
    """Run the grader red-team against a benchmark."""
    b = await db.get(BenchmarkCandidate, benchmark_id)
    if not b:
        raise HTTPException(status_code=404, detail=f"Benchmark {benchmark_id} not found")

    # Get existing attacks
    attacks_result = await db.execute(
        select(GraderAttack).where(GraderAttack.benchmark_id == benchmark_id)
    )
    attacks = attacks_result.scalars().all()

    if not attacks:
        raise HTTPException(
            status_code=400,
            detail="No red-team attacks found. Run 'failureforge redteam BENCHMARK_ID' first."
        )

    # Compute metrics
    tp = sum(1 for a in attacks if not a.grader_bypassed and a.actual_verdict == "fail")
    tn = sum(1 for a in attacks if not a.grader_bypassed and a.actual_verdict in ("pass", "suspicious"))
    fp = sum(1 for a in attacks if a.grader_bypassed)
    fn = sum(1 for a in attacks if not a.grader_bypassed and a.actual_verdict == "pass")

    total = tp + tn + fp + fn or 1
    precision = tp / (tp + fp) if (tp + fp) > 0 else 1.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 1.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
    rh_resistance = 1.0 - (fp / len(attacks)) if attacks else 1.0

    return GraderReportOut(
        benchmark_id=benchmark_id,
        total_attacks=len(attacks),
        true_positives=tp,
        true_negatives=tn,
        false_positives=fp,
        false_negatives=fn,
        precision=round(precision, 3),
        recall=round(recall, 3),
        f1=round(f1, 3),
        reward_hacking_resistance=round(rh_resistance, 3),
        attacks=attacks,
    )


@router.post("/redteam")
async def run_global_redteam() -> dict:
    """Run global grader red-team suite against benchmark suite."""
    from failureforge.redteam.grader_redteam import GraderRedTeam
    redteam = GraderRedTeam()
    return redteam.run_redteam_suite()

