import re
import asyncio
from urllib.parse import urlparse
from typing import List, Dict, Any, Optional, Tuple
import httpx
from bs4 import BeautifulSoup

from app.utils.url_helpers import resolve_url, is_same_domain, extract_domain
from app.services.fetcher import FetchResult, DEFAULT_HEADERS, DEFAULT_TIMEOUT
from app.services.html_parser import parse_html, ParsedHTMLData
from app.models import (
    PageContentItem,
    ContactInfoModel,
    CTAModel,
    ServiceStructureModel,
    ContentAnalysisResultModel,
)

# Known Booking & Scheduling Providers
BOOKING_PROVIDERS = [
    ("calendly.com", "Calendly"),
    ("acuityscheduling.com", "Acuity Scheduling"),
    ("zocdoc.com", "Zocdoc"),
    ("setmore.com", "Setmore"),
    ("square.site", "Square Appointments"),
    ("squareup.com/appointments", "Square Appointments"),
    ("appointlet.com", "Appointlet"),
    ("booksy.com", "Booksy"),
    ("fresha.com", "Fresha"),
    ("mindbodyonline.com", "Mindbody"),
    ("jane.app", "Jane App"),
    ("cliniko.com", "Cliniko"),
    ("schedulicity.com", "Schedulicity"),
    ("timely.com", "Timely"),
    ("vagaro.com", "Vagaro"),
    ("simplybook.me", "SimplyBook.me"),
]

# Patterns for prioritizing internal links
SERVICE_PAGE_PATTERN = re.compile(
    r"/(services?|treatments?|procedures?|what-we-do|offerings|solutions|care|specialties)/?",
    re.I,
)
SPECIFIC_SERVICE_PATTERN = re.compile(
    r"/(services?|treatments?|procedures?|care)/[a-zA-Z0-9_-]+",
    re.I,
)
ABOUT_PAGE_PATTERN = re.compile(
    r"/(about|about-us|our-team|team|meet-the-doctor|doctors?|staff|story|who-we-are|profile)",
    re.I,
)
CONTACT_PAGE_PATTERN = re.compile(
    r"/(contact|contact-us|location|locations|directions|find-us|hours)",
    re.I,
)
BOOKING_PAGE_PATTERN = re.compile(
    r"/(book|booking|appointment|appointments|schedule|reserve|reservation)",
    re.I,
)
PRICING_PAGE_PATTERN = re.compile(
    r"/(pricing|prices|fees|cost|costs|insurance|payment|plans)",
    re.I,
)

# Ignored URL patterns (low information / utility)
IGNORED_URL_PATTERNS = re.compile(
    r"/(cart|checkout|login|signup|register|signin|logout|privacy|terms|cookie|disclaimer|wp-content|wp-admin|wp-includes|cdn-cgi|tag|category|feed|rss)/?",
    re.I,
)


def classify_content_depth(word_count: int) -> str:
    """
    Classifies page content depth based on visible text word count.
    - Thin: < 250 words
    - Moderate: 250 - 800 words
    - Comprehensive: > 800 words
    """
    if word_count < 250:
        return "Thin"
    elif word_count <= 800:
        return "Moderate"
    else:
        return "Comprehensive"


def extract_visible_words(soup: BeautifulSoup) -> Tuple[int, str]:
    """
    Extracts visible text word count and text snippet from a BeautifulSoup document.
    Removes script, style, nav, footer, header, noscript, svg, etc.
    """
    text_soup = BeautifulSoup(str(soup), "html.parser")
    for elem in text_soup(["script", "style", "noscript", "svg", "header", "footer", "nav", "meta", "link", "aside"]):
        elem.decompose()

    raw_text = text_soup.get_text(separator=" ", strip=True)
    words = [w for w in re.split(r"\s+", raw_text) if w and len(w) > 1]
    word_count = len(words)
    snippet = " ".join(words[:100]) if words else ""
    return word_count, snippet


def derive_page_name(title: Optional[str], h1_tags: List[str], url: str) -> str:
    """
    Derives a friendly, concise page name from title, H1, or URL path.
    """
    if title:
        # Strip trailing branding e.g. "Services | Bright Smile Dental" -> "Services"
        clean_title = re.split(r"\s+[|\-–—:]\s+", title)[0].strip()
        if clean_title and len(clean_title) <= 60:
            return clean_title

    if h1_tags and h1_tags[0].strip():
        h1 = h1_tags[0].strip()
        if len(h1) <= 60:
            return h1

    # Fallback to URL path
    parsed = urlparse(url)
    path = parsed.path.strip("/")
    if not path:
        return "Homepage"

    segments = path.split("/")
    last_seg = segments[-1].replace("-", " ").replace("_", " ").title()
    return last_seg or "Page"


def is_service_page_check(url: str, title: Optional[str], h1_tags: List[str], headings: List[str]) -> bool:
    """
    Determines deterministically if a page appears to be a dedicated service page.
    """
    url_lower = url.lower()

    # If it is clearly an about or contact page, not a dedicated service page
    if ABOUT_PAGE_PATTERN.search(url_lower) or CONTACT_PAGE_PATTERN.search(url_lower) or BOOKING_PAGE_PATTERN.search(url_lower):
        return False

    # Check for specific service URL structure e.g. /services/teeth-whitening or /treatments/implants
    if SPECIFIC_SERVICE_PATTERN.search(url_lower):
        return True

    if SERVICE_PAGE_PATTERN.search(url_lower):
        return True

    # Check H1 or Title for service keywords
    title_text = f"{title or ''} {' '.join(h1_tags)}".lower()
    if any(k in title_text for k in ["service", "treatment", "procedure", "what we do", "our services", "care plan"]):
        return True

    return False


def prioritize_subpages(
    internal_links: List[str],
    base_url: str,
    key_subpages: Optional[Dict[str, List[str]]] = None,
    limit: int = 5,
) -> List[str]:
    """
    Prioritizes internal subpages for content analysis up to `limit` (max 5).
    Prioritization order:
    1. Dedicated service pages (/services/sub-page)
    2. Main services page (/services)
    3. About pages (/about, /team)
    4. Contact pages (/contact, /location)
    5. Booking pages (/book, /appointment)
    6. Pricing pages (/pricing)
    7. Other relevant internal pages
    """
    if not internal_links:
        return []

    base_domain = extract_domain(base_url)
    clean_base = base_url.rstrip("/")

    # Categorized buckets
    specific_services = []
    main_services = []
    about_pages = []
    contact_pages = []
    booking_pages = []
    pricing_pages = []
    other_pages = []

    seen = set()
    # Also add base_url and variants to seen
    seen.add(clean_base)
    seen.add(f"{clean_base}/")

    # If key_subpages dict from HTML parser is available, use it for early populating
    all_candidate_links = list(internal_links)
    if key_subpages:
        for cat in ["services", "about", "contact", "booking", "pricing"]:
            for link in key_subpages.get(cat, []):
                if link not in all_candidate_links:
                    all_candidate_links.insert(0, link)

    for raw_link in all_candidate_links:
        resolved = resolve_url(base_url, raw_link)
        if not resolved:
            continue

        clean_link = resolved.rstrip("/")
        if clean_link in seen:
            continue
        if not is_same_domain(base_url, clean_link):
            continue
        if IGNORED_URL_PATTERNS.search(clean_link):
            continue

        seen.add(clean_link)

        # Categorize
        if SPECIFIC_SERVICE_PATTERN.search(clean_link):
            specific_services.append(clean_link)
        elif SERVICE_PAGE_PATTERN.search(clean_link):
            main_services.append(clean_link)
        elif ABOUT_PAGE_PATTERN.search(clean_link):
            about_pages.append(clean_link)
        elif CONTACT_PAGE_PATTERN.search(clean_link):
            contact_pages.append(clean_link)
        elif BOOKING_PAGE_PATTERN.search(clean_link):
            booking_pages.append(clean_link)
        elif PRICING_PAGE_PATTERN.search(clean_link):
            pricing_pages.append(clean_link)
        else:
            # Check extension to avoid images/docs
            if not re.search(r"\.(pdf|jpg|jpeg|png|gif|svg|webp|css|js|xml|json)$", clean_link, re.I):
                other_pages.append(clean_link)

    # Assemble in strict priority order
    ordered: List[str] = []
    for bucket in [specific_services, main_services, about_pages, contact_pages, booking_pages, pricing_pages, other_pages]:
        for url in bucket:
            if url not in ordered:
                ordered.append(url)
            if len(ordered) >= limit:
                return ordered[:limit]

    return ordered[:limit]


def extract_ctas_and_contact(soup: BeautifulSoup, page_url: str, base_url: str) -> Dict[str, Any]:
    """
    Extracts CTAs, phone numbers, emails, whatsapp links, booking links,
    and physical address / opening hours from a single page's HTML / Schema.
    """
    phones: List[str] = []
    emails: List[str] = []
    whatsapp: List[str] = []
    booking_links: List[str] = []
    booking_providers: List[str] = []
    detected_address: Optional[str] = None
    detected_hours: List[str] = []

    # 1. Links (a tags)
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if not href:
            continue

        href_lower = href.lower()

        # Phone
        if href_lower.startswith("tel:"):
            num = re.sub(r"^tel:", "", href, flags=re.I).strip()
            # Clean number format
            cleaned_num = re.sub(r"[^\d+\s\-().]", "", num).strip()
            if cleaned_num and cleaned_num not in phones:
                phones.append(cleaned_num)

        # Email
        elif href_lower.startswith("mailto:"):
            mail = re.sub(r"^mailto:", "", href, flags=re.I).split("?")[0].strip()
            if mail and "@" in mail and mail not in emails:
                emails.append(mail)

        # WhatsApp
        elif any(w in href_lower for w in ["wa.me", "api.whatsapp.com", "whatsapp://", "web.whatsapp.com"]):
            if href not in whatsapp:
                whatsapp.append(href)

        # Booking / Scheduling Providers
        for domain_pattern, provider_name in BOOKING_PROVIDERS:
            if domain_pattern in href_lower:
                if href not in booking_links:
                    booking_links.append(href)
                if provider_name not in booking_providers:
                    booking_providers.append(provider_name)

        # Internal booking links
        if BOOKING_PAGE_PATTERN.search(href_lower) and not href_lower.startswith("tel:") and not href_lower.startswith("mailto:"):
            resolved_booking = resolve_url(base_url, href)
            if resolved_booking and resolved_booking not in booking_links:
                booking_links.append(resolved_booking)

    # 2. Schema.org (JSON-LD) Contact & Address
    for script in soup.find_all("script", attrs={"type": "application/ld+json"}):
        raw_json = script.string or script.get_text()
        if not raw_json:
            continue
        try:
            import json
            data = json.loads(raw_json.strip())

            def parse_schema_node(node: Any):
                nonlocal detected_address, phones, emails, detected_hours
                if not isinstance(node, dict):
                    if isinstance(node, list):
                        for item in node:
                            parse_schema_node(item)
                    return

                # Check phone in schema
                if "telephone" in node and isinstance(node["telephone"], str):
                    tel = node["telephone"].strip()
                    if tel and tel not in phones:
                        phones.append(tel)

                # Check email in schema
                if "email" in node and isinstance(node["email"], str):
                    em = node["email"].strip()
                    if em and "@" in em and em not in emails:
                        emails.append(em)

                # Check address
                if "address" in node and not detected_address:
                    addr = node["address"]
                    if isinstance(addr, dict):
                        parts = [
                            addr.get("streetAddress"),
                            addr.get("addressLocality"),
                            addr.get("addressRegion"),
                            addr.get("postalCode"),
                            addr.get("addressCountry"),
                        ]
                        valid_parts = [str(p).strip() for p in parts if p and str(p).strip()]
                        if valid_parts:
                            detected_address = ", ".join(valid_parts)
                    elif isinstance(addr, str) and len(addr.strip()) > 5:
                        detected_address = addr.strip()

                # Check opening hours
                if "openingHours" in node:
                    oh = node["openingHours"]
                    if isinstance(oh, list):
                        detected_hours.extend([str(h).strip() for h in oh if str(h).strip()])
                    elif isinstance(oh, str) and oh.strip():
                        detected_hours.append(oh.strip())
                elif "openingHoursSpecification" in node:
                    specs = node["openingHoursSpecification"]
                    if isinstance(specs, list):
                        for spec in specs:
                            if isinstance(spec, dict):
                                days = spec.get("dayOfWeek", "")
                                opens = spec.get("opens", "")
                                closes = spec.get("closes", "")
                                if days and opens and closes:
                                    day_str = ", ".join(days) if isinstance(days, list) else str(days)
                                    detected_hours.append(f"{day_str}: {opens} - {closes}")

                # Traverse nested graph
                if "@graph" in node and isinstance(node["@graph"], list):
                    for item in node["@graph"]:
                        parse_schema_node(item)

            parse_schema_node(data)
        except Exception:
            pass

    # 3. Microdata / Semantic <address> tag fallback
    if not detected_address:
        address_elem = soup.find("address")
        if address_elem:
            addr_text = address_elem.get_text(separator=" ", strip=True)
            # Basic validation that it contains street/number or city characteristics
            if len(addr_text) >= 10 and any(char.isdigit() for char in addr_text):
                detected_address = " ".join(addr_text.split())

    return {
        "phones": phones,
        "emails": emails,
        "whatsapp": whatsapp,
        "booking_links": booking_links,
        "booking_providers": booking_providers,
        "address": detected_address,
        "opening_hours": detected_hours if detected_hours else None,
    }


def extract_services_from_content(
    pages: List[PageContentItem],
    homepage_soup: BeautifulSoup,
) -> Tuple[List[str], List[Dict[str, Any]], bool, bool, bool, str, str]:
    """
    Deterministically identifies services, dedicated service pages,
    and website service architecture across both dedicated pages and homepage sections.

    Returns:
        (detected_services, service_details, has_dedicated_pages, services_mainly_on_homepage,
         services_detected_from_homepage, service_detection_confidence, service_architecture)
    """
    detected_services: List[str] = []
    service_details: List[Dict[str, Any]] = []
    homepage_service_count = 0

    # 1. Collect from dedicated service pages
    dedicated_service_pages = [
        p for p in pages
        if p.is_service_page and not p.url.rstrip("/").endswith(extract_domain(p.url))
    ]

    for p in dedicated_service_pages:
        svc_name = p.page_name
        # Clean service name
        svc_name = re.sub(r"^(our\s+services?|treatments?|services?|solutions?)\s*[:|-]\s*", "", svc_name, flags=re.I).strip()
        if svc_name and svc_name.lower() not in [s.lower() for s in detected_services] and svc_name.lower() not in [
            "services", "our services", "treatments", "solutions", "products", "overview"
        ]:
            detected_services.append(svc_name)
            service_details.append({
                "name": svc_name,
                "source": "dedicated_page",
                "url": p.url,
            })

    # 2. Extract services / solutions from Homepage sections & headings
    service_section_headers = ["services", "solutions", "what we do", "capabilities", "offerings", "products", "use cases", "our treatments", "what we offer", "platform capabilities"]
    generic_skips = {
        "our services", "services", "what we do", "our treatments", "overview", "read more",
        "learn more", "contact us", "about us", "solutions", "capabilities", "get in touch",
        "pricing", "features", "products", "case studies", "testimonials", "blog", "faq",
        "terms of service", "privacy policy", "quick links", "menu", "navigation"
    }

    # Find section elements with service-related id/class or heading
    for heading_tag in homepage_soup.find_all(["h1", "h2", "h3", "h4"]):
        h_text = heading_tag.get_text(strip=True).lower()
        if any(sec in h_text for sec in service_section_headers):
            # Look at sibling or descendant sub-headings
            parent_sec = heading_tag.find_parent(["section", "div", "article", "main"])
            if parent_sec:
                for sub_h in parent_sec.find_all(["h2", "h3", "h4", "strong"]):
                    sub_text = sub_h.get_text(strip=True)
                    if 3 < len(sub_text) < 55 and sub_text.lower() not in generic_skips:
                        if sub_text.lower() not in [s.lower() for s in detected_services]:
                            detected_services.append(sub_text)
                            homepage_service_count += 1
                            service_details.append({
                                "name": sub_text,
                                "source": "homepage_section",
                                "url": pages[0].url if pages else "",
                            })

    # 3. Collect from headings across all analyzed pages
    for p in pages:
        for heading in p.headings:
            clean_h = heading.strip()
            if len(clean_h) < 4 or len(clean_h) > 55 or clean_h.lower() in generic_skips:
                continue

            if p.is_service_page and clean_h.lower() not in [s.lower() for s in detected_services]:
                detected_services.append(clean_h)
                service_details.append({
                    "name": clean_h,
                    "source": "page_heading",
                    "url": p.url,
                })

    has_dedicated_pages = len(dedicated_service_pages) > 0
    services_detected_from_homepage = homepage_service_count > 0
    services_mainly_on_homepage = not has_dedicated_pages and len(detected_services) > 0

    # Classify architecture
    if has_dedicated_pages and len(dedicated_service_pages) >= 2:
        architecture = "dedicated_multi_page"
    elif has_dedicated_pages and services_detected_from_homepage:
        architecture = "mixed"
    elif len(detected_services) > 0:
        architecture = "homepage_centric"
    else:
        architecture = "inconclusive"

    # Confidence score
    if len(detected_services) >= 3 or (has_dedicated_pages and len(detected_services) >= 1):
        confidence = "high"
    elif len(detected_services) >= 1:
        confidence = "medium"
    else:
        confidence = "low"

    return (
        detected_services[:20],
        service_details[:20],
        has_dedicated_pages,
        services_mainly_on_homepage,
        services_detected_from_homepage,
        confidence,
        architecture,
    )


async def analyze_content(
    homepage_fetch: FetchResult,
    client: Optional[httpx.AsyncClient] = None,
) -> ContentAnalysisResultModel:
    """
    Performs comprehensive Content, CTA, Contact, and Service Structure Analysis
    across the homepage and up to 5 prioritized internal subpages.
    """
    target_url = homepage_fetch.final_url

    # Reliability Gate: If the crawler was blocked by WAF/403/429, mark content inconclusive
    is_blocked = (
        not getattr(homepage_fetch, "content_accessible", True)
        or homepage_fetch.error_type == "bot_protection_detected"
        or (homepage_fetch.status_code in (403, 429))
    )
    if is_blocked:
        return ContentAnalysisResultModel(
            pages_analyzed=[],
            total_pages_analyzed=0,
            homepage_word_count=0,
            average_word_count=0,
            contact_info=ContactInfoModel(
                phones=[],
                emails=[],
                address=None,
                opening_hours=None,
            ),
            ctas=CTAModel(
                phones=[],
                emails=[],
                whatsapp=[],
                booking_links=[],
                booking_providers=[],
            ),
            services_structure=ServiceStructureModel(
                has_dedicated_service_pages=False,
                services_mainly_on_homepage=False,
                service_pages_count=0,
                detected_services=[],
                service_details=[],
            ),
            summary=(
                f"Automated crawler access was challenged by edge security firewall (HTTP {homepage_fetch.status_code or 403}/WAF). "
                "Live page content, word counts, and service structure could not be analyzed."
            ),
            is_inconclusive=True,
            inconclusive_reason=(
                f"Website returned an automated access or bot-protection challenge (HTTP {homepage_fetch.status_code or 403}). "
                "Page content cannot be evaluated as actual website copy."
            ),
        )

    pages_analyzed: List[PageContentItem] = []

    # Aggregated contact and CTA containers
    all_phones: List[str] = []
    all_emails: List[str] = []
    all_whatsapp: List[str] = []
    all_booking_links: List[str] = []
    all_booking_providers: List[str] = []
    final_address: Optional[str] = None
    final_opening_hours: Optional[List[str]] = None

    # 1. Process Homepage
    homepage_html = homepage_fetch.raw_html or ""
    homepage_soup = BeautifulSoup(homepage_html, "html.parser")
    homepage_parsed = homepage_fetch.parsed_data or parse_html(homepage_html, target_url)

    hp_word_count, _ = extract_visible_words(homepage_soup)
    # Use parsed data word count if greater
    hp_word_count = max(hp_word_count, homepage_parsed.visible_word_count)

    hp_depth = classify_content_depth(hp_word_count)
    hp_headings = [h for h in (homepage_parsed.h1_tags + homepage_parsed.h2_tags[:5] + homepage_parsed.h3_tags[:5]) if h]
    hp_name = derive_page_name(homepage_parsed.title, homepage_parsed.h1_tags, target_url)

    hp_item = PageContentItem(
        url=target_url,
        page_name=hp_name,
        word_count=hp_word_count,
        content_depth=hp_depth,
        headings=hp_headings[:15],
        is_service_page=False,
    )
    pages_analyzed.append(hp_item)

    # Extract CTAs and Contact from Homepage
    hp_extracted = extract_ctas_and_contact(homepage_soup, target_url, target_url)
    all_phones.extend(hp_extracted["phones"])
    all_emails.extend(hp_extracted["emails"])
    all_whatsapp.extend(hp_extracted["whatsapp"])
    all_booking_links.extend(hp_extracted["booking_links"])
    all_booking_providers.extend(hp_extracted["booking_providers"])
    if hp_extracted["address"]:
        final_address = hp_extracted["address"]
    if hp_extracted["opening_hours"]:
        final_opening_hours = hp_extracted["opening_hours"]

    # 2. Select up to 5 prioritized internal subpages
    candidate_links = homepage_parsed.internal_links
    subpages_to_crawl = prioritize_subpages(
        internal_links=candidate_links,
        base_url=target_url,
        key_subpages=homepage_parsed.key_subpages,
        limit=5,
    )

    # 3. Crawl subpages concurrently
    own_client = False
    if client is None:
        client = httpx.AsyncClient(
            headers=DEFAULT_HEADERS,
            timeout=httpx.Timeout(connect=4.0, read=6.0, write=4.0, pool=10.0),
            follow_redirects=True,
            verify=False,
        )
        own_client = True

    try:
        async def fetch_and_analyze_subpage(sub_url: str) -> Optional[Tuple[PageContentItem, Dict[str, Any]]]:
            try:
                resp = await client.get(sub_url)
                if resp.status_code != 200 or not resp.text:
                    return None

                sub_soup = BeautifulSoup(resp.text, "html.parser")
                sub_parsed = parse_html(resp.text, sub_url)
                w_count, _ = extract_visible_words(sub_soup)
                w_count = max(w_count, sub_parsed.visible_word_count)
                depth = classify_content_depth(w_count)

                headings = [h for h in (sub_parsed.h1_tags + sub_parsed.h2_tags[:5] + sub_parsed.h3_tags[:5]) if h]
                p_name = derive_page_name(sub_parsed.title, sub_parsed.h1_tags, sub_url)
                is_svc = is_service_page_check(sub_url, sub_parsed.title, sub_parsed.h1_tags, headings)

                page_item = PageContentItem(
                    url=sub_url,
                    page_name=p_name,
                    word_count=w_count,
                    content_depth=depth,
                    headings=headings[:15],
                    is_service_page=is_svc,
                )

                extracted_cta = extract_ctas_and_contact(sub_soup, sub_url, target_url)
                return page_item, extracted_cta
            except Exception:
                return None

        if subpages_to_crawl:
            tasks = [fetch_and_analyze_subpage(u) for u in subpages_to_crawl]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            for res in results:
                if isinstance(res, tuple) and res[0] is not None:
                    p_item, cta_data = res
                    pages_analyzed.append(p_item)

                    # Merge CTAs and Contact
                    for p in cta_data["phones"]:
                        if p not in all_phones:
                            all_phones.append(p)
                    for e in cta_data["emails"]:
                        if e not in all_emails:
                            all_emails.append(e)
                    for w in cta_data["whatsapp"]:
                        if w not in all_whatsapp:
                            all_whatsapp.append(w)
                    for b in cta_data["booking_links"]:
                        if b not in all_booking_links:
                            all_booking_links.append(b)
                    for prov in cta_data["booking_providers"]:
                        if prov not in all_booking_providers:
                            all_booking_providers.append(prov)
                    if not final_address and cta_data["address"]:
                        final_address = cta_data["address"]
                    if not final_opening_hours and cta_data["opening_hours"]:
                        final_opening_hours = cta_data["opening_hours"]

    finally:
        if own_client:
            await client.aclose()

    # 4. Service and Architecture Analysis
    (
        detected_svcs,
        svc_details,
        has_dedicated,
        mainly_homepage,
        from_homepage,
        svc_confidence,
        architecture,
    ) = extract_services_from_content(
        pages=pages_analyzed,
        homepage_soup=homepage_soup,
    )

    dedicated_count = sum(1 for p in pages_analyzed if p.is_service_page and p.url != target_url)

    # 5. Compute summary metrics
    total_analyzed = len(pages_analyzed)
    total_words = sum(p.word_count for p in pages_analyzed)
    avg_words = int(total_words / total_analyzed) if total_analyzed > 0 else hp_word_count

    # Build concise summary
    if architecture == "dedicated_multi_page":
        structure_desc = f"multi-page architecture with {dedicated_count} dedicated service pages"
    elif architecture == "mixed":
        structure_desc = f"mixed architecture with {dedicated_count} dedicated subpages and homepage listings"
    elif architecture == "homepage_centric":
        structure_desc = "homepage-centric service presentation"
    else:
        structure_desc = "general content structure"

    if len(detected_svcs) > 0:
        svc_phrase = f"Identified {len(detected_svcs)} service/capability offerings"
    else:
        svc_phrase = "Services could not be reliably identified from the analyzed content"

    summary_text = (
        f"Analyzed {total_analyzed} pages ({hp_word_count} homepage words, {avg_words} avg words/page). "
        f"{svc_phrase} across a {structure_desc}."
    )

    return ContentAnalysisResultModel(
        pages_analyzed=pages_analyzed,
        total_pages_analyzed=total_analyzed,
        homepage_word_count=hp_word_count,
        average_word_count=avg_words,
        contact_info=ContactInfoModel(
            phones=all_phones,
            emails=all_emails,
            address=final_address,
            opening_hours=final_opening_hours,
        ),
        ctas=CTAModel(
            phones=all_phones,
            emails=all_emails,
            whatsapp=all_whatsapp,
            booking_links=all_booking_links,
            booking_providers=all_booking_providers,
        ),
        services_structure=ServiceStructureModel(
            has_dedicated_service_pages=has_dedicated,
            services_mainly_on_homepage=mainly_homepage,
            service_pages_count=dedicated_count,
            detected_services=detected_svcs,
            service_details=svc_details,
            service_detection_confidence=svc_confidence,
            services_detected_from_homepage=from_homepage,
            service_architecture=architecture,
        ),
        summary=summary_text,
    )
