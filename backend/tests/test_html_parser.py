import pytest
from app.services.html_parser import parse_html

SAMPLE_CLINIC_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Bright Smile Dental Clinic | Family & Cosmetic Dentistry</title>
    <meta name="description" content="Providing premier dental care, whitening, and Invisalign in San Francisco. Book an appointment today.">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link rel="canonical" href="https://bright-smile-clinic.com/">
    <script type="application/ld+json">
    {
      "@context": "https://schema.org",
      "@type": "MedicalBusiness",
      "name": "Bright Smile Dental Clinic",
      "telephone": "+1-555-234-5678",
      "address": {
        "@type": "PostalAddress",
        "streetAddress": "452 Market St",
        "addressLocality": "San Francisco",
        "addressRegion": "CA"
      }
    }
    </script>
</head>
<body>
    <header>
        <a href="/">Home</a>
        <a href="/services/implants">Dental Implants</a>
        <a href="/about-us">About Our Team</a>
        <a href="/contact-location">Contact</a>
        <a href="/pricing-plans">Pricing</a>
        <a href="https://calendly.com/bright-smile">Book Online</a>
        <a href="tel:+15552345678">Call Us</a>
        <a href="https://wa.me/15552345678">WhatsApp</a>
        <a href="mailto:care@bright-smile-clinic.com">Email Us</a>
    </header>
    <main>
        <h1>Gentle Family and Cosmetic Dentistry in Downtown SF</h1>
        <h2>Our Core Dental Procedures</h2>
        <p>We are a dedicated team of experienced dentists offering modern preventative care, porcelain veneers, root canal treatments, and pediatric services for adults and children.</p>
        
        <h3>State of the Art Technology</h3>
        <p>Our clinic utilizes 3D intraoral scanners and digital low-radiation x-rays to make your visits fast and painless.</p>

        <img src="/images/hero-doctor.jpg" alt="Dr. Jane Smith smiling with patient">
        <img src="/images/clinic-room.jpg" alt="">
        <img src="/images/dental-chair.png">
    </main>
</body>
</html>
"""

SAMPLE_SPA_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>React SPA App</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
</head>
<body>
    <div id="root"></div>
    <noscript>You need to enable JavaScript to run this app.</noscript>
    <script src="/static/bundle.js"></script>
</body>
</html>
"""


def test_parse_html_standard_clinic():
    base_url = "https://bright-smile-clinic.com"
    data = parse_html(SAMPLE_CLINIC_HTML, base_url)

    # Title & Meta
    assert data.title == "Bright Smile Dental Clinic | Family & Cosmetic Dentistry"
    assert data.title_length == 56
    assert "premier dental care" in (data.meta_description or "")
    assert data.canonical_url == "https://bright-smile-clinic.com/"
    assert data.viewport_meta == "width=device-width, initial-scale=1.0"

    # Headings
    assert len(data.h1_tags) == 1
    assert "Gentle Family" in data.h1_tags[0]
    assert len(data.h2_tags) == 1
    assert len(data.h3_tags) == 1

    # Images
    assert data.total_images == 3
    assert data.missing_alt_count == 2  # 1 has empty alt, 1 has missing alt
    assert len(data.images_missing_alt) == 2

    # Structured Data
    assert "MedicalBusiness" in data.structured_data_types
    assert len(data.structured_data_blocks) == 1
    assert data.structured_data_blocks[0]["name"] == "Bright Smile Dental Clinic"

    # CTAs
    assert "+15552345678" in data.detected_ctas["phone"]
    assert "care@bright-smile-clinic.com" in data.detected_ctas["email"]
    assert "https://wa.me/15552345678" in data.detected_ctas["whatsapp"]
    assert "https://calendly.com/bright-smile" in data.detected_ctas["booking_links"]

    # Key Subpages
    assert "https://bright-smile-clinic.com/services/implants" in data.key_subpages["services"]
    assert "https://bright-smile-clinic.com/about-us" in data.key_subpages["about"]
    assert "https://bright-smile-clinic.com/contact-location" in data.key_subpages["contact"]
    assert "https://bright-smile-clinic.com/pricing-plans" in data.key_subpages["pricing"]

    # SPA detection
    assert data.is_javascript_heavy is False


def test_parse_html_spa_detection():
    base_url = "https://react-spa-example.com"
    data = parse_html(SAMPLE_SPA_HTML, base_url)

    assert data.is_javascript_heavy is True
    assert data.javascript_rendering_note is not None
    assert "client-side JavaScript" in data.javascript_rendering_note
    assert data.visible_word_count < 20
