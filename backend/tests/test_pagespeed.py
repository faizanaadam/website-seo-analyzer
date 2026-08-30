import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient
import httpx

from app.main import app
from app.services.pagespeed import get_pagespeed_insights
from app.models import PageSpeedResultModel, PageSpeedMetricsModel
from app.services.fetcher import FetchResult
from app.services.html_parser import parse_html

test_client = TestClient(app)


MOCK_SUCCESSFUL_PAGESPEED_JSON = {
    "lighthouseResult": {
        "categories": {
            "performance": {
                "score": 0.85
            }
        },
        "audits": {
            "first-contentful-paint": {
                "displayValue": "1.4 s",
                "numericValue": 1400
            },
            "largest-contentful-paint": {
                "displayValue": "2.6 s",
                "numericValue": 2600
            },
            "cumulative-layout-shift": {
                "displayValue": "0.04",
                "numericValue": 0.042
            },
            "total-blocking-time": {
                "displayValue": "180 ms",
                "numericValue": 180
            },
            "interaction-to-next-paint": {
                "displayValue": "210 ms",
                "numericValue": 210
            }
        }
    }
}


@pytest.mark.anyio
async def test_pagespeed_successful_response():
    """Verify successful PageSpeed API response parsing into metrics."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = MOCK_SUCCESSFUL_PAGESPEED_JSON

    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.get = AsyncMock(return_value=mock_resp)

    result = await get_pagespeed_insights("https://example.com", client=mock_client, api_key="test-api-key")

    assert result.status == "available"
    assert result.performance_score == 85
    assert result.metrics is not None
    assert result.metrics.fcp == "1.4 s"
    assert result.metrics.lcp == "2.6 s"
    assert result.metrics.cls == 0.042
    assert result.metrics.tbt == "180 ms"
    assert result.metrics.inp == "210 ms"
    assert result.reason is None


@pytest.mark.anyio
async def test_pagespeed_missing_api_key():
    """Verify graceful handling when no PageSpeed API key is configured."""
    result = await get_pagespeed_insights("https://example.com", api_key="")

    assert result.status == "unavailable"
    assert result.performance_score is None
    assert result.metrics is None
    assert "not configured" in result.reason.lower()


@pytest.mark.anyio
async def test_pagespeed_invalid_api_key():
    """Verify graceful handling of HTTP 403 / invalid key response."""
    mock_resp = MagicMock()
    mock_resp.status_code = 403
    mock_resp.json.return_value = {
        "error": {
            "message": "The provided API key is invalid.",
            "code": 403
        }
    }

    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.get = AsyncMock(return_value=mock_resp)

    result = await get_pagespeed_insights("https://example.com", client=mock_client, api_key="invalid-key")

    assert result.status == "unavailable"
    assert result.performance_score is None
    assert "invalid" in result.reason.lower() or "permissions" in result.reason.lower()


@pytest.mark.anyio
async def test_pagespeed_quota_exceeded():
    """Verify graceful handling of HTTP 429 rate limit or quota exceeded."""
    mock_resp = MagicMock()
    mock_resp.status_code = 429

    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.get = AsyncMock(return_value=mock_resp)

    result = await get_pagespeed_insights("https://example.com", client=mock_client, api_key="valid-key")

    assert result.status == "unavailable"
    assert result.performance_score is None
    assert "quota" in result.reason.lower() or "rate limit" in result.reason.lower()


@pytest.mark.anyio
async def test_pagespeed_timeout():
    """Verify graceful handling of timeout exceptions."""
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.get = AsyncMock(side_effect=httpx.TimeoutException("Connection timed out"))

    result = await get_pagespeed_insights("https://example.com", client=mock_client, api_key="valid-key")

    assert result.status == "unavailable"
    assert result.performance_score is None
    assert "timed out" in result.reason.lower()


@pytest.mark.anyio
async def test_pagespeed_bad_request_or_malformed():
    """Verify graceful handling of HTTP 400 bad request."""
    mock_resp = MagicMock()
    mock_resp.status_code = 400
    mock_resp.json.return_value = {
        "error": {
            "message": "Invalid URL supplied.",
            "code": 400
        }
    }

    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.get = AsyncMock(return_value=mock_resp)

    result = await get_pagespeed_insights("https://example.com", client=mock_client, api_key="valid-key")

    assert result.status == "unavailable"
    assert result.performance_score is None
    assert "bad request" in result.reason.lower() or "invalid url" in result.reason.lower()


def test_analyse_endpoint_with_pagespeed_and_content():
    """Verify POST /api/analyse integrates Content Analysis and PageSpeed seamlessly."""
    mock_html = """
    <html>
        <head><title>Apex Auto Care</title></head>
        <body>
            <h1>Apex Auto Care</h1>
            <p>Welcome to top rated auto service in Austin.</p>
            <a href="tel:5125550100">512-555-0100</a>
        </body>
    </html>
    """
    mock_parsed = parse_html(mock_html, "https://apexautocare.com")
    mock_fetch_res = FetchResult(
        success=True,
        initial_url="https://apexautocare.com",
        final_url="https://apexautocare.com",
        status_code=200,
        response_time_ms=150,
        content_type="text/html",
        raw_html=mock_html,
        parsed_data=mock_parsed,
    )

    mock_pagespeed_res = PageSpeedResultModel(
        status="available",
        performance_score=78,
        metrics=PageSpeedMetricsModel(
            fcp="1.2 s",
            lcp="2.4 s",
            cls=0.05,
            inp="150 ms",
            tbt="120 ms",
        ),
        reason=None,
    )

    with patch("app.main.fetch_website", return_value=mock_fetch_res), \
         patch("app.main.get_pagespeed_insights", return_value=mock_pagespeed_res):

        response = test_client.post("/api/analyse", json={"url": "https://apexautocare.com"})
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "success"
        assert data["target_url"] == "https://apexautocare.com"
        assert data["technical_seo"] is not None

        # Content Analysis assertions
        assert data["content_analysis"] is not None
        assert data["content_analysis"]["total_pages_analyzed"] >= 1
        assert "5125550100" in data["content_analysis"]["contact_info"]["phones"] or "512-555-0100" in data["content_analysis"]["contact_info"]["phones"]

        # PageSpeed assertions
        assert data["pagespeed"] is not None
        assert data["pagespeed"]["status"] == "available"
        assert data["pagespeed"]["performance_score"] == 78
        assert data["pagespeed"]["metrics"]["fcp"] == "1.2 s"
        assert data["pagespeed"]["metrics"]["cls"] == 0.05
