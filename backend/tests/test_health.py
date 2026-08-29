import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient
from app.main import app
from app.services.fetcher import FetchResult
from app.services.html_parser import parse_html

client = TestClient(app)


def test_get_health():
    """Verify that GET /health returns status 200 and expected schema."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "running" in data["message"]


def test_post_analyse_valid_mock():
    """Verify that POST /api/analyse processes valid URLs and returns structured raw data."""
    mock_html = "<html><head><title>Test Clinic</title></head><body><h1>Welcome to Test Clinic</h1></body></html>"
    mock_parsed = parse_html(mock_html, "https://test-clinic.com")
    mock_result = FetchResult(
        success=True,
        initial_url="https://test-clinic.com",
        final_url="https://test-clinic.com",
        status_code=200,
        response_time_ms=120,
        content_type="text/html",
        parsed_data=mock_parsed,
    )

    with patch("app.main.fetch_website", return_value=mock_result):
        response = client.post("/api/analyse", json={"url": "test-clinic.com"})
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["target_url"] == "https://test-clinic.com"
        assert data["fetch_data"]["status_code"] == 200
        assert data["fetch_data"]["parsed_data"]["title"] == "Test Clinic"
        assert data["fetch_data"]["parsed_data"]["h1_count"] == 1


def test_post_analyse_empty_url_fails():
    """Verify that empty URL fails validation with 422."""
    response = client.post("/api/analyse", json={"url": "   "})
    assert response.status_code == 422


def test_post_analyse_invalid_scheme_fails():
    """Verify that invalid URL scheme fails validation with 422."""
    response = client.post("/api/analyse", json={"url": "ftp://example.com"})
    assert response.status_code == 422
