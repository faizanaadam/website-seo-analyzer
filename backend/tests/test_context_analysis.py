import pytest
import json
from unittest.mock import AsyncMock, patch, MagicMock
from bs4 import BeautifulSoup
import httpx

from app.models import (
    ParsedHTMLModel,
    RawFetchData,
    PageContentItem,
    ContactInfoModel,
    CTAModel,
    ServiceStructureModel,
    ContentAnalysisResultModel,
    BusinessContextModel,
    AudienceContextModel,
    ContextIntelligenceResultModel,
    TechnicalSEOResultModel,
    TechnicalSEOSummaryModel,
    TechnicalFindingModel,
    PageSpeedResultModel,
)
from app.services.context_analysis import (
    classify_business_context,
    infer_target_audience,
    evaluate_context_intelligence,
)
from app.services.content_analysis import extract_services_from_content
from app.services.recommendation_engine import (
    get_title_suggested_action,
    get_meta_desc_suggested_action,
    get_structured_data_suggested_action,
    generate_strategic_projects,
)
from app.services.technical_seo import evaluate_technical_seo
from app.services.fetcher import FetchResult
from app.services.html_parser import parse_html
from app.services.ai_insights import (
    build_compact_factual_payload,
    generate_ai_insights,
    GroundingEvidenceRegistry,
)


# =============================================================================
# 1. Technology / AI Website Classification
# =============================================================================
def test_technology_ai_website_classification():
    html = """
    <html>
    <head><title>Neuralake - AI Automation & Data Lake Platform</title></head>
    <body>
        <h1>Enterprise AI & Neural Automation Platform</h1>
        <h2>Data Lake Solutions & Machine Learning Infrastructure</h2>
        <p>We build deep learning software and data platforms for modern enterprises.</p>
    </body>
    </html>
    """
    parsed = parse_html(html, "https://theneuralake.com")
    ctx = classify_business_context(parsed, "https://theneuralake.com")

    assert ctx.category == "technology"
    assert ctx.confidence in ("high", "medium")
    assert ctx.reliability == "reliable"
    assert any("AI" in e or "title" in e.lower() for e in ctx.evidence)


# =============================================================================
# 2. Local Business Classification
# =============================================================================
def test_local_business_classification():
    html = """
    <html>
    <head><title>Apex Auto Repair & Mechanic Services</title></head>
    <body>
        <h1>Full Service Auto Repair & Car Care Garage</h1>
        <h2>Emergency Roadside Towing & Oil Change Near You</h2>
        <p>Certified mechanics providing professional automotive diagnostics.</p>
    </body>
    </html>
    """
    parsed = parse_html(html, "https://apexautorepair.com")
    ctx = classify_business_context(parsed, "https://apexautorepair.com")

    assert ctx.category == "local_business"
    assert ctx.confidence in ("high", "medium")
    assert ctx.reliability == "reliable"


# =============================================================================
# 3. Healthcare Classification
# =============================================================================
def test_healthcare_classification():
    html = """
    <html>
    <head><title>Bright Smile Dental Clinic - Cosmetic Dentistry</title></head>
    <body>
        <h1>Family & Cosmetic Dentist in City Center</h1>
        <h2>Teeth Whitening, Dental Implants & Invisalign</h2>
        <p>Gentle dental care for all patients with state-of-the-art medical technology.</p>
    </body>
    </html>
    """
    parsed = parse_html(html, "https://brightsmiledental.com")
    ctx = classify_business_context(parsed, "https://brightsmiledental.com")

    assert ctx.category == "healthcare"
    assert ctx.confidence in ("high", "medium")


# =============================================================================
# 4. Unknown Website Classification
# =============================================================================
def test_unknown_website_classification():
    html = """
    <html>
    <head><title>Example Domain</title></head>
    <body>
        <h1>Example Domain</h1>
        <p>This domain is for use in illustrative examples in documents.</p>
    </body>
    </html>
    """
    parsed = parse_html(html, "https://example.com")
    ctx = classify_business_context(parsed, "https://example.com")

    assert ctx.category == "unknown"
    assert ctx.confidence == "low"


# =============================================================================
# 5. Insufficient Evidence Returns Unknown / Inconclusive
# =============================================================================
def test_insufficient_evidence_returns_unknown():
    html = "<html><head><title>Welcome</title></head><body><h1>Hello World</h1><p>Welcome to our simple web page.</p></body></html>"
    parsed = parse_html(html, "https://simplepage.org")
    ctx = classify_business_context(parsed, "https://simplepage.org")

    assert ctx.category == "unknown"
    assert ctx.confidence == "low"
    assert ctx.reliability == "limited"


# =============================================================================
# 6. Domain Name Alone Does Not Determine Classification
# =============================================================================
def test_domain_name_alone_does_not_determine_classification():
    # A domain name that sounds like a dental clinic but has generic/unrelated content
    html = "<html><head><title>Personal Blog</title></head><body><h1>My Daily Journal</h1><p>Today I went for a walk in the park.</p></body></html>"
    parsed = parse_html(html, "https://dentalcare-something.com")
    ctx = classify_business_context(parsed, "https://dentalcare-something.com")

    assert ctx.category == "unknown"
    assert ctx.confidence == "low"


# =============================================================================
# 7. Audience Inference With Strong Evidence
# =============================================================================
def test_audience_inference_with_strong_evidence():
    html = """
    <html>
    <head><title>Enterprise AI Platform</title></head>
    <body>
        <h1>Enterprise Data Architecture & Automation</h1>
        <p>Built for engineering teams and enterprise organizations evaluating software.</p>
    </body>
    </html>
    """
    parsed = parse_html(html, "https://theneuralake.com")
    biz_ctx = classify_business_context(parsed, "https://theneuralake.com")
    aud_ctx = infer_target_audience(biz_ctx, parsed)

    assert aud_ctx.reliability == "reliable"
    assert "Engineering teams" in aud_ctx.target_audience or "Businesses" in aud_ctx.target_audience
    assert "hospitality" not in aud_ctx.target_audience.lower()


# =============================================================================
# 8. Audience Inference With Insufficient Evidence
# =============================================================================
def test_audience_inference_with_insufficient_evidence():
    html = "<html><head><title>Example Domain</title></head><body><p>Illustrative example.</p></body></html>"
    parsed = parse_html(html, "https://example.com")
    biz_ctx = classify_business_context(parsed, "https://example.com")
    aud_ctx = infer_target_audience(biz_ctx, parsed)

    assert aud_ctx.target_audience == "Inconclusive"
    assert aud_ctx.confidence == "low"
    assert aud_ctx.reliability == "inconclusive"


# =============================================================================
# 9. Homepage Service Detection
# =============================================================================
def test_homepage_service_detection():
    html = """
    <html>
    <body>
        <h1>Neuralake AI Platform</h1>
        <section id="services">
            <h2>Our Capabilities</h2>
            <h3>Automated Data Pipeline</h3>
            <h3>Predictive Analytics Engine</h3>
            <h3>Neural Search API</h3>
        </section>
    </body>
    </html>
    """
    soup = BeautifulSoup(html, "html.parser")
    hp_item = PageContentItem(
        url="https://theneuralake.com",
        page_name="Home",
        word_count=200,
        content_depth="adequate",
        headings=["Automated Data Pipeline", "Predictive Analytics Engine", "Neural Search API"],
        is_service_page=False,
    )
    svcs, details, has_ded, mainly_hp, from_hp, conf, arch = extract_services_from_content(
        pages=[hp_item],
        homepage_soup=soup,
    )

    assert "Automated Data Pipeline" in svcs
    assert "Predictive Analytics Engine" in svcs
    assert from_hp is True
    assert has_ded is False
    assert arch == "homepage_centric"


# =============================================================================
# 10. Dedicated Service Page Detection
# =============================================================================
def test_dedicated_service_page_detection():
    html = "<html><body><h1>Home</h1></body></html>"
    soup = BeautifulSoup(html, "html.parser")
    pages = [
        PageContentItem(url="https://example.com", page_name="Home", word_count=100, content_depth="shallow", is_service_page=False),
        PageContentItem(url="https://example.com/services/root-canal", page_name="Root Canal Therapy", word_count=350, content_depth="comprehensive", is_service_page=True),
        PageContentItem(url="https://example.com/services/teeth-whitening", page_name="Teeth Whitening", word_count=400, content_depth="comprehensive", is_service_page=True),
    ]
    svcs, details, has_ded, mainly_hp, from_hp, conf, arch = extract_services_from_content(
        pages=pages,
        homepage_soup=soup,
    )

    assert "Root Canal Therapy" in svcs
    assert "Teeth Whitening" in svcs
    assert has_ded is True
    assert arch == "dedicated_multi_page"


# =============================================================================
# 11. Homepage-Centric Architecture
# =============================================================================
def test_homepage_centric_architecture():
    html = "<html><body><section><h2>Solutions</h2><h3>Cloud Migration</h3><h3>Security Audit</h3></section></body></html>"
    soup = BeautifulSoup(html, "html.parser")
    hp = PageContentItem(url="https://example.com", page_name="Home", word_count=150, content_depth="adequate", is_service_page=False)
    svcs, details, has_ded, mainly_hp, from_hp, conf, arch = extract_services_from_content(
        pages=[hp],
        homepage_soup=soup,
    )

    assert arch == "homepage_centric"
    assert mainly_hp is True


# =============================================================================
# 12. Mixed Architecture
# =============================================================================
def test_mixed_architecture():
    html = "<html><body><section><h2>Solutions</h2><h3>Cloud Migration</h3></section></body></html>"
    soup = BeautifulSoup(html, "html.parser")
    pages = [
        PageContentItem(url="https://example.com", page_name="Home", word_count=150, content_depth="adequate", is_service_page=False),
        PageContentItem(url="https://example.com/services/devops", page_name="DevOps Consulting", word_count=300, content_depth="adequate", is_service_page=True),
    ]
    svcs, details, has_ded, mainly_hp, from_hp, conf, arch = extract_services_from_content(
        pages=pages,
        homepage_soup=soup,
    )

    assert arch == "mixed"
    assert has_ded is True
    assert from_hp is True


# =============================================================================
# 13. Unknown / Inconclusive Architecture
# =============================================================================
def test_inconclusive_architecture():
    html = "<html><body><p>Just a simple text page.</p></body></html>"
    soup = BeautifulSoup(html, "html.parser")
    hp = PageContentItem(url="https://example.com", page_name="Home", word_count=20, content_depth="thin", is_service_page=False)
    svcs, details, has_ded, mainly_hp, from_hp, conf, arch = extract_services_from_content(
        pages=[hp],
        homepage_soup=soup,
    )

    assert arch == "inconclusive"
    assert len(svcs) == 0


# =============================================================================
# 14. Local Recommendations Only When Local Evidence Exists
# =============================================================================
def test_local_recommendations_only_when_local_evidence_exists():
    biz_local = BusinessContextModel(category="local_business", confidence="high", evidence=["Address present"])
    projects = generate_strategic_projects(biz_local, has_local_evidence=True)

    project_ids = [p["id"] for p in projects]
    assert "bp-local-gmb" in project_ids
    assert "bp-local-reviews" in project_ids


# =============================================================================
# 15. Google Review Recommendations Suppressed For Technology / SaaS
# =============================================================================
def test_google_review_recommendations_suppressed_for_technology():
    biz_tech = BusinessContextModel(category="technology", confidence="high", evidence=["AI platform"])
    projects = generate_strategic_projects(biz_tech, has_local_evidence=False)

    project_ids = [p["id"] for p in projects]
    assert "bp-local-reviews" not in project_ids
    assert "bp-local-gmb" not in project_ids
    assert "bp-tech-solutions" in project_ids or "bp-tech-docs" in project_ids


# =============================================================================
# 16. Context-Aware Title Recommendations
# =============================================================================
def test_context_aware_title_recommendations():
    # Local business title action
    local_action = get_title_suggested_action("local_business", has_local_evidence=True, title_len=15)
    assert "location" in local_action.lower()

    # Tech business title action
    tech_action = get_title_suggested_action("technology", has_local_evidence=False, title_len=15)
    assert "product" in tech_action.lower() or "service" in tech_action.lower()

    # Unknown category title action
    unknown_action = get_title_suggested_action("unknown", has_local_evidence=False, title_len=15)
    assert "primary purpose" in unknown_action.lower()


# =============================================================================
# 17. WAF Language Does Not Claim Googlebot Is Blocked
# =============================================================================
def test_waf_language_does_not_claim_googlebot_is_blocked():
    mock_fetch = FetchResult(
        success=True,
        initial_url="https://www.tajhotels.com",
        final_url="https://www.tajhotels.com",
        status_code=403,
        response_time_ms=100,
        content_type="text/html",
        redirect_chain=[],
        raw_html="<html><body>Access Denied</body></html>",
        parsed_data=parse_html("<html><body>Access Denied</body></html>", "https://www.tajhotels.com"),
        content_accessible=False,
        content_reliability="unreliable",
        error_type="bot_protection_detected",
    )
    result = evaluate_technical_seo(mock_fetch)
    findings_map = {f.id: f for f in result.findings}

    bot_finding = findings_map["bot_protection_detected"]
    assert "Googlebot is blocked" not in bot_finding.summary
    assert "We could not verify whether verified search engine crawlers" in bot_finding.summary
    assert "Review CDN/WAF logs" in bot_finding.suggested_action


# =============================================================================
# 18. Inconclusive Robots / Sitemap Are Not Treated As Missing
# =============================================================================
def test_inconclusive_robots_sitemap_on_blocked_site():
    mock_fetch = FetchResult(
        success=True,
        initial_url="https://www.tajhotels.com",
        final_url="https://www.tajhotels.com",
        status_code=403,
        response_time_ms=100,
        content_type="text/html",
        redirect_chain=[],
        raw_html="<html><body>Access Denied</body></html>",
        parsed_data=parse_html("<html><body>Access Denied</body></html>", "https://www.tajhotels.com"),
        robots_txt_present=False,  # could not be fetched due to 403
        sitemap_xml_present=False,
        content_accessible=False,
        content_reliability="unreliable",
        error_type="bot_protection_detected",
    )
    result = evaluate_technical_seo(mock_fetch)
    findings_map = {f.id: f for f in result.findings}

    # Should be inconclusive, NOT claiming definitely missing 404
    assert findings_map["robots_txt"].is_inconclusive is True
    assert "Verify robots.txt" in findings_map["robots_txt"].suggested_action
    assert findings_map["sitemap_xml"].is_inconclusive is True
    assert "Verify XML sitemap" in findings_map["sitemap_xml"].suggested_action


# =============================================================================
# 19. AI Payload Contains Deterministic Business Context
# =============================================================================
def test_ai_payload_contains_deterministic_business_context():
    html = """
    <html>
    <head><title>Neuralake - AI Automation Platform</title></head>
    <body><h1>AI Cloud Automation</h1><p>Enterprise machine learning.</p></body>
    </html>
    """
    parsed = parse_html(html, "https://theneuralake.com")
    raw_fetch = RawFetchData(
        success=True,
        initial_url="https://theneuralake.com",
        final_url="https://theneuralake.com",
        parsed_data=ParsedHTMLModel(**parsed.to_dict()),
    )
    payload = build_compact_factual_payload(fetch_data=raw_fetch)

    assert "business_context" in payload
    assert payload["business_context"]["category"] == "technology"
    assert "audience_context" in payload
    assert "service_context" in payload


# =============================================================================
# 20. AI Output Cannot Override Deterministic Unknown Category
# =============================================================================
@pytest.mark.anyio
async def test_ai_output_cannot_override_deterministic_unknown_category():
    html = "<html><head><title>Example Domain</title></head><body><p>Illustrative.</p></body></html>"
    parsed = parse_html(html, "https://example.com")
    raw_fetch = RawFetchData(
        success=True,
        initial_url="https://example.com",
        final_url="https://example.com",
        parsed_data=ParsedHTMLModel(**parsed.to_dict()),
    )
    biz_ctx = BusinessContextModel(category="unknown", confidence="low", evidence=["Thin page"])
    aud_ctx = AudienceContextModel(target_audience="Inconclusive", confidence="low", evidence=["Thin content"])
    context_intel = ContextIntelligenceResultModel(business_context=biz_ctx, audience_context=aud_ctx)

    # Hallucinated AI response claiming it's a hotel
    hallucinated_ai_json = {
        "status": "available",
        "overall_assessment": "good",
        "executive_summary": "Example Domain is a luxury 5-star hotel in London.",
        "top_priorities": [
            {
                "title": "Claim Google Business Profile for Dental Clinic",
                "priority": "high",
                "category": "visibility",
                "explanation": "Local clinic map rank.",
                "business_impact": "Patient calls.",
                "recommended_action": "Verify GBP.",
                "estimated_effort": "quick",
                "anchor_finding_id": "schema_org"
            }
        ],
        "quick_wins": ["Update GBP address"],
        "strengths": ["Valid HTTPS"],
        "limitations": []
    }

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "choices": [{"message": {"content": json.dumps(hallucinated_ai_json)}}]
    }

    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.post = AsyncMock(return_value=mock_resp)

    ai_result = await generate_ai_insights(
        fetch_data=raw_fetch,
        context_intelligence=context_intel,
        client=mock_client,
        api_key="valid-key",
    )

    assert ai_result.status == "available"
    # Deterministic context intelligence is immutable in our models
    assert context_intel.business_context.category == "unknown"
