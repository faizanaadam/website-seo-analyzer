import pytest
from app.utils.url_helpers import normalize_url, extract_domain, is_same_domain, resolve_url


def test_normalize_url_basic():
    assert normalize_url("example.com") == "https://example.com"
    assert normalize_url("http://example.com") == "http://example.com"
    assert normalize_url("HTTPS://EXAMPLE.COM/") == "https://example.com"
    assert normalize_url("  https://clinic.com/about/  ") == "https://clinic.com/about/"


def test_normalize_url_with_query_and_fragment():
    # Fragments are stripped, queries preserved
    assert normalize_url("https://example.com/page?ref=123#section") == "https://example.com/page?ref=123"


def test_normalize_url_invalid():
    with pytest.raises(ValueError):
        normalize_url("")

    with pytest.raises(ValueError):
        normalize_url("ftp://example.com")

    with pytest.raises(ValueError):
        normalize_url("just-a-word-with-no-dot")


def test_extract_domain():
    assert extract_domain("https://www.example.com/services") == "www.example.com"
    assert extract_domain("http://clinic.org:8000") == "clinic.org"
    assert extract_domain("invalid") == ""


def test_is_same_domain():
    assert is_same_domain("https://example.com", "https://example.com/about") is True
    assert is_same_domain("https://example.com", "https://www.example.com/contact") is True
    assert is_same_domain("https://www.example.com", "https://example.com/pricing") is True
    assert is_same_domain("https://example.com", "https://otherclinic.com") is False


def test_resolve_url():
    base = "https://example.com/clinic/"
    assert resolve_url(base, "/about") == "https://example.com/about"
    assert resolve_url(base, "services/whitening") == "https://example.com/clinic/services/whitening"
    assert resolve_url(base, "https://google.com") == "https://google.com"

    # Filter out non-http schemes and empty fragments
    assert resolve_url(base, "tel:+15552345678") is None
    assert resolve_url(base, "mailto:info@example.com") is None
    assert resolve_url(base, "javascript:void(0)") is None
    assert resolve_url(base, "#top") is None
