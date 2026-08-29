import json
import re
from typing import List, Dict, Any, Optional
from bs4 import BeautifulSoup
from app.utils.url_helpers import resolve_url, is_same_domain


class ParsedHTMLData:
    def __init__(
        self,
        title: Optional[str],
        title_length: int,
        meta_description: Optional[str],
        meta_description_length: int,
        canonical_url: Optional[str],
        viewport_meta: Optional[str],
        h1_tags: List[str],
        h2_tags: List[str],
        h3_tags: List[str],
        total_images: int,
        images_missing_alt: List[Dict[str, str]],
        missing_alt_count: int,
        structured_data_types: List[str],
        structured_data_blocks: List[Dict[str, Any]],
        internal_links: List[str],
        key_subpages: Dict[str, List[str]],
        visible_word_count: int,
        visible_text_snippet: str,
        is_javascript_heavy: bool,
        javascript_rendering_note: Optional[str],
        detected_ctas: Dict[str, List[str]],
    ):
        self.title = title
        self.title_length = title_length
        self.meta_description = meta_description
        self.meta_description_length = meta_description_length
        self.canonical_url = canonical_url
        self.viewport_meta = viewport_meta
        self.h1_tags = h1_tags
        self.h2_tags = h2_tags
        self.h3_tags = h3_tags
        self.total_images = total_images
        self.images_missing_alt = images_missing_alt
        self.missing_alt_count = missing_alt_count
        self.structured_data_types = structured_data_types
        self.structured_data_blocks = structured_data_blocks
        self.internal_links = internal_links
        self.key_subpages = key_subpages
        self.visible_word_count = visible_word_count
        self.visible_text_snippet = visible_text_snippet
        self.is_javascript_heavy = is_javascript_heavy
        self.javascript_rendering_note = javascript_rendering_note
        self.detected_ctas = detected_ctas

    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "title_length": self.title_length,
            "meta_description": self.meta_description,
            "meta_description_length": self.meta_description_length,
            "canonical_url": self.canonical_url,
            "viewport_meta": self.viewport_meta,
            "h1_tags": self.h1_tags,
            "h1_count": len(self.h1_tags),
            "h2_tags": self.h2_tags,
            "h2_count": len(self.h2_tags),
            "h3_tags": self.h3_tags,
            "h3_count": len(self.h3_tags),
            "total_images": self.total_images,
            "missing_alt_count": self.missing_alt_count,
            "images_missing_alt": self.images_missing_alt,
            "structured_data_types": self.structured_data_types,
            "structured_data_blocks": self.structured_data_blocks,
            "internal_links_count": len(self.internal_links),
            "internal_links": self.internal_links[:30],  # cap list for cleanliness
            "key_subpages": self.key_subpages,
            "visible_word_count": self.visible_word_count,
            "visible_text_snippet": self.visible_text_snippet,
            "is_javascript_heavy": self.is_javascript_heavy,
            "javascript_rendering_note": self.javascript_rendering_note,
            "detected_ctas": self.detected_ctas,
        }


def parse_html(html_content: str, base_url: str) -> ParsedHTMLData:
    """
    Parses HTML content using BeautifulSoup and extracts structured SEO, content, and CTA data.
    """
    soup = BeautifulSoup(html_content, "html.parser")

    # 1. Page Title
    title_tag = soup.find("title")
    title = title_tag.get_text().strip() if title_tag else None
    title_length = len(title) if title else 0

    # 2. Meta Description (check standard name="description" and fallback to og:description)
    meta_desc_tag = soup.find("meta", attrs={"name": re.compile(r"^description$", re.I)})
    if not meta_desc_tag:
        meta_desc_tag = soup.find("meta", attrs={"property": re.compile(r"^og:description$", re.I)})
    meta_description = meta_desc_tag.get("content", "").strip() if meta_desc_tag else None
    meta_description_length = len(meta_description) if meta_description else 0

    # 3. Canonical Tag
    canonical_tag = soup.find("link", attrs={"rel": re.compile(r"^canonical$", re.I)})
    canonical_url = canonical_tag.get("href", "").strip() if canonical_tag else None

    # 4. Viewport Meta Tag
    viewport_tag = soup.find("meta", attrs={"name": re.compile(r"^viewport$", re.I)})
    viewport_meta = viewport_tag.get("content", "").strip() if viewport_tag else None

    # 5. Headings
    h1_tags = [h.get_text().strip() for h in soup.find_all("h1") if h.get_text().strip()]
    h2_tags = [h.get_text().strip() for h in soup.find_all("h2") if h.get_text().strip()]
    h3_tags = [h.get_text().strip() for h in soup.find_all("h3") if h.get_text().strip()]

    # 6. Images & Alt text
    img_tags = soup.find_all("img")
    total_images = len(img_tags)
    images_missing_alt: List[Dict[str, str]] = []

    for img in img_tags:
        src = img.get("src", "").strip()
        alt = img.get("alt")
        # An image is missing alt text if the attribute is omitted or is pure whitespace
        if alt is None or not alt.strip():
            resolved_src = resolve_url(base_url, src) or src
            images_missing_alt.append({
                "src": resolved_src,
                "raw_src": src,
            })

    missing_alt_count = len(images_missing_alt)

    # 7. Structured Data (JSON-LD)
    structured_data_types: List[str] = []
    structured_data_blocks: List[Dict[str, Any]] = []

    for script in soup.find_all("script", attrs={"type": "application/ld+json"}):
        raw_json = script.string or script.get_text()
        if raw_json:
            try:
                parsed_json = json.loads(raw_json.strip())
                structured_data_blocks.append(parsed_json)

                # Extract @type definitions
                def extract_types(data: Any):
                    if isinstance(data, dict):
                        if "@type" in data:
                            t = data["@type"]
                            if isinstance(t, list):
                                structured_data_types.extend(t)
                            elif isinstance(t, str):
                                structured_data_types.append(t)
                        if "@graph" in data and isinstance(data["@graph"], list):
                            for item in data["@graph"]:
                                extract_types(item)
                    elif isinstance(data, list):
                        for item in data:
                            extract_types(item)

                extract_types(parsed_json)
            except Exception:
                # Malformed JSON-LD script block
                pass

    # Deduplicate structured data types preserving order
    unique_schema_types = list(dict.fromkeys(structured_data_types))

    # 8. Internal Links & Key Subpage Discovery
    discovered_internal_links: List[str] = []
    seen_links = set()

    key_subpages: Dict[str, List[str]] = {
        "services": [],
        "about": [],
        "contact": [],
        "pricing": [],
        "booking": [],
    }

    # Patterns for key pages
    service_pattern = re.compile(r"/(services?|treatments?|procedures?|what-we-do|menu|care)", re.I)
    about_pattern = re.compile(r"/(about|our-team|team|meet-the-doctor|doctors?|staff|story|who-we-are)", re.I)
    contact_pattern = re.compile(r"/(contact|location|directions|find-us|hours)", re.I)
    pricing_pattern = re.compile(r"/(pricing|prices|fees|insurance|payment|costs)", re.I)
    booking_pattern = re.compile(r"/(book|booking|appointment|schedule|reserve)", re.I)

    # 9. CTA Discovery (tel, mailto, whatsapp, booking)
    detected_ctas: Dict[str, List[str]] = {
        "phone": [],
        "email": [],
        "whatsapp": [],
        "booking_links": [],
    }

    for a_tag in soup.find_all("a", href=True):
        href = a_tag["href"].strip()
        if not href:
            continue

        # CTAs
        if href.lower().startswith("tel:"):
            phone_val = href[4:].strip()
            if phone_val and phone_val not in detected_ctas["phone"]:
                detected_ctas["phone"].append(phone_val)
        elif href.lower().startswith("mailto:"):
            email_val = href[7:].split("?")[0].strip()
            if email_val and email_val not in detected_ctas["email"]:
                detected_ctas["email"].append(email_val)
        elif "wa.me/" in href.lower() or "whatsapp" in href.lower():
            if href not in detected_ctas["whatsapp"]:
                detected_ctas["whatsapp"].append(href)
        elif any(provider in href.lower() for provider in ["calendly.com", "acuityscheduling.com", "zocdoc.com", "setmore.com"]):
            if href not in detected_ctas["booking_links"]:
                detected_ctas["booking_links"].append(href)

        # Internal Link Resolution
        resolved = resolve_url(base_url, href)
        if resolved and is_same_domain(base_url, resolved):
            if resolved not in seen_links and resolved != base_url:
                seen_links.add(resolved)
                discovered_internal_links.append(resolved)

                # Categorize into key subpages
                if service_pattern.search(resolved) and resolved not in key_subpages["services"]:
                    key_subpages["services"].append(resolved)
                elif about_pattern.search(resolved) and resolved not in key_subpages["about"]:
                    key_subpages["about"].append(resolved)
                elif contact_pattern.search(resolved) and resolved not in key_subpages["contact"]:
                    key_subpages["contact"].append(resolved)
                elif pricing_pattern.search(resolved) and resolved not in key_subpages["pricing"]:
                    key_subpages["pricing"].append(resolved)
                elif booking_pattern.search(resolved) and resolved not in key_subpages["booking"]:
                    key_subpages["booking"].append(resolved)

    # 10. Visible Text Extraction & Word Count
    # Clone soup for text cleaning
    text_soup = BeautifulSoup(html_content, "html.parser")
    for element in text_soup(["script", "style", "noscript", "svg", "header", "footer", "nav", "meta", "link"]):
        element.decompose()

    raw_text = text_soup.get_text(separator=" ", strip=True)
    cleaned_words = [w for w in re.split(r"\s+", raw_text) if w and len(w) > 1]
    visible_word_count = len(cleaned_words)
    visible_text_snippet = " ".join(cleaned_words[:120]) if cleaned_words else ""

    # 11. JavaScript Heavy SPA Detection
    is_javascript_heavy = False
    javascript_rendering_note = None

    # Check for empty root container typical of SPAs
    has_empty_root = bool(
        soup.find("div", id=re.compile(r"^(root|app|__next)$", re.I))
        or soup.find("div", class_=re.compile(r"^(app-root|react-root)$", re.I))
    )
    has_noscript_warning = bool(soup.find("noscript"))

    if (has_empty_root and visible_word_count < 100) or (visible_word_count < 40 and has_noscript_warning):
        is_javascript_heavy = True
        javascript_rendering_note = (
            "This website relies heavily on client-side JavaScript. "
            "The analyser could not extract all visible content from the initial HTML response."
        )

    return ParsedHTMLData(
        title=title,
        title_length=title_length,
        meta_description=meta_description,
        meta_description_length=meta_description_length,
        canonical_url=canonical_url,
        viewport_meta=viewport_meta,
        h1_tags=h1_tags,
        h2_tags=h2_tags,
        h3_tags=h3_tags,
        total_images=total_images,
        images_missing_alt=images_missing_alt[:10],  # first 10 for sample evidence
        missing_alt_count=missing_alt_count,
        structured_data_types=unique_schema_types,
        structured_data_blocks=structured_data_blocks,
        internal_links=discovered_internal_links,
        key_subpages=key_subpages,
        visible_word_count=visible_word_count,
        visible_text_snippet=visible_text_snippet,
        is_javascript_heavy=is_javascript_heavy,
        javascript_rendering_note=javascript_rendering_note,
        detected_ctas=detected_ctas,
    )
