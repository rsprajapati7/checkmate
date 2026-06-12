import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock, patch

from backend.main import app
from backend.core.config import settings
from backend.core.database import get_db
from backend.core.models import Job, JobStatus


@pytest.fixture
def client():
    # Clear overrides before each test
    app.dependency_overrides.clear()
    return TestClient(app)


def test_health_check(client):
    # Mock ping_db and llm_client.ping
    with patch("backend.main.ping_db", return_value=True), \
         patch("backend.ai_investigator.llm_client.llm_client.ping", return_value=True):
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["db"] == "connected"


def test_liveness_ready_probes(client):
    response = client.get("/health/live")
    assert response.status_code == 200
    assert response.json() == {"alive": True}

    with patch("backend.main.ping_db", return_value=True):
        response = client.get("/health/ready")
        assert response.status_code == 200
        assert response.json() == {"ready": True}

    with patch("backend.main.ping_db", return_value=False):
        response = client.get("/health/ready")
        assert response.status_code == 503


def test_api_key_auth_bypassed_if_unset(client):
    # When API_KEY_SECRET is unset (empty string), authentication is bypassed
    with patch.object(settings, "API_KEY_SECRET", ""):
        # Mock database session to return None (trigger 404)
        mock_db = MagicMock()
        mock_db.get = AsyncMock(return_value=None)
        
        # Define a mock generator for get_db dependency override
        async def override_get_db():
            yield mock_db

        app.dependency_overrides[get_db] = override_get_db

        response = client.get("/api/v1/jobs/some-job")
        # Should bypass auth and return 404 because job doesn't exist
        assert response.status_code == 404


def test_api_key_auth_enforced_if_set(client):
    # Enforce API key validation
    with patch.object(settings, "API_KEY_SECRET", "super-secret"):
        # Missing header -> 403 Forbidden
        response = client.get("/api/v1/jobs/some-job")
        assert response.status_code == 403
        assert response.json() == {"detail": "Invalid API key"}

        # Incorrect key -> 403 Forbidden
        response = client.get("/api/v1/jobs/some-job", headers={"X-Api-Key": "wrong-secret"})
        assert response.status_code == 403
        assert response.json() == {"detail": "Invalid API key"}

        # Correct key -> 404 (passes auth, goes to handler, doesn't find job)
        mock_db = MagicMock()
        mock_db.get = AsyncMock(return_value=None)
        
        async def override_get_db():
            yield mock_db

        app.dependency_overrides[get_db] = override_get_db

        response = client.get("/api/v1/jobs/some-job", headers={"X-Api-Key": "super-secret"})
        assert response.status_code == 404