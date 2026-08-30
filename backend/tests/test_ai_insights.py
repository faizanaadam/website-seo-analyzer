import pytest
import json
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient
import httpx

from app.main import app
from app.services.ai_insights import (
    generate_ai_insights,
    build_compact_factual_payload,
)
from app.models import (
    AIAnalysisResultModel,
    AIRecommendationModel,
    TechnicalSEOResultModel,
    TechnicalSEOSummaryModel,
    TechnicalFindingModel,
    ContentAnalysisResultModel,
    ContactInfoModel,
    CTAModel,
    ServiceStructureModel,
    PageSpeedResultModel,
    PageSpeedMetricsModel,
    RawFetchData,
    ParsedHTMLModel,
)

test_client = TestClient(app)

MOCK_OPENAI_VALID_JSON = {
    "status": "available",
    "overall_assessment": "moderate",
    "executive_summary": "Apex Auto Care exhibits a strong technical SEO foundation with HTTPS and mobile responsiveness. However, missing image alt tags and unconfigured structured data represent high-impact opportunities to improve local search visibility.",
    "top_priorities": [
        {
            "title": "Implement LocalBusiness and AutoRepair Schema Markup",
            "priority": "high",
            "category": "technical_seo",
            "explanation": "Structured data is currently absent, preventing rich snippets and local search highlights.",
            "business_impact": "Boosts local map pack presence and Google search visibility for auto repair queries in Austin.",
            "recommended_action": "Add JSON-LD LocalBusiness schema containing address, phone, and opening hours.",
            "estimated_effort": "moderate"
        },
        {
            "title": "Add Descriptive Alt Tags to Images",
            "priority": "medium",
            "category": "content",
            "explanation": "Multiple images lack alt attributes, reducing accessibility and image SEO value.",
            "business_impact": "Enables image search indexing and improves accessibility compliance.",
            "recommended_action": "Audit all <img> tags and add descriptive alt text describing vehicle repairs.",
            "estimated_effort": "quick"
        }
    ],
    "quick_wins": [
        "Add meta description to homepage targeting local auto repair services",
        "Add alt text to 3 uncaptioned service images"
    ],
    "strengths": [
        "Valid HTTPS encryption across all pages",
        "Responsive mobile viewport configuration",
        "Clear phone and email CTAs detected on homepage"
    ],
    "limitations": [
        "PageSpeed insights were unavailable due to API rate limit, so live lab performance vitals could not be evaluated."
    ]
}


from app.services.fetcher import FetchResult
from app.services.html_parser import parse_html


def build_mock_analysis_data():
    """Helper to generate factual test inputs."""
    tech_findings = [
        TechnicalFindingModel(
            id="image_alt_tags",
            title="Image Alt Text",
            status="needs_attention",
            summary="3 images missing alt text",
            why_it_matters="Helps screen readers",
            evidence_found="3 images without alt",
            suggested_action="Add alt text",
        ),
        TechnicalFindingModel(
            id="schema_org",
            title="Structured Data (Schema.org)",
            status="needs_attention",
            summary="Missing LocalBusiness schema.",
            why_it_matters="Helps local rich snippets.",
            evidence_found="No JSON-LD blocks found",
            suggested_action="Add LocalBusiness JSON-LD markup.",
        ),
        TechnicalFindingModel(
            id="ssl_https",
            title="HTTPS Security",
            status="pass",
            summary="Valid SSL",
            why_it_matters="Confirmed ranking factor",
            evidence_found="HTTPS active",
            suggested_action="No action needed",
        ),
    ]
    tech_seo = TechnicalSEOResultModel(
        summary=TechnicalSEOSummaryModel(
            passed_count=8,
            needs_attention_count=2,
            issues_count=0,
            total_checks=10,
            health_score=85,
            summary_text="Solid technical foundation.",
        ),
        findings=tech_findings,
        inferred_category="automotive",
    )
    content = ContentAnalysisResultModel(
        pages_analyzed=[],
        total_pages_analyzed=2,
        homepage_word_count=550,
        average_word_count=600,
        contact_info=ContactInfoModel(phones=["512-555-0199"], emails=["info@apexauto.com"]),
        ctas=CTAModel(phones=["512-555-0199"], emails=["info@apexauto.com"], booking_providers=["Calendly"]),
        services_structure=ServiceStructureModel(
            has_dedicated_service_pages=True,
            services_mainly_on_homepage=False,
            service_pages_count=2,
            detected_services=["Brake Repair", "Oil Change"],
        ),
        summary="Analyzed 2 pages.",
    )
    pagespeed = PageSpeedResultModel(
        status="available",
        performance_score=82,
        metrics=PageSpeedMetricsModel(fcp="1.2 s", lcp="2.4 s", cls=0.05),
        reason=None,
    )
    mock_html = "<html><head><title>Apex Auto Care | Austin TX</title></head><body><h1>Apex Auto Care</h1><p>Brake repair and oil change in Austin.</p></body></html>"
    parsed = parse_html(mock_html, "https://apexauto.com")
    fetch_result = FetchResult(
        success=True,
        initial_url="https://apexauto.com",
        final_url="https://apexauto.com",
        status_code=200,
        response_time_ms=250.0,
        parsed_data=parsed,
    )
    return tech_seo, content, pagespeed, fetch_result


def test_build_compact_factual_payload():
    """Verify that compact factual payload extracts necessary data without raw HTML or secrets."""
    tech_seo, content, pagespeed, fetch_data = build_mock_analysis_data()
    payload = build_compact_factual_payload(tech_seo, content, pagespeed, fetch_data)

    assert payload["target_url"] == "https://apexauto.com"
    assert payload["page_title"] == "Apex Auto Care | Austin TX"
    assert payload["inferred_category"] == "automotive"
    assert payload["technical_seo"]["health_score"] == 85
    assert len(payload["technical_seo"]["findings"]) == 3
    assert payload["content_analysis"]["homepage_word_count"] == 550
    assert payload["pagespeed"]["performance_score"] == 82
    # Ensure no raw HTML or sensitive keys are present
    assert "raw_html" not in str(payload)
    assert "api_key" not in str(payload).lower()


@pytest.mark.anyio
async def test_ai_insights_successful_response():
    """Verify successful OpenAI response parsing and Pydantic validation."""
    tech_seo, content, pagespeed, fetch_data = build_mock_analysis_data()

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "choices": [
            {
                "message": {
                    "content": json.dumps(MOCK_OPENAI_VALID_JSON)
                }
            }
        ]
    }

    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.post = AsyncMock(return_value=mock_resp)

    result = await generate_ai_insights(
        technical_seo=tech_seo,
        content_analysis=content,
        pagespeed=pagespeed,
        fetch_data=fetch_data,
        client=mock_client,
        api_key="test-openai-key",
    )

    assert result.status == "available"
    assert result.overall_assessment == "moderate"
    assert "Apex Auto Care" in (result.executive_summary or "")
    assert len(result.top_priorities) == 2
    assert result.top_priorities[0].priority == "high"
    assert len(result.quick_wins) >= 1
    assert len(result.strengths) >= 1


@pytest.mark.anyio
async def test_ai_insights_missing_api_key():
    """Verify graceful fallback when no OpenAI API key is configured."""
    tech_seo, content, pagespeed, fetch_data = build_mock_analysis_data()

    result = await generate_ai_insights(
        technical_seo=tech_seo,
        content_analysis=content,
        pagespeed=pagespeed,
        fetch_data=fetch_data,
        api_key="",
    )

    assert result.status == "unavailable"
    assert "not configured" in (result.reason or "").lower()


@pytest.mark.anyio
async def test_ai_insights_malformed_json_response():
    """Verify graceful handling when OpenAI returns malformed JSON."""
    tech_seo, content, pagespeed, fetch_data = build_mock_analysis_data()

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "choices": [{"message": {"content": "This is plain text, not JSON"}}]
    }

    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.post = AsyncMock(return_value=mock_resp)

    result = await generate_ai_insights(
        technical_seo=tech_seo,
        content_analysis=content,
        pagespeed=pagespeed,
        fetch_data=fetch_data,
        client=mock_client,
        api_key="valid-key",
    )

    assert result.status == "unavailable"
    assert "not valid json" in (result.reason or "").lower()


@pytest.mark.anyio
async def test_ai_insights_timeout():
    """Verify graceful handling when OpenAI request times out."""
    tech_seo, content, pagespeed, fetch_data = build_mock_analysis_data()

    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.post = AsyncMock(side_effect=httpx.TimeoutException("OpenAI timeout"))

    result = await generate_ai_insights(
        technical_seo=tech_seo,
        content_analysis=content,
        pagespeed=pagespeed,
        fetch_data=fetch_data,
        client=mock_client,
        api_key="valid-key",
    )

    assert result.status == "unavailable"
    assert "timed out" in (result.reason or "").lower()


@pytest.mark.anyio
async def test_ai_insights_rate_limit():
    """Verify graceful handling when OpenAI returns HTTP 429."""
    tech_seo, content, pagespeed, fetch_data = build_mock_analysis_data()

    mock_resp = MagicMock()
    mock_resp.status_code = 429

    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.post = AsyncMock(return_value=mock_resp)

    result = await generate_ai_insights(
        technical_seo=tech_seo,
        content_analysis=content,
        pagespeed=pagespeed,
        fetch_data=fetch_data,
        client=mock_client,
        api_key="valid-key",
    )

    assert result.status == "unavailable"
    assert "rate limit" in (result.reason or "").lower()


@pytest.mark.anyio
async def test_ai_insights_validation_failure():
    """Verify graceful fallback when OpenAI JSON fails Pydantic schema validation."""
    tech_seo, content, pagespeed, fetch_data = build_mock_analysis_data()

    # Missing required top_priorities fields
    invalid_schema = {
        "status": "available",
        "top_priorities": [
            {"title": "Broken Item", "priority": "invalid_priority"}
        ]
    }

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "choices": [{"message": {"content": json.dumps(invalid_schema)}}]
    }

    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.post = AsyncMock(return_value=mock_resp)

    result = await generate_ai_insights(
        technical_seo=tech_seo,
        content_analysis=content,
        pagespeed=pagespeed,
        fetch_data=fetch_data,
        client=mock_client,
        api_key="valid-key",
    )

    assert result.status == "unavailable"
    assert "validate" in (result.reason or "").lower()


def test_analyse_endpoint_with_ai_insights_integration():
    """Verify POST /api/analyse integrates AI Insights alongside deterministic results."""
    mock_html = "<html><head><title>Apex Auto Care</title></head><body><h1>Apex Auto Care</h1></body></html>"
    tech_seo, content, pagespeed, fetch_data = build_mock_analysis_data()

    mock_ai_result = AIAnalysisResultModel(**MOCK_OPENAI_VALID_JSON)

    with patch("app.main.fetch_website", return_value=fetch_data), \
         patch("app.main.get_pagespeed_insights", return_value=pagespeed), \
         patch("app.main.analyze_content", return_value=content), \
         patch("app.main.generate_ai_insights", return_value=mock_ai_result):

        response = test_client.post("/api/analyse", json={"url": "https://apexauto.com"})
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "success"
        assert data["target_url"] == "https://apexauto.com"
        assert data["technical_seo"] is not None
        assert data["content_analysis"] is not None
        assert data["pagespeed"] is not None

        # AI Insights assertions
        assert data["ai_insights"] is not None
        assert data["ai_insights"]["status"] == "available"
        assert data["ai_insights"]["overall_assessment"] == "moderate"
        assert len(data["ai_insights"]["top_priorities"]) == 2
        assert data["ai_insights"]["top_priorities"][0]["priority"] == "high"

        # Verify API key is not in JSON response
        response_str = json.dumps(data)
        assert "sk-" not in response_str
        assert "openai_api_key" not in response_str.lower()


@pytest.mark.anyio
async def test_grounding_removes_recommendation_on_passed_check():
    """Verify that recommendations attempting to fix already PASSED checks are removed."""
    tech_seo, content, pagespeed, fetch_data = build_mock_analysis_data()

    # SSL is 'pass' in mock data. Let's craft an AI response that recommends fixing SSL/HTTPS.
    hallucinated_json = {
        "status": "available",
        "overall_assessment": "good",
        "executive_summary": "Test summary",
        "top_priorities": [
            {
                "title": "Install SSL Certificate to Enable HTTPS",
                "priority": "critical",
                "category": "technical_seo",
                "explanation": "Your website lacks SSL encryption.",
                "business_impact": "Security warnings will drive users away.",
                "recommended_action": "Purchase and install an SSL certificate.",
                "estimated_effort": "moderate",
                "anchor_finding_id": "ssl_https"
            },
            {
                "title": "Add Descriptive Alt Tags to Images",
                "priority": "medium",
                "category": "content",
                "explanation": "Images are missing alt text.",
                "business_impact": "Helps search engines understand image content.",
                "recommended_action": "Add alt tags.",
                "estimated_effort": "quick",
                "anchor_finding_id": "image_alt_tags"
            }
        ],
        "quick_wins": ["Install SSL certificate", "Add alt text to images"],
        "strengths": ["Valid HTTPS encryption"],
        "limitations": []
    }

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "choices": [{"message": {"content": json.dumps(hallucinated_json)}}]
    }

    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.post = AsyncMock(return_value=mock_resp)

    result = await generate_ai_insights(
        technical_seo=tech_seo,
        content_analysis=content,
        pagespeed=pagespeed,
        fetch_data=fetch_data,
        client=mock_client,
        api_key="valid-key",
    )

    # SSL recommendation must be discarded because SSL passed
    titles = [p.title for p in result.top_priorities]
    assert "Install SSL Certificate to Enable HTTPS" not in titles
    # Image alt tag recommendation must be retained
    assert "Add Descriptive Alt Tags to Images" in titles
    assert result.top_priorities[0].anchor_finding_id == "image_alt_tags"
    # Contradictory quick win must also be removed
    assert "Install SSL certificate" not in result.quick_wins


@pytest.mark.anyio
async def test_grounding_removes_unsupported_hallucinated_recommendation():
    """Verify that completely ungrounded recommendations (not matching any observed deficiency) are removed."""
    tech_seo, content, pagespeed, fetch_data = build_mock_analysis_data()

    hallucinated_json = {
        "status": "available",
        "overall_assessment": "needs_improvement",
        "executive_summary": "Test summary",
        "top_priorities": [
            {
                "title": "Patch SQL Injection Vulnerability in Custom Plugin",
                "priority": "critical",
                "category": "technical_seo",
                "explanation": "Detected database vulnerability.",
                "business_impact": "Prevents data breach.",
                "recommended_action": "Update SQL queries.",
                "estimated_effort": "significant",
                "anchor_finding_id": "sql_injection"
            },
            {
                "title": "Add Descriptive Alt Tags to Images",
                "priority": "medium",
                "category": "content",
                "explanation": "Images are missing alt text.",
                "business_impact": "Helps search engines.",
                "recommended_action": "Add alt text.",
                "estimated_effort": "quick",
                "anchor_finding_id": "image_alt_tags"
            }
        ],
        "quick_wins": ["Fix SQL injection", "Add alt text to images"],
        "strengths": ["Valid HTTPS encryption"],
        "limitations": []
    }

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "choices": [{"message": {"content": json.dumps(hallucinated_json)}}]
    }

    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.post = AsyncMock(return_value=mock_resp)

    result = await generate_ai_insights(
        technical_seo=tech_seo,
        content_analysis=content,
        pagespeed=pagespeed,
        fetch_data=fetch_data,
        client=mock_client,
        api_key="valid-key",
    )

    titles = [p.title for p in result.top_priorities]
    assert "Patch SQL Injection Vulnerability in Custom Plugin" not in titles
    assert "Add Descriptive Alt Tags to Images" in titles


@pytest.mark.anyio
async def test_grounding_removes_false_strengths():
    """Verify that strengths claiming failed checks are filtered out."""
    tech_seo, content, pagespeed, fetch_data = build_mock_analysis_data()

    # Image alt tags is 'needs_attention' (3 images missing alt text).
    # Let's craft an AI response that claims perfect alt text as a strength.
    hallucinated_json = {
        "status": "available",
        "overall_assessment": "good",
        "executive_summary": "Test summary",
        "top_priorities": [
            {
                "title": "Add Descriptive Alt Tags to Images",
                "priority": "medium",
                "category": "content",
                "explanation": "Images are missing alt text.",
                "business_impact": "Helps SEO.",
                "recommended_action": "Add alt text.",
                "estimated_effort": "quick",
                "anchor_finding_id": "image_alt_tags"
            }
        ],
        "quick_wins": ["Add alt text to images"],
        "strengths": [
            "All images contain complete and descriptive alt attributes",  # FALSE / CONTRADICTED
            "Valid HTTPS encryption across all pages"  # TRUE / CONFIRMED
        ],
        "limitations": []
    }

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "choices": [{"message": {"content": json.dumps(hallucinated_json)}}]
    }

    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.post = AsyncMock(return_value=mock_resp)

    result = await generate_ai_insights(
        technical_seo=tech_seo,
        content_analysis=content,
        pagespeed=pagespeed,
        fetch_data=fetch_data,
        client=mock_client,
        api_key="valid-key",
    )

    assert "All images contain complete and descriptive alt attributes" not in result.strengths
    assert "Valid HTTPS encryption across all pages" in result.strengths


@pytest.mark.anyio
async def test_grounding_fallback_when_all_priorities_hallucinated():
    """Verify fallback grounded priorities are generated from actual deficiencies when all AI priorities are discarded."""
    tech_seo, content, pagespeed, fetch_data = build_mock_analysis_data()

    hallucinated_json = {
        "status": "available",
        "overall_assessment": "needs_improvement",
        "executive_summary": "Test summary",
        "top_priorities": [
            {
                "title": "Configure Cloudflare CDN Enterprise Plan",
                "priority": "critical",
                "category": "performance",
                "explanation": "Hallucinated CDN recommendation.",
                "business_impact": "None.",
                "recommended_action": "Purchase plan.",
                "estimated_effort": "significant"
            }
        ],
        "quick_wins": ["Buy enterprise CDN"],
        "strengths": ["Enterprise CDN configured"],
        "limitations": []
    }

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "choices": [{"message": {"content": json.dumps(hallucinated_json)}}]
    }

    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.post = AsyncMock(return_value=mock_resp)

    result = await generate_ai_insights(
        technical_seo=tech_seo,
        content_analysis=content,
        pagespeed=pagespeed,
        fetch_data=fetch_data,
        client=mock_client,
        api_key="valid-key",
    )

    # Grounding layer must replace the hallucinated priority with real grounded deficiency
    assert len(result.top_priorities) >= 1
    assert result.top_priorities[0].anchor_finding_id in ("image_alt_tags", "pagespeed_performance", "dedicated_service_pages_missing")

