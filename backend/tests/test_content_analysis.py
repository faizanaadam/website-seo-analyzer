import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from bs4 import BeautifulSoup
import httpx

from app.services.fetcher import FetchResult
from app.services.html_parser import parse_html
from app.services.content_analysis import (
    classify_content_depth,
    extract_visible_words,
    derive_page_name,
    is_service_page_check,
    prioritize_subpages,
    extract_ctas_and_contact,
    extract_services_from_content,
    analyze_content,
)
from app.models import PageContentItem


def test_classify_content_depth():
    """Verify content depth classification based on word counts."""
    assert classify_content_depth(0) == "Thin"
    assert classify_content_depth(100) == "Thin"
    assert classify_content_depth(249) == "Thin"
    assert classify_content_depth(250) == "Moderate"
    assert classify_content_depth(500) == "Moderate"
    assert classify_content_depth(800) == "Moderate"
    assert classify_content_depth(801) == "Comprehensive"
    assert classify_content_depth(2000) == "Comprehensive"


def test_extract_visible_words():
    """Verify visible words extraction removes script, style, nav, footer."""
    html = """
    <html>
        <head><title>Test Page</title><style>.hidden { display: none; }</style></head>
        <body>
            <header><p>Header Navigation Link One Two</p></header>
            <nav><a href="/home">Home</a><a href="/about">About</a></nav>
            <main>
                <h1>Main Heading</h1>
                <p>This is a paragraph with visible content words for analysis.</p>
            </main>
            <footer><p>Copyright 2026 Dental Practice All Rights Reserved</p></footer>
            <script>console.log('invisible script code');</script>
        </body>
    </html>
    """
    soup = BeautifulSoup(html, "html.parser")
    word_count, snippet = extract_visible_words(soup)

    assert word_count > 5
    assert "invisible script code" not in snippet
    assert "Main Heading" in snippet or "Main" in snippet


def test_derive_page_name():
    """Verify derivation of friendly page names."""
    # From title
    assert derive_page_name("Cosmetic Dentistry | Bright Smiles Clinic", ["Our Services"], "https://example.com/cosmetic") == "Cosmetic Dentistry"
    assert derive_page_name("About Us - Dr. Smith DDS", ["Meet the Team"], "https://example.com/about") == "About Us"

    # From H1 fallback when title is missing or generic
    assert derive_page_name(None, ["Teeth Whitening Treatments"], "https://example.com/services/teeth-whitening") == "Teeth Whitening Treatments"

    # From URL slug fallback
    assert derive_page_name(None, [], "https://example.com/root-canal-therapy") == "Root Canal Therapy"
    assert derive_page_name(None, [], "https://example.com/") == "Homepage"


def test_is_service_page_check():
    """Verify service page detection heuristics."""
    # Dedicated service URLs
    assert is_service_page_check("https://example.com/services/general-dentistry", "General Dentistry", ["General Dentistry"], []) is True
    assert is_service_page_check("https://example.com/treatments/invisalign", "Invisalign", ["Invisalign"], []) is True
    assert is_service_page_check("https://example.com/services", "Our Services", ["Dental Services"], []) is True

    # Non-service pages
    assert is_service_page_check("https://example.com/about-us", "About Our Team", ["About Us"], []) is False
    assert is_service_page_check("https://example.com/contact", "Contact Us", ["Get In Touch"], []) is False
    assert is_service_page_check("https://example.com/book-now", "Book Appointment", ["Book Now"], []) is False


def test_prioritize_subpages_ranking_and_limits():
    """Verify prioritization ordering and strict crawl limit (max 5)."""
    links = [
        "https://example.com/blog/article-1",
        "https://example.com/about-us",
        "https://example.com/pricing",
        "https://example.com/services/dental-implants",
        "https://example.com/services/teeth-whitening",
        "https://example.com/services",
        "https://example.com/contact-us",
        "https://example.com/book-appointment",
        "https://example.com/privacy-policy",  # ignored pattern
        "https://external-domain.com/other",    # external
    ]

    prioritized = prioritize_subpages(
        internal_links=links,
        base_url="https://example.com",
        limit=5,
    )

    # Must not exceed limit of 5
    assert len(prioritized) <= 5

    # Specific services must have top priority
    assert "https://example.com/services/dental-implants" in prioritized
    assert "https://example.com/services/teeth-whitening" in prioritized
    assert "https://example.com/services" in prioritized

    # Ignored and external links must not be present
    assert "https://example.com/privacy-policy" not in prioritized
    assert "https://external-domain.com/other" not in prioritized


def test_extract_ctas_and_contact_detection():
    """Verify phone, email, whatsapp, booking links, address, and hours detection."""
    html = """
    <html>
        <head>
            <script type="application/ld+json">
            {
                "@context": "https://schema.org",
                "@type": "Dentist",
                "name": "Bright Smile Clinic",
                "telephone": "+1 555-0199",
                "email": "info@brightsmile.com",
                "address": {
                    "@type": "PostalAddress",
                    "streetAddress": "123 Dental Way",
                    "addressLocality": "Austin",
                    "addressRegion": "TX",
                    "postalCode": "78701",
                    "addressCountry": "US"
                },
                "openingHours": [
                    "Mo-Fr 08:00-17:00",
                    "Sa 09:00-13:00"
                ]
            }
            </script>
        </head>
        <body>
            <a href="tel:+15550199">Call Us</a>
            <a href="mailto:appointments@brightsmile.com">Email Us</a>
            <a href="https://wa.me/15550199">Chat on WhatsApp</a>
            <a href="https://calendly.com/brightsmile/consultation">Book via Calendly</a>
            <a href="https://acuityscheduling.com/schedule.php?owner=12345">Book via Acuity</a>
        </body>
    </html>
    """
    soup = BeautifulSoup(html, "html.parser")
    data = extract_ctas_and_contact(soup, "https://brightsmile.com", "https://brightsmile.com")

    # Phones
    assert "+15550199" in data["phones"] or "+1 555-0199" in data["phones"]

    # Emails
    assert "appointments@brightsmile.com" in data["emails"]
    assert "info@brightsmile.com" in data["emails"]

    # WhatsApp
    assert any("wa.me" in w for w in data["whatsapp"])

    # Booking links & providers
    assert any("calendly.com" in b for b in data["booking_links"])
    assert any("acuityscheduling.com" in b for b in data["booking_links"])
    assert "Calendly" in data["booking_providers"]
    assert "Acuity Scheduling" in data["booking_providers"]

    # Address & Hours
    assert data["address"] is not None
    assert "123 Dental Way" in data["address"]
    assert "Austin" in data["address"]
    assert data["opening_hours"] is not None
    assert len(data["opening_hours"]) == 2


def test_missing_contact_info_returns_null_and_no_hallucination():
    """Verify that absent contact information returns None/empty without fabricating data."""
    html = """
    <html>
        <body>
            <h1>Minimalist Modern Design</h1>
            <p>Welcome to our artistic showcase. We create modern visual experiences.</p>
        </body>
    </html>
    """
    soup = BeautifulSoup(html, "html.parser")
    data = extract_ctas_and_contact(soup, "https://minimalist.com", "https://minimalist.com")

    assert data["phones"] == []
    assert data["emails"] == []
    assert data["whatsapp"] == []
    assert data["booking_links"] == []
    assert data["booking_providers"] == []
    assert data["address"] is None
    assert data["opening_hours"] is None


def test_extract_services_and_structure():
    """Verify dedicated service pages vs homepage-only service detection."""
    pages = [
        PageContentItem(
            url="https://clinic.com",
            page_name="Homepage",
            word_count=500,
            content_depth="Moderate",
            headings=["Welcome to Clinic", "Our Services"],
            is_service_page=False,
        ),
        PageContentItem(
            url="https://clinic.com/services/teeth-whitening",
            page_name="Teeth Whitening",
            word_count=600,
            content_depth="Moderate",
            headings=["Professional Teeth Whitening", "Laser Whitening Options"],
            is_service_page=True,
        ),
        PageContentItem(
            url="https://clinic.com/services/dental-implants",
            page_name="Dental Implants",
            word_count=900,
            content_depth="Comprehensive",
            headings=["Dental Implants Solutions", "Single Tooth Replacement"],
            is_service_page=True,
        ),
    ]

    homepage_soup = BeautifulSoup("<h1>Clinic</h1>", "html.parser")
    svcs, details, has_dedicated, mainly_homepage, from_homepage, confidence, architecture = extract_services_from_content(pages, homepage_soup)

    assert has_dedicated is True
    assert mainly_homepage is False
    assert architecture == "dedicated_multi_page"
    assert "Teeth Whitening" in svcs
    assert "Dental Implants" in svcs
    assert len(details) >= 2


@pytest.mark.anyio
async def test_full_content_analysis_pipeline():
    """Verify end-to-end analyze_content with mock subpage responses."""
    hp_html = """
    <html>
        <head><title>Apex Auto Repair | Austin TX</title></head>
        <body>
            <h1>Apex Auto Repair</h1>
            <p>We provide complete auto maintenance and repair services across Austin.</p>
            <a href="/services/brake-repair">Brake Repair Services</a>
            <a href="/contact">Contact Our Garage</a>
            <a href="tel:5125550144">512-555-0144</a>
        </body>
    </html>
    """
    hp_parsed = parse_html(hp_html, "https://apexautorepair.com")
    hp_fetch = FetchResult(
        success=True,
        initial_url="https://apexautorepair.com",
        final_url="https://apexautorepair.com",
        status_code=200,
        raw_html=hp_html,
        parsed_data=hp_parsed,
    )

    subpage_brake_html = """
    <html>
        <head><title>Brake Repair & Replacement | Apex Auto Repair</title></head>
        <body>
            <h1>Brake Repair & Replacement</h1>
            <p>Comprehensive brake pad replacement, rotor resurfacing, and brake fluid flushes.</p>
            <a href="mailto:service@apexauto.com">service@apexauto.com</a>
        </body>
    </html>
    """

    mock_client = AsyncMock(spec=httpx.AsyncClient)

    def mock_get_side_effect(url, **kwargs):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        if "brake-repair" in str(url):
            mock_resp.text = subpage_brake_html
        else:
            mock_resp.text = "<html><body><h1>Page</h1><p>Some content</p></body></html>"
        return mock_resp

    mock_client.get = AsyncMock(side_effect=mock_get_side_effect)

    result = await analyze_content(hp_fetch, client=mock_client)

    assert result.total_pages_analyzed >= 1
    assert result.homepage_word_count > 0
    assert "5125550144" in result.contact_info.phones or "512-555-0144" in result.contact_info.phones
    assert result.services_structure is not None
    assert result.summary != ""
