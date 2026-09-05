"""FastAPI application entry point."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from failureforge.config import get_settings
from failureforge.database import create_tables
from failureforge.logging_config import configure_logging
from failureforge.api import tasks, runs, benchmarks, reports, health

settings = get_settings()
configure_logging(settings.log_level)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await create_tables()
    yield
    # Shutdown


app = FastAPI(
    title="FailureForge",
    description="Adversarial Evaluation Engine for Agent Benchmarking",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)

# Direct prefixes
app.include_router(tasks.router, prefix="/tasks")
app.include_router(runs.router, prefix="/runs")
app.include_router(benchmarks.router, prefix="/benchmarks")
app.include_router(reports.router, prefix="/grader-reports")

# /api/v1 prefixes
app.include_router(tasks.router, prefix="/api/v1/tasks")
app.include_router(runs.router, prefix="/api/v1/runs")
app.include_router(benchmarks.router, prefix="/api/v1/benchmarks")
app.include_router(reports.router, prefix="/api/v1/grader-reports")


@app.get("/")
async def root():
    return {
        "name": "FailureForge",
        "tagline": "Adversarial evaluation engine for agent benchmarking",
        "version": "0.1.0",
        "docs": "/docs",
    }
