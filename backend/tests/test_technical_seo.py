import pytest
from app.services.fetcher import FetchResult
from app.services.html_parser import parse_html
from app.services.technical_seo import evaluate_technical_seo, detect_observable_category


def create_mock_fetch_result(
    html: str,
    final_url: str = "https://example.com",
    robots_present: bool = True,
    sitemap_present: bool = True,
) -> FetchResult:
    parsed = parse_html(html, final_url)
    return FetchResult(
        success=True,
        initial_url=final_url,
        final_url=final_url,
        status_code=200,
        response_time_ms=150,
        content_type="text/html",
        parsed_data=parsed,
        robots_txt_present=robots_present,
        sitemap_xml_present=sitemap_present,
    )


# 1. Page Title Rule Tests
def test_title_optimal():
    html = '<html><head><title>Bright Smile Dental Clinic | San Francisco</title></head><body><h1>Hi</h1></body></html>'
    res = evaluate_technical_seo(create_mock_fetch_result(html))
    finding = next(f for f in res.findings if f.id == "page_title")
    assert finding.status == "pass"


def test_title_too_short():
    html = '<html><head><title>Clinic</title></head><body><h1>Hi</h1></body></html>'
    res = evaluate_technical_seo(create_mock_fetch_result(html))
    finding = next(f for f in res.findings if f.id == "page_title")
    assert finding.status == "needs_attention"
    assert "too short" in finding.summary.lower()


def test_title_too_long():
    long_title = "A" * 75
    html = f'<html><head><title>{long_title}</title></head><body><h1>Hi</h1></body></html>'
    res = evaluate_technical_seo(create_mock_fetch_result(html))
    finding = next(f for f in res.findings if f.id == "page_title")
    assert finding.status == "needs_attention"
    assert "too long" in finding.summary.lower()


def test_title_missing():
    html = '<html><head></head><body><h1>Hi</h1></body></html>'
    res = evaluate_technical_seo(create_mock_fetch_result(html))
    finding = next(f for f in res.findings if f.id == "page_title")
    assert finding.status == "fail"


# 2. Meta Description Rule Tests
def test_meta_description_optimal():
    desc = "Providing gentle family and cosmetic dental care in downtown San Francisco. Schedule your online appointment with our expert dental team today."
    html = f'<html><head><meta name="description" content="{desc}"><title>Title</title></head><body><h1>Hi</h1></body></html>'
    res = evaluate_technical_seo(create_mock_fetch_result(html))
    finding = next(f for f in res.findings if f.id == "meta_description")
    assert finding.status == "pass"


def test_meta_description_missing():
    html = '<html><head><title>Title</title></head><body><h1>Hi</h1></body></html>'
    res = evaluate_technical_seo(create_mock_fetch_result(html))
    finding = next(f for f in res.findings if f.id == "meta_description")
    assert finding.status == "needs_attention"
    assert "missing" in finding.summary.lower()


def test_meta_description_too_short():
    html = '<html><head><meta name="description" content="We are a dentist."><title>Title</title></head><body><h1>Hi</h1></body></html>'
    res = evaluate_technical_seo(create_mock_fetch_result(html))
    finding = next(f for f in res.findings if f.id == "meta_description")
    assert finding.status == "needs_attention"
    assert "short" in finding.summary.lower()


# 3. Heading Structure Tests
def test_heading_structure_single_h1_with_h2():
    html = '<html><body><h1>Primary Heading</h1><h2>Service 1</h2><h2>Service 2</h2></body></html>'
    res = evaluate_technical_seo(create_mock_fetch_result(html))
    finding = next(f for f in res.findings if f.id == "heading_structure")
    assert finding.status == "pass"


def test_heading_structure_missing_h1():
    html = '<html><body><h2>Only Subheading</h2></body></html>'
    res = evaluate_technical_seo(create_mock_fetch_result(html))
    finding = next(f for f in res.findings if f.id == "heading_structure")
    assert finding.status == "fail"


def test_heading_structure_multiple_h1s():
    html = '<html><body><h1>Heading One</h1><h1>Heading Two</h1></body></html>'
    res = evaluate_technical_seo(create_mock_fetch_result(html))
    finding = next(f for f in res.findings if f.id == "heading_structure")
    assert finding.status == "needs_attention"
    assert "multiple" in finding.summary.lower()


# 4. Image Alt Text Tests
def test_image_alt_text_all_present():
    html = '<html><body><img src="/img1.jpg" alt="Doctor smiling"><img src="/img2.jpg" alt="Clinic lobby"></body></html>'
    res = evaluate_technical_seo(create_mock_fetch_result(html))
    finding = next(f for f in res.findings if f.id == "image_alt_text")
    assert finding.status == "pass"


def test_image_alt_text_missing_images():
    html = '<html><body><img src="/img1.jpg" alt="Doctor"><img src="/img2.jpg"><img src="/img3.jpg" alt=""></body></html>'
    res = evaluate_technical_seo(create_mock_fetch_result(html))
    finding = next(f for f in res.findings if f.id == "image_alt_text")
    assert finding.status in ("needs_attention", "fail")
    assert len(finding.affected_urls) > 0


# 5 & 6. Robots.txt and Sitemap.xml Tests
def test_robots_and_sitemap_present():
    html = '<html><body><h1>Hi</h1></body></html>'
    res = evaluate_technical_seo(create_mock_fetch_result(html, robots_present=True, sitemap_present=True))
    assert next(f for f in res.findings if f.id == "robots_txt").status == "pass"
    assert next(f for f in res.findings if f.id == "sitemap_xml").status == "pass"


def test_robots_and_sitemap_missing():
    html = '<html><body><h1>Hi</h1></body></html>'
    res = evaluate_technical_seo(create_mock_fetch_result(html, robots_present=False, sitemap_present=False))
    assert next(f for f in res.findings if f.id == "robots_txt").status == "needs_attention"
    assert next(f for f in res.findings if f.id == "sitemap_xml").status == "needs_attention"


# 7. HTTPS Security Tests
def test_https_security_pass():
    html = '<html><body><h1>Hi</h1></body></html>'
    res = evaluate_technical_seo(create_mock_fetch_result(html, final_url="https://secure-clinic.com"))
    assert next(f for f in res.findings if f.id == "https_security").status == "pass"


def test_https_security_fail():
    html = '<html><body><h1>Hi</h1></body></html>'
    res = evaluate_technical_seo(create_mock_fetch_result(html, final_url="http://insecure-clinic.com"))
    assert next(f for f in res.findings if f.id == "https_security").status == "fail"


# 8. Canonical Tag Tests
def test_canonical_matching():
    html = '<html><head><link rel="canonical" href="https://example.com/page"></head><body><h1>Hi</h1></body></html>'
    res = evaluate_technical_seo(create_mock_fetch_result(html, final_url="https://example.com/page"))
    finding = next(f for f in res.findings if f.id == "canonical_tag")
    assert finding.status == "pass"


def test_canonical_mismatch():
    html = '<html><head><link rel="canonical" href="http://otherdomain.com/other"></head><body><h1>Hi</h1></body></html>'
    res = evaluate_technical_seo(create_mock_fetch_result(html, final_url="https://example.com/page"))
    finding = next(f for f in res.findings if f.id == "canonical_tag")
    assert finding.status == "needs_attention"


# 9. Viewport Tag Tests
def test_viewport_present():
    html = '<html><head><meta name="viewport" content="width=device-width, initial-scale=1.0"></head><body></body></html>'
    res = evaluate_technical_seo(create_mock_fetch_result(html))
    finding = next(f for f in res.findings if f.id == "mobile_viewport")
    assert finding.status == "pass"


def test_viewport_missing():
    html = '<html><head></head><body></body></html>'
    res = evaluate_technical_seo(create_mock_fetch_result(html))
    finding = next(f for f in res.findings if f.id == "mobile_viewport")
    assert finding.status == "fail"


# 10. Context-Aware Structured Data Tests
def test_structured_data_healthcare_with_dentist():
    html = """
    <html><head>
    <title>Family Dentist & Teeth Whitening Clinic</title>
    <script type="application/ld+json">
    {"@context": "https://schema.org", "@type": "Dentist", "name": "SF Smiles"}
    </script>
    </head><body><h1>Gentle Pediatric Dental Care</h1></body></html>
    """
    res = evaluate_technical_seo(create_mock_fetch_result(html))
    assert res.inferred_category == "healthcare"
    finding = next(f for f in res.findings if f.id == "structured_data")
    assert finding.status == "pass"
    assert "Dentist" in finding.summary


def test_structured_data_healthcare_with_generic_org_needs_attention():
    html = """
    <html><head>
    <title>Dr. Smith Dental Surgery Clinic</title>
    <script type="application/ld+json">
    {"@context": "https://schema.org", "@type": "Organization", "name": "Smith Corp"}
    </script>
    </head><body><h1>Comprehensive Dental Health</h1></body></html>
    """
    res = evaluate_technical_seo(create_mock_fetch_result(html))
    assert res.inferred_category == "healthcare"
    finding = next(f for f in res.findings if f.id == "structured_data")
    assert finding.status == "needs_attention"
    assert "MedicalBusiness" in finding.suggested_action


def test_structured_data_healthcare_missing_fail():
    html = """
    <html><head>
    <title>Metro Dental Care Clinic</title>
    </head><body><h1>Dental Implants and Orthodontics</h1></body></html>
    """
    res = evaluate_technical_seo(create_mock_fetch_result(html))
    assert res.inferred_category == "healthcare"
    finding = next(f for f in res.findings if f.id == "structured_data")
    assert finding.status == "fail"


def test_structured_data_local_service_auto_repair():
    html = """
    <html><head>
    <title>Apex Auto Repair & Mechanic Garage</title>
    <script type="application/ld+json">
    {"@context": "https://schema.org", "@type": "AutoRepair", "name": "Apex Auto"}
    </script>
    </head><body><h1>Brake Service and Transmission Repair</h1></body></html>
    """
    res = evaluate_technical_seo(create_mock_fetch_result(html))
    assert res.inferred_category == "local_service"
    finding = next(f for f in res.findings if f.id == "structured_data")
    assert finding.status == "pass"


def test_structured_data_general_saas_with_organization():
    html = """
    <html><head>
    <title>CloudFlow SaaS Platform | Enterprise Data</title>
    <script type="application/ld+json">
    {"@context": "https://schema.org", "@type": "Organization", "name": "CloudFlow Inc"}
    </script>
    </head><body><h1>Cloud APIs and Developer Tools</h1></body></html>
    """
    res = evaluate_technical_seo(create_mock_fetch_result(html))
    assert res.inferred_category == "general"
    finding = next(f for f in res.findings if f.id == "structured_data")
    assert finding.status == "pass"


def test_overall_health_score_calculation():
    html = """
    <html><head>
    <title>Comprehensive Healthcare Clinic | San Francisco</title>
    <meta name="description" content="Providing expert healthcare, physician treatments, and doctor checkups in downtown San Francisco. Book your visit online today.">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link rel="canonical" href="https://example.com/">
    <script type="application/ld+json">
    {"@context": "https://schema.org", "@type": "MedicalBusiness", "name": "SF Health"}
    </script>
    </head>
    <body>
        <h1>Premier Health and Wellness Clinic</h1>
        <h2>Our Doctor Services</h2>
        <img src="/hero.jpg" alt="Doctor with patient">
    </body></html>
    """
    res = evaluate_technical_seo(create_mock_fetch_result(html, final_url="https://example.com/"))
    assert res.summary.passed_count == 10
    assert res.summary.issues_count == 0
    assert res.summary.needs_attention_count == 0
    assert res.summary.health_score == 100
