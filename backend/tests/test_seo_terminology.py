import pytest
from app.services.fetcher import FetchResult
from app.services.html_parser import parse_html
from app.services.technical_seo import evaluate_technical_seo
from app.services.recommendation_engine import generate_strategic_projects
from app.models import BusinessContextModel

FORBIDDEN_PHRASES = [
    "duplicate content penalty",
    "duplicate content penalties",
    "guaranteed ranking",
    "guaranteed traffic",
    "guaranteed index",
    "google penalty",
    "google penalties",
]


def test_canonical_wording_accuracy():
    """Verify that canonical tag evaluation uses accurate wording and never claims penalties."""
    html = "<html><head><title>Test Page</title></head><body><h1>Hello</h1></body></html>"
    parsed = parse_html(html, "https://example.com")
    fetch_res = FetchResult(
        success=True,
        initial_url="https://example.com",
        final_url="https://example.com",
        status_code=200,
        response_time_ms=100,
        parsed_data=parsed,
    )
    result = evaluate_technical_seo(fetch_res)
    findings_map = {f.id: f for f in result.findings}

    canonical = findings_map["canonical_tag"]
    assert "preferred authoritative URL" in canonical.why_it_matters or "authoritative URL" in canonical.why_it_matters
    for phrase in FORBIDDEN_PHRASES:
        assert phrase not in canonical.why_it_matters.lower()
        assert phrase not in canonical.suggested_action.lower()


def test_all_technical_seo_findings_avoid_exaggerated_claims():
    """Verify that all deterministic technical SEO findings avoid exaggerated penalty/guarantee claims."""
    html = """
    <html>
        <head>
            <title>A</title>
        </head>
        <body>
            <img src="/broken.jpg">
        </body>
    </html>
    """
    parsed = parse_html(html, "https://example.com")
    fetch_res = FetchResult(
        success=True,
        initial_url="https://example.com",
        final_url="https://example.com",
        status_code=200,
        response_time_ms=100,
        parsed_data=parsed,
    )
    result = evaluate_technical_seo(fetch_res)

    for finding in result.findings:
        text_corpus = f"{finding.title} {finding.summary} {finding.why_it_matters} {finding.suggested_action}".lower()
        for phrase in FORBIDDEN_PHRASES:
            assert phrase not in text_corpus, f"Forbidden phrase '{phrase}' found in finding '{finding.id}'"


def test_strategic_projects_avoid_exaggerated_claims():
    """Verify that generated strategic projects do not contain forbidden exaggerated claims."""
    categories = ["technology", "saas", "local_business", "healthcare", "hospitality", "ecommerce", "unknown"]
    for cat in categories:
        biz_ctx = BusinessContextModel(category=cat, confidence="high", evidence=["Test"])
        projects = generate_strategic_projects(biz_ctx, has_local_evidence=(cat in ("local_business", "healthcare")))
        for p in projects:
            text = f"{p['title']} {p['why']}".lower()
            for phrase in FORBIDDEN_PHRASES:
                assert phrase not in text, f"Forbidden phrase '{phrase}' found in project '{p['id']}'"
