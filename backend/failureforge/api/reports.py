"""Grader Reports API."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from failureforge.database import get_db
from failureforge.models import GraderAttack, BenchmarkCandidate

router = APIRouter(tags=["reports"])


@router.get("")
async def list_grader_reports(db: AsyncSession = Depends(get_db)) -> list[dict]:
    """List all grader reports grouped by benchmark."""
    benchmarks = (await db.execute(select(BenchmarkCandidate))).scalars().all()
    reports = []

    for b in benchmarks:
        attacks = (await db.execute(
            select(GraderAttack).where(GraderAttack.benchmark_id == b.id)
        )).scalars().all()

        if not attacks:
            continue

        fp = sum(1 for a in attacks if a.grader_bypassed)
        reports.append({
            "benchmark_id": b.id,
            "known_failure_mode": b.known_failure_mode,
            "total_attacks": len(attacks),
            "false_positives": fp,
            "reward_hacking_resistance": round(1.0 - (fp / len(attacks)), 3),
        })

    return reports
