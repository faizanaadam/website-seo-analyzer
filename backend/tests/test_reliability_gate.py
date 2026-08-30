import pytest
import json
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient
import httpx

from app.main import app
from app.services.fetcher import fetch_website, FetchResult
from app.services.html_parser import parse_html
from app.services.technical_seo import evaluate_technical_seo
from app.services.content_analysis import analyze_content
from app.services.ai_insights import generate_ai_insights, GroundingEvidenceRegistry
from app.models import (
    RawFetchData,
    TechnicalSEOResultModel,
    ContentAnalysisResultModel,
    PageSpeedResultModel,
)

test_client = TestClient(app)

CHALLENGE_HTML_403 = """
<!DOCTYPE html>
<html lang="en">
<head>
    <title>Access Denied | www.tajhotels.com</title>
</head>
<body>
    <h1>Access Denied</h1>
    <p>You don't have permission to access "http://www.tajhotels.com/" on this server.</p>
    <p>Reference #18.a8c64317.1709192400.1234567</p>
</body>
</html>
"""


def build_mock_403_fetch_result():
    parsed = parse_html(CHALLENGE_HTML_403, "https://www.tajhotels.com")
    return FetchResult(
        success=True,
        initial_url="https://www.tajhotels.com",
        final_url="https://www.tajhotels.com",
        status_code=403,
        response_time_ms=120,
        content_type="text/html",
        redirect_chain=[],
        raw_html=CHALLENGE_HTML_403,
        parsed_data=parsed,
        robots_txt_present=True,
        sitemap_xml_present=True,
        content_accessible=False,
        content_reliability="unreliable",
        error_type="bot_protection_detected",
        error_message="Website returned an automated access or bot-protection challenge (HTTP 403).",
    )


@pytest.mark.anyio
async def test_fetcher_403_waf_challenge_flags_unreliable_content():
    """Verify fetcher flags HTTP 403 / WAF challenges as content_accessible=False."""
    mock_resp = MagicMock()
    mock_resp.status_code = 403
    mock_resp.text = CHALLENGE_HTML_403
    mock_resp.history = []
    mock_resp.url = "https://www.tajhotels.com"
    mock_resp.headers = {"content-type": "text/html"}

    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.get = AsyncMock(return_value=mock_resp)

    # robots.txt and sitemap.xml checks
    with patch("app.services.fetcher.check_robots_and_sitemap", return_value=(True, True)):
        result = await fetch_website("https://www.tajhotels.com", client=mock_client)

        assert result.status_code == 403
        assert result.content_accessible is False
        assert result.content_reliability == "unreliable"
        assert result.error_type == "bot_protection_detected"
        assert result.robots_txt_present is True
        assert result.sitemap_xml_present is True


def test_technical_seo_gate_suppresses_false_content_failures_on_403():
    """Verify Technical SEO suppresses false content failures when crawler is blocked."""
    fetch_result = build_mock_403_fetch_result()
    tech_eval = evaluate_technical_seo(fetch_result)

    summary = tech_eval.summary
    assert summary.is_content_blocked is True
    assert summary.reliability_notice is not None

    findings_map = {f.id: f for f in tech_eval.findings}

    # Reliable network checks must be preserved
    assert findings_map["ssl_https"].status == "pass"
    assert findings_map["robots_txt"].status == "pass"
    assert findings_map["sitemap_xml"].status == "pass"
    assert findings_map["bot_protection_detected"].status == "needs_attention"

    # HTML/content-derived checks must NOT be marked as failed claims about the actual site
    assert findings_map["page_title"].is_inconclusive is True
    assert "Inconclusive" in findings_map["page_title"].summary
    assert findings_map["meta_description"].is_inconclusive is True
    assert findings_map["heading_structure"].is_inconclusive is True
    assert findings_map["image_alt_tags"].is_inconclusive is True
    assert findings_map["schema_org"].is_inconclusive is True


@pytest.mark.anyio
async def test_content_analysis_gate_returns_inconclusive_on_blocked_site():
    """Verify Content Analysis skips subpage crawling and returns inconclusive structure."""
    fetch_result = build_mock_403_fetch_result()
    content_eval = await analyze_content(fetch_result)

    assert content_eval.is_inconclusive is True
    assert content_eval.inconclusive_reason is not None
    assert content_eval.total_pages_analyzed == 0
    assert content_eval.homepage_word_count == 0
    assert len(content_eval.services_structure.detected_services) == 0
    assert len(content_eval.ctas.phones) == 0
    assert "challenged by edge security firewall" in content_eval.summary.lower()


@pytest.mark.anyio
async def test_ai_insights_gate_on_403_discards_hallucinated_content_fixes():
    """Verify AI Insights grounding layer discards hallucinated content recommendations on 403 sites."""
    fetch_result = build_mock_403_fetch_result()
    tech_eval = evaluate_technical_seo(fetch_result)
    content_eval = await analyze_content(fetch_result)

    # Craft an AI response that hallucinated content fixes based on the challenge page
    hallucinated_ai_json = {
        "status": "available",
        "overall_assessment": "needs_improvement",
        "executive_summary": "The website has 17 words and lacks procedure pages.",
        "top_priorities": [
            {
                "title": "Add Descriptive Image Alt Tags to 3 Images",
                "priority": "high",
                "category": "content",
                "explanation": "Images on challenge page missing alt text.",
                "business_impact": "Image search.",
                "recommended_action": "Add alt tags.",
                "estimated_effort": "quick",
                "anchor_finding_id": "image_alt_tags"
            },
            {
                "title": "Whitelist Search Engine Bots in CDN/WAF Firewall Rules",
                "priority": "critical",
                "category": "technical_seo",
                "explanation": "Automated access returned HTTP 403 challenge.",
                "business_impact": "Allows Googlebot to index hotel pages.",
                "recommended_action": "Configure Akamai/Cloudflare WAF rule to allow verified bots.",
                "estimated_effort": "moderate",
                "anchor_finding_id": "bot_protection_detected"
            }
        ],
        "quick_wins": ["Add image alt tags", "Configure WAF bot whitelist"],
        "strengths": ["Valid HTTPS encryption across all pages"],
        "limitations": ["Automated crawler was challenged by edge security firewall."]
    }

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "choices": [{"message": {"content": json.dumps(hallucinated_ai_json)}}]
    }

    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.post = AsyncMock(return_value=mock_resp)

    raw_fetch = RawFetchData(**fetch_result.to_dict())
    tech_model = TechnicalSEOResultModel(**tech_eval.to_dict())

    result = await generate_ai_insights(
        technical_seo=tech_model,
        content_analysis=content_eval,
        pagespeed=PageSpeedResultModel(status="unavailable"),
        fetch_data=raw_fetch,
        client=mock_client,
        api_key="valid-key",
    )

    # image_alt_tags was marked inconclusive, so it must be discarded
    priority_anchors = [p.anchor_finding_id for p in result.top_priorities]
    assert "image_alt_tags" not in priority_anchors
    assert "bot_protection_detected" in priority_anchors


def test_end_to_end_analyse_endpoint_on_blocked_site():
    """Verify POST /api/analyse on a 403/WAF challenged website."""
    fetch_result = build_mock_403_fetch_result()
    mock_psi = PageSpeedResultModel(status="unavailable", reason="Rate limit")

    with patch("app.main.fetch_website", return_value=fetch_result), \
         patch("app.main.get_pagespeed_insights", return_value=mock_psi):

        response = test_client.post("/api/analyse", json={"url": "https://www.tajhotels.com"})
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "success"
        assert data["fetch_data"]["content_accessible"] is False
        assert data["fetch_data"]["content_reliability"] == "unreliable"
        assert data["technical_seo"]["summary"]["is_content_blocked"] is True
        assert data["content_analysis"]["is_inconclusive"] is True
