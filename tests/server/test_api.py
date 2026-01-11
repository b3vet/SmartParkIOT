"""
API integration tests.
"""

import pytest
from unittest.mock import Mock, patch

# Mock the inference engine before importing the app
with patch('app.services.inference.InferenceEngine'):
    from fastapi.testclient import TestClient
    from app.main import app


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


def test_root_endpoint(client):
    """Test root endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "SmartPark API"
    assert data["version"] == "1.0.0"
    assert data["status"] == "running"


def test_health_endpoint(client):
    """Test health check endpoint."""
    response = client.get("/api/v1/health/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "timestamp" in data


def test_summary_endpoint(client):
    """Test summary endpoint."""
    response = client.get("/api/v1/frames/summary")
    assert response.status_code == 200
    data = response.json()
    assert 'free_count' in data
    assert 'occupied_count' in data
    assert 'total_slots' in data


def test_slots_endpoint(client):
    """Test slots endpoint."""
    response = client.get("/api/v1/frames/slots")
    assert response.status_code == 200
    data = response.json()
    assert 'slots' in data
    assert 'summary' in data


def test_unauthorized_upload(client):
    """Test upload without API key."""
    response = client.post("/api/v1/frames/")
    assert response.status_code in [401, 422]  # Unauthorized or validation error


def test_upload_with_invalid_key(client):
    """Test upload with invalid API key."""
    response = client.post(
        "/api/v1/frames/",
        headers={"X-API-Key": "invalid-key"},
        data={
            "frame_id": 1,
            "timestamp": "2026-01-15T10:00:00Z",
            "node_id": "test"
        }
    )
    assert response.status_code in [401, 422]
