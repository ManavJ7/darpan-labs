"""Tests for health check and basic API endpoints — 7+ tests."""
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_health_check_returns_200():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_health_check_body():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health")
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "study-design-engine"


@pytest.mark.asyncio
async def test_health_check_has_status_field():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health")
    data = response.json()
    assert "status" in data


@pytest.mark.asyncio
async def test_health_check_has_service_field():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health")
    data = response.json()
    assert "service" in data


@pytest.mark.asyncio
async def test_create_study_endpoint_exists():
    """Test that the POST /api/v1/studies endpoint is registered."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/api/v1/studies")
    assert response.status_code == 422  # Validation error, not 404


@pytest.mark.asyncio
async def test_get_study_endpoint_registered():
    """Test that the GET /api/v1/studies/{study_id} endpoint is registered by checking route list."""
    routes = [r.path for r in app.routes]
    assert "/api/v1/studies/{study_id}" in routes


@pytest.mark.asyncio
async def test_list_studies_endpoint_registered():
    """Test that the GET /api/v1/studies endpoint is registered."""
    routes = [r.path for r in app.routes]
    assert "/api/v1/studies" in routes
