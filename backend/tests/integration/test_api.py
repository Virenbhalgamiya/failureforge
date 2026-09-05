"""Integration tests for FailureForge FastAPI API endpoints."""

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport

from failureforge.main import app
from failureforge.database import create_tables, get_async_engine
from failureforge.models import Base


@pytest_asyncio.fixture(autouse=True)
async def setup_database():
    """Ensure database schema is created before API tests."""
    engine = get_async_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield


@pytest.mark.asyncio
async def test_health_endpoint():
    """Test /health API endpoint."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        res = await client.get("/health")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "ok"


@pytest.mark.asyncio
async def test_list_tasks_endpoint():
    """Test /api/v1/tasks endpoint."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        res = await client.get("/api/v1/tasks")
        assert res.status_code == 200
        data = res.json()
        assert isinstance(data, list)



@pytest.mark.asyncio
async def test_overview_endpoint():
    """Test /api/v1/runs/overview endpoint."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        res = await client.get("/api/v1/runs/overview")
        assert res.status_code == 200
        data = res.json()
        assert "total_tasks" in data
        assert "pass_rate" in data


@pytest.mark.asyncio
async def test_redteam_api():
    """Test /api/v1/benchmarks/redteam endpoint."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        res = await client.post("/api/v1/benchmarks/redteam")
        assert res.status_code == 200
        data = res.json()
        assert "robustness_score" in data
