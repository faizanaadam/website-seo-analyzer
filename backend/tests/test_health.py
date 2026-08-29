import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_get_health():
    """Verify that GET /health returns status 200 and expected schema."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "running" in data["message"]


def test_post_analyse_placeholder():
    """Verify that POST /api/analyse validates input and returns response."""
    response = client.post("/api/analyse", json={"url": "https://example.com"})
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "connected"
    assert data["target_url"] == "https://example.com"


def test_post_analyse_url_normalization():
    """Verify that URLs without protocol prefix are normalized."""
    response = client.post("/api/analyse", json={"url": "example-clinic.com"})
    assert response.status_code == 200
    data = response.json()
    assert data["target_url"] == "https://example-clinic.com"


def test_post_analyse_empty_url_fails():
    """Verify that empty URL fails validation with 422."""
    response = client.post("/api/analyse", json={"url": "   "})
    assert response.status_code == 422
