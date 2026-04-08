"""Tests for the connectors API and cost recording."""

import pytest
import sys
import os
from unittest.mock import AsyncMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from backend.main import app
from backend.database import CostEntry, AsyncSessionLocal, engine, Base
from backend.providers.base import AIResponse


@pytest.fixture
async def db_setup():
    """Set up test database tables."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.mark.asyncio
async def test_complete_records_cost(db_setup):
    """Test that /api/connectors/complete records costs to database."""
    client = TestClient(app)

    # Mock the provider response
    mock_response = AIResponse(
        provider="test-provider",
        model="test-model",
        content="Test response",
        tokens_in=10,
        tokens_out=20,
        cost_usd=0.001,
        latency_ms=100,
    )

    with patch("backend.providers.registry.get_registry") as mock_get_registry:
        mock_provider = AsyncMock()
        mock_provider.complete.return_value = mock_response

        mock_registry = {"test-provider": mock_provider}
        mock_get_registry.return_value = mock_registry

        response = client.post(
            "/api/connectors/complete",
            json={
                "provider": "test-provider",
                "model": "test-model",
                "prompt": "Test prompt",
                "max_tokens": 100,
            },
        )

        assert response.status_code == 200
        assert response.json()["cost_usd"] == 0.001

        # Verify cost was recorded in database
        async with AsyncSessionLocal() as session:
            from sqlalchemy import select
            result = await session.execute(select(CostEntry))
            costs = result.scalars().all()
            assert len(costs) == 1
            assert costs[0].provider == "test-provider"
            assert costs[0].model == "test-model"
            assert costs[0].cost_usd == 0.001
            assert costs[0].tokens_in == 10
            assert costs[0].tokens_out == 20
