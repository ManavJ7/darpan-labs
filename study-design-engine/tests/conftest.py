import json
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.fixture
def mock_llm_client():
    """Mock LLM client that returns canned JSON responses."""
    client = AsyncMock()
    client.model = "gpt-4o"
    client.temperature = 0.3

    default_response = json.dumps({
        "study_type": "concept_testing",
        "study_type_confidence": 0.92,
        "recommended_title": "Test Study",
        "recommended_metrics": ["purchase_intent", "uniqueness"],
        "recommended_audience": {"age": "18-45", "geography": "urban"},
        "methodology_family": "sequential_monadic",
        "methodology_rationale": "Best for multi-concept testing",
        "clarification_questions": [],
        "flags": [],
    })

    client.generate = AsyncMock(return_value=default_response)
    client.generate_json = AsyncMock(return_value=json.loads(default_response))
    return client


@pytest.fixture
def mock_db_session():
    """Mock async database session."""
    session = AsyncMock()
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    session.execute = AsyncMock()
    session.delete = AsyncMock()
    return session


@pytest.fixture
def sample_study():
    """Create a sample study object for testing."""
    study = MagicMock()
    study.id = uuid.uuid4()
    study.brand_id = uuid.uuid4()
    study.status = "init"
    study.question = "Which of our 3 new snack concepts resonates best with urban millennials?"
    study.title = None
    study.brand_name = "TestBrand"
    study.category = "snacks"
    study.context = {}
    study.study_metadata = {}
    study.created_at = datetime.now(timezone.utc)
    study.updated_at = datetime.now(timezone.utc)
    return study


@pytest.fixture
def sample_study_id():
    return uuid.uuid4()


@pytest.fixture
async def test_client():
    """Async test client for FastAPI app."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
