import re
from urllib.parse import urlparse, urljoin, urldefrag
from typing import Optional


def normalize_url(raw_url: str) -> str:
    """
    Normalizes a user-supplied URL.
    - Strips leading/trailing whitespace
    - Adds https:// scheme if missing
    - Validates domain format
    - Lowercases scheme and hostname
    - Strips trailing slash on root paths (e.g. https://example.com/ -> https://example.com)
    """
    if not raw_url:
        raise ValueError("URL cannot be empty")

    cleaned = raw_url.strip()
    # Remove surrounding quotes or backticks if pasted by mistake
    cleaned = cleaned.strip("\"'`<>")

    # If scheme missing, prepend https://
    if not re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*://", cleaned):
        cleaned = f"https://{cleaned}"

    parsed = urlparse(cleaned)
    scheme = parsed.scheme.lower()
    if scheme not in ("http", "https"):
        raise ValueError(f"Unsupported URL scheme '{scheme}'. Only http and https are supported.")

    hostname = (parsed.hostname or "").lower().strip()
    if not hostname:
        raise ValueError("Invalid URL: missing hostname or domain")

    # Validate that hostname contains at least one dot or is localhost
    if "." not in hostname and hostname != "localhost":
        raise ValueError(f"Invalid domain format '{hostname}'")

    # Reconstruct clean URL
    port_part = f":{parsed.port}" if parsed.port and parsed.port not in (80, 443) else ""
    path = parsed.path or ""
    # Normalize empty or solitary slash path
    if path == "/":
        path = ""

    query_part = f"?{parsed.query}" if parsed.query else ""
    # We strip fragments for crawling targets
    normalized = f"{scheme}://{hostname}{port_part}{path}{query_part}"
    return normalized


def extract_domain(url: str) -> str:
    """Extracts lowercase hostname without port or scheme."""
    try:
        parsed = urlparse(url)
        return (parsed.hostname or "").lower()
    except Exception:
        return ""


def is_same_domain(base_url: str, target_url: str) -> bool:
    """
    Checks if target_url belongs to the same domain/host as base_url.
    Handles www vs non-www subdomains seamlessly (e.g. example.com vs www.example.com).
    """
    base_host = extract_domain(base_url)
    target_host = extract_domain(target_url)

    if not base_host or not target_host:
        return False

    if base_host == target_host:
        return True

    # Strip leading 'www.'
    base_root = re.sub(r"^www\.", "", base_host)
    target_root = re.sub(r"^www\.", "", target_host)
    return base_root == target_root


def resolve_url(base_url: str, link: str) -> Optional[str]:
    """
    Resolves relative or protocol-relative links against a base URL.
    Strips fragment identifiers (#...).
    Returns None for mailto:, tel:, javascript:, whatsapp:, etc.
    """
    if not link:
        return None

    cleaned_link = link.strip()
    if not cleaned_link:
        return None

    # Filter out non-HTTP schemes
    if re.match(r"^(mailto|tel|javascript|data|whatsapp|sms|callto|viber|tg):", cleaned_link, re.IGNORECASE):
        return None

    # Remove fragment
    defragged, _ = urldefrag(cleaned_link)
    if not defragged:
        return None

    try:
        resolved = urljoin(base_url, defragged)
        parsed = urlparse(resolved)
        if parsed.scheme.lower() in ("http", "https") and parsed.hostname:
            return resolved
    except Exception:
        pass

    return None
