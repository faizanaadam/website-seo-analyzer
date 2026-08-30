import re
from typing import List, Dict, Any, Optional
from app.services.fetcher import FetchResult
from app.services.html_parser import ParsedHTMLData
from app.utils.url_helpers import resolve_url, extract_domain, is_same_domain

# Healthcare and Medical keywords for observable context detection
HEALTHCARE_KEYWORDS = [
    "dental", "dentist", "teeth", "clinic", "doctor", "physician", "orthodont",
    "medical", "hospital", "surgery", "patient", "health", "therapy", "chiropract",
    "optometr", "pediatric", "implant", "invisalign", "whitening", "dermatol"
]

LOCAL_SERVICE_KEYWORDS = [
    "plumb", "garage", "auto repair", "mechanic", "hvac", "electrician", "roofing",
    "contractor", "cleaner", "cleaning", "salon", "barber", "restaurant", "cafe",
    "bakery", "locksmith", "pest control", "towing", "mover", "landscap", "dentist",
    "clinic", "veterinar", "car care"
]

HEALTHCARE_SCHEMA_TYPES = {
    "MedicalBusiness", "Dentist", "Physician", "MedicalOrganization",
    "HealthAndBeautyBusiness", "MedicalClinic", "Hospital", "Pharmacy",
    "DiagnosticLab", "MedicalCondition"
}

LOCAL_BUSINESS_SCHEMA_TYPES = {
    "LocalBusiness", "AutomotiveBusiness", "AutoRepair", "HomeAndConstructionBusiness",
    "Plumber", "HVACBusiness", "Electrician", "RoofingContractor", "LegalService",
    "Attorney", "FoodEstablishment", "Restaurant", "CafeOrCoffeeShop", "BeautySalon",
    "HairSalon", "DryCleaningOrLaundry", "Store", "ProfessionalService", "FinancialService"
}

ORGANIZATION_SCHEMA_TYPES = {
    "Organization", "Corporation", "EducationalOrganization", "WebSite", "WebPage"
}


class TechnicalFinding:
    def __init__(
        self,
        id: str,
        title: str,
        status: str,  # 'pass' | 'needs_attention' | 'fail'
        summary: str,
        why_it_matters: str,
        evidence_found: str,
        suggested_action: str,
        affected_urls: Optional[List[str]] = None,
        is_inconclusive: bool = False,
    ):
        self.id = id
        self.title = title
        self.status = status
        self.summary = summary
        self.why_it_matters = why_it_matters
        self.evidence_found = evidence_found
        self.suggested_action = suggested_action
        self.affected_urls = affected_urls or []
        self.is_inconclusive = is_inconclusive

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "status": self.status,
            "summary": self.summary,
            "why_it_matters": self.why_it_matters,
            "evidence_found": self.evidence_found,
            "suggested_action": self.suggested_action,
            "affected_urls": self.affected_urls,
            "is_inconclusive": self.is_inconclusive,
        }


class TechnicalSEOSummary:
    def __init__(
        self,
        passed_count: int,
        needs_attention_count: int,
        issues_count: int,
        total_checks: int,
        health_score: int,
        summary_text: str,
        is_content_blocked: bool = False,
        reliability_notice: Optional[str] = None,
    ):
        self.passed_count = passed_count
        self.needs_attention_count = needs_attention_count
        self.issues_count = issues_count
        self.total_checks = total_checks
        self.health_score = health_score
        self.summary_text = summary_text
        self.is_content_blocked = is_content_blocked
        self.reliability_notice = reliability_notice

    def to_dict(self) -> Dict[str, Any]:
        return {
            "passed_count": self.passed_count,
            "needs_attention_count": self.needs_attention_count,
            "issues_count": self.issues_count,
            "total_checks": self.total_checks,
            "health_score": self.health_score,
            "summary_text": self.summary_text,
            "is_content_blocked": self.is_content_blocked,
            "reliability_notice": self.reliability_notice,
        }


class TechnicalSEOResult:
    def __init__(
        self,
        summary: TechnicalSEOSummary,
        findings: List[TechnicalFinding],
        inferred_category: str,
    ):
        self.summary = summary
        self.findings = findings
        self.inferred_category = inferred_category

    def to_dict(self) -> Dict[str, Any]:
        return {
            "summary": self.summary.to_dict(),
            "findings": [f.to_dict() for f in self.findings],
            "inferred_category": self.inferred_category,
        }


def detect_observable_category(parsed: ParsedHTMLData) -> str:
    """
    Infers the business category strictly from observable text and schema evidence.
    Returns: 'healthcare' | 'local_service' | 'general'
    """
    evidence_text = " ".join([
        parsed.title or "",
        parsed.meta_description or "",
        " ".join(parsed.h1_tags),
        " ".join(parsed.h2_tags),
        parsed.visible_text_snippet,
    ]).lower()

    # Check for healthcare keywords
    if any(re.search(rf"\b{kw}\b", evidence_text, re.I) for kw in HEALTHCARE_KEYWORDS):
        return "healthcare"

    # Check for local service keywords
    if any(re.search(rf"\b{kw}\b", evidence_text, re.I) for kw in LOCAL_SERVICE_KEYWORDS):
        return "local_service"

    return "general"


def evaluate_technical_seo(fetch_result: FetchResult) -> TechnicalSEOResult:
    """
    Executes deterministic, evidence-based SEO rules on a FetchResult.
    """
    findings: List[TechnicalFinding] = []
    parsed = fetch_result.parsed_data

    # If fetch failed before parsing HTML (e.g. DNS failure)
    if not parsed:
        summary = TechnicalSEOSummary(
            passed_count=0,
            needs_attention_count=0,
            issues_count=1,
            total_checks=1,
            health_score=0,
            summary_text="Could not analyze technical SEO because the website could not be retrieved.",
        )
        return TechnicalSEOResult(summary=summary, findings=[], inferred_category="unknown")

    final_url = fetch_result.final_url
    category = detect_observable_category(parsed)

    # -------------------------------------------------------------
    # Reliability Gate: Blocked or Bot-Protected Sites (403/429/WAF)
    # -------------------------------------------------------------
    is_blocked = (
        not getattr(fetch_result, "content_accessible", True)
        or fetch_result.error_type == "bot_protection_detected"
        or (fetch_result.status_code in (403, 429))
    )
    if is_blocked:
        is_https = final_url.startswith("https://")
        findings.append(
            TechnicalFinding(
                id="ssl_https",
                title="HTTPS Security",
                status="pass" if is_https else "fail",
                summary="Website uses secure HTTPS encryption." if is_https else "Website is not using secure HTTPS encryption.",
                why_it_matters="HTTPS is a confirmed Google ranking factor and protects user trust.",
                evidence_found=f"URL scheme: {'https://' if is_https else 'http://'}",
                suggested_action="No action needed." if is_https else "Enforce 301 redirect to HTTPS and configure SSL certificate.",
                is_inconclusive=False,
            )
        )

        findings.append(
            TechnicalFinding(
                id="bot_protection_detected",
                title="Bot Protection & Crawler Accessibility (WAF)",
                status="needs_attention",
                summary=f"Edge security firewall returned a challenge or blocked status (HTTP {fetch_result.status_code or 403}) on crawler access.",
                why_it_matters="Major search engines (Googlebot, Bingbot) must be able to crawl page content to index and rank pages.",
                evidence_found=f"HTTP {fetch_result.status_code} challenge page returned. Live page HTML was inaccessible.",
                suggested_action="Verify edge firewall/WAF rules (Cloudflare, Akamai, AWS WAF) to ensure verified search engine bots are allowed.",
                is_inconclusive=False,
            )
        )

        findings.append(
            TechnicalFinding(
                id="robots_txt",
                title="Robots.txt Configuration",
                status="pass" if fetch_result.robots_txt_present else "needs_attention",
                summary="robots.txt file is present." if fetch_result.robots_txt_present else "robots.txt was not detected at /robots.txt.",
                why_it_matters="Guides search engine crawlers on crawl budget and index prioritization.",
                evidence_found=f"HTTP status on /robots.txt: {'200 OK' if fetch_result.robots_txt_present else 'Not found'}",
                suggested_action="No action needed." if fetch_result.robots_txt_present else "Create and publish a valid robots.txt file.",
                is_inconclusive=False,
            )
        )

        findings.append(
            TechnicalFinding(
                id="sitemap_xml",
                title="XML Sitemap",
                status="pass" if fetch_result.sitemap_xml_present else "needs_attention",
                summary="sitemap.xml file is present." if fetch_result.sitemap_xml_present else "sitemap.xml was not detected at standard location.",
                why_it_matters="Helps search engines discover and index all core pages and services.",
                evidence_found=f"HTTP status on /sitemap.xml: {'200 OK' if fetch_result.sitemap_xml_present else 'Not found'}",
                suggested_action="No action needed." if fetch_result.sitemap_xml_present else "Generate and submit an XML sitemap to Google Search Console.",
                is_inconclusive=False,
            )
        )

        content_checks = [
            ("page_title", "Page Title"),
            ("meta_description", "Meta Description"),
            ("heading_structure", "Heading Structure"),
            ("image_alt_tags", "Image Alt Text"),
            ("schema_org", "Structured Data (Schema.org)"),
            ("mobile_viewport", "Mobile Viewport"),
        ]
        for check_id, check_title in content_checks:
            findings.append(
                TechnicalFinding(
                    id=check_id,
                    title=check_title,
                    status="needs_attention",
                    summary="Inconclusive: Automated crawler was challenged by edge firewall (HTTP 403/WAF). Content could not be verified.",
                    why_it_matters="Search engines require direct access to HTML tags and content structure to properly rank pages.",
                    evidence_found=f"HTTP {fetch_result.status_code or 403} challenge response. Live page content was inaccessible.",
                    suggested_action="Ensure search engine crawlers are whitelisted on your CDN/WAF to allow verification.",
                    is_inconclusive=True,
                )
            )

        passed_count = sum(1 for f in findings if f.status == "pass")
        needs_attention_count = sum(1 for f in findings if f.status == "needs_attention")
        issues_count = sum(1 for f in findings if f.status == "fail")
        total_checks = len(findings)
        health_score = int(round(((passed_count * 10) + (needs_attention_count * 5)) / (total_checks * 10) * 100))

        summary = TechnicalSEOSummary(
            passed_count=passed_count,
            needs_attention_count=needs_attention_count,
            issues_count=issues_count,
            total_checks=total_checks,
            health_score=health_score,
            summary_text="Crawler access was challenged by edge security (HTTP 403/WAF). Content-level analysis is inconclusive.",
            is_content_blocked=True,
            reliability_notice=f"Automated crawler access was blocked by edge security firewall (HTTP {fetch_result.status_code or 403}). Content-derived checks are inconclusive and have been suppressed from scoring penalties.",
        )
        return TechnicalSEOResult(
            summary=summary,
            findings=findings,
            inferred_category="general",
        )

    # -------------------------------------------------------------
    # 1. Page Title Check
    # -------------------------------------------------------------
    title = parsed.title
    title_len = parsed.title_length

    if not title or title_len == 0:
        findings.append(
            TechnicalFinding(
                id="page_title",
                title="Page Title",
                status="fail",
                summary="Page title is missing from the <head> section.",
                why_it_matters="The <title> tag is the single most important on-page HTML tag for search engines and user click-throughs.",
                evidence_found="No <title> tag detected in HTML.",
                suggested_action="Add a descriptive 30–60 character <title> tag containing your primary service and city/brand.",
            )
        )
    elif title_len < 25:
        findings.append(
            TechnicalFinding(
                id="page_title",
                title="Page Title",
                status="needs_attention",
                summary=f"Page title is too short ({title_len} characters). Recommended range is 30–60 characters.",
                why_it_matters="Short titles miss opportunities to include relevant service keywords and geographic location.",
                evidence_found=f"<title>{title}</title> ({title_len} chars)",
                suggested_action="Expand title to include your business name, primary service, and location.",
            )
        )
    elif title_len > 65:
        findings.append(
            TechnicalFinding(
                id="page_title",
                title="Page Title",
                status="needs_attention",
                summary=f"Page title is too long ({title_len} characters) and may be truncated by search engines.",
                why_it_matters="Truncated titles cut off valuable information in Google search snippets.",
                evidence_found=f"<title>{title}</title> ({title_len} chars)",
                suggested_action="Shorten title to between 30 and 60 characters to prevent truncation.",
            )
        )
    else:
        findings.append(
            TechnicalFinding(
                id="page_title",
                title="Page Title",
                status="pass",
                summary=f"Page title is well-optimized ({title_len} characters).",
                why_it_matters="A concise, well-sized title ensures full visibility in search engine result pages (SERPs).",
                evidence_found=f"<title>{title}</title>",
                suggested_action="Keep title up to date when services or branding evolve.",
            )
        )

    # -------------------------------------------------------------
    # 2. Meta Description Check
    # -------------------------------------------------------------
    meta_desc = parsed.meta_description
    meta_len = parsed.meta_description_length

    if not meta_desc or meta_len == 0:
        findings.append(
            TechnicalFinding(
                id="meta_description",
                title="Meta Description",
                status="needs_attention",
                summary="Meta description is missing.",
                why_it_matters="Without a meta description, Google auto-generates snippets that may not highlight your value proposition.",
                evidence_found="No meta description or og:description tag detected.",
                suggested_action="Add a compelling 120–160 character meta description outlining your services and call to action.",
            )
        )
    elif meta_len < 70:
        findings.append(
            TechnicalFinding(
                id="meta_description",
                title="Meta Description",
                status="needs_attention",
                summary=f"Meta description is relatively short ({meta_len} characters). Recommended range is 120–160.",
                why_it_matters="Short descriptions underutilize snippet space on search result pages.",
                evidence_found=f'content="{meta_desc}" ({meta_len} chars)',
                suggested_action="Expand description with service highlights and a clear reason to choose your business.",
            )
        )
    elif meta_len > 165:
        findings.append(
            TechnicalFinding(
                id="meta_description",
                title="Meta Description",
                status="needs_attention",
                summary=f"Meta description is too long ({meta_len} characters) and may be truncated by search engines.",
                why_it_matters="Descriptions exceeding 160 characters risk getting cut off with ellipses (...) in search results.",
                evidence_found=f'content="{meta_desc}" ({meta_len} chars)',
                suggested_action="Trim description to between 120 and 160 characters.",
            )
        )
    else:
        findings.append(
            TechnicalFinding(
                id="meta_description",
                title="Meta Description",
                status="pass",
                summary=f"Meta description is well-formed ({meta_len} characters).",
                why_it_matters="Compelling descriptions improve search click-through rates (CTR).",
                evidence_found=f'content="{meta_desc}"',
                suggested_action="Ensure description includes your primary contact or booking CTA.",
            )
        )

    # -------------------------------------------------------------
    # 3. Heading Structure Check
    # -------------------------------------------------------------
    h1_count = len(parsed.h1_tags)
    h2_count = len(parsed.h2_tags)

    if h1_count == 0:
        findings.append(
            TechnicalFinding(
                id="heading_structure",
                title="Heading Structure",
                status="fail",
                summary="No <h1> heading tag found on the page.",
                why_it_matters="The <h1> tag represents the primary topic of the page to search engine crawlers.",
                evidence_found="Found 0 <h1> tags.",
                suggested_action="Add exactly one descriptive <h1> heading communicating your primary service and value.",
            )
        )
    elif h1_count > 1:
        sample_h1s = ", ".join([f'"{h}"' for h in parsed.h1_tags[:3]])
        findings.append(
            TechnicalFinding(
                id="heading_structure",
                title="Heading Structure",
                status="needs_attention",
                summary=f"Multiple <h1> tags found ({h1_count} detected). Best practice is exactly one <h1> per page.",
                why_it_matters="Multiple <h1> tags can dilute semantic hierarchy and confuse search crawlers about the main page focus.",
                evidence_found=f"Found {h1_count} <h1> tags: {sample_h1s}",
                suggested_action="Retain one primary <h1> and convert secondary headings into <h2> tags.",
            )
        )
    else:
        if h2_count == 0 and len(parsed.h3_tags) == 0:
            findings.append(
                TechnicalFinding(
                    id="heading_structure",
                    title="Heading Structure",
                    status="needs_attention",
                    summary="Single <h1> found, but no supporting <h2> subheadings.",
                    why_it_matters="Subheadings (<h2>) break content into logical sections for both users and search engines.",
                    evidence_found=f'<h1>: "{parsed.h1_tags[0]}", 0 <h2> tags',
                    suggested_action="Add <h2> subheadings to organize procedure and service descriptions.",
                )
            )
        else:
            findings.append(
                TechnicalFinding(
                    id="heading_structure",
                    title="Heading Structure",
                    status="pass",
                    summary=f"Clear heading hierarchy with 1 <h1> and {h2_count} <h2> subheadings.",
                    why_it_matters="Structured headings allow search crawlers and screen readers to understand content hierarchy.",
                    evidence_found=f'<h1>: "{parsed.h1_tags[0]}" | <h2> count: {h2_count}',
                    suggested_action="Maintain consistent heading hierarchy when adding new sections.",
                )
            )

    # -------------------------------------------------------------
    # 4. Image Alt Text Check
    # -------------------------------------------------------------
    total_images = parsed.total_images
    missing_alt_count = parsed.missing_alt_count

    if total_images == 0:
        findings.append(
            TechnicalFinding(
                id="image_alt_text",
                title="Image Alt Text",
                status="pass",
                summary="No images detected on the page.",
                why_it_matters="Alt text is required for accessibility and image search indexing.",
                evidence_found="0 images found.",
                suggested_action="When adding images, ensure every image includes descriptive alt text.",
            )
        )
    elif missing_alt_count == 0:
        findings.append(
            TechnicalFinding(
                id="image_alt_text",
                title="Image Alt Text",
                status="pass",
                summary=f"All {total_images} images have descriptive alt attributes.",
                why_it_matters="Alt text enables visual search indexing and complies with accessibility standards.",
                evidence_found=f"{total_images} / {total_images} images have alt text.",
                suggested_action="Continue adding alt text to any newly uploaded images.",
            )
        )
    else:
        # Collect affected image URLs
        affected = [img["src"] for img in parsed.images_missing_alt if img.get("src")]
        status_val = "needs_attention" if (missing_alt_count / total_images) < 0.5 else "fail"
        findings.append(
            TechnicalFinding(
                id="image_alt_text",
                title="Image Alt Text",
                status=status_val,
                summary=f"{missing_alt_count} of {total_images} images are missing descriptive alt text.",
                why_it_matters="Search engines cannot interpret image context without alt text, and screen readers cannot read them.",
                evidence_found=f"{missing_alt_count} uncaptioned images detected.",
                suggested_action="Add descriptive, keyword-relevant alt attributes to the affected images.",
                affected_urls=affected[:5],
            )
        )

    # -------------------------------------------------------------
    # 5. robots.txt Check
    # -------------------------------------------------------------
    if fetch_result.robots_txt_present:
        findings.append(
            TechnicalFinding(
                id="robots_txt",
                title="robots.txt File",
                status="pass",
                summary="robots.txt file is present and accessible (HTTP 200).",
                why_it_matters="robots.txt directs search engine crawlers on which sections of your site to index or ignore.",
                evidence_found=f"Accessible at {resolve_url(final_url, '/robots.txt')}",
                suggested_action="Periodically verify that robots.txt does not inadvertently disallow important service pages.",
            )
        )
    else:
        findings.append(
            TechnicalFinding(
                id="robots_txt",
                title="robots.txt File",
                status="needs_attention",
                summary="robots.txt was not found or returned an error.",
                why_it_matters="Without robots.txt, crawlers may index admin pages or waste crawl budget on utility paths.",
                evidence_found=f"HTTP request to /robots.txt failed or was not found.",
                suggested_action="Create a robots.txt file in your root domain allowing search bots to crawl public pages.",
            )
        )

    # -------------------------------------------------------------
    # 6. sitemap.xml Check
    # -------------------------------------------------------------
    if fetch_result.sitemap_xml_present:
        findings.append(
            TechnicalFinding(
                id="sitemap_xml",
                title="XML Sitemap",
                status="pass",
                summary="XML Sitemap is present and accessible (HTTP 200).",
                why_it_matters="Sitemaps help Google quickly discover and index all your service and subpages.",
                evidence_found=f"Accessible at {resolve_url(final_url, '/sitemap.xml')}",
                suggested_action="Keep sitemap automatically updated when new procedure pages are published.",
            )
        )
    else:
        findings.append(
            TechnicalFinding(
                id="sitemap_xml",
                title="XML Sitemap",
                status="needs_attention",
                summary="sitemap.xml was not found at standard root path.",
                why_it_matters="Sitemaps provide search engines with a roadmap of all your site's URLs, accelerating discovery.",
                evidence_found=f"HTTP request to /sitemap.xml returned non-200 status.",
                suggested_action="Generate an XML sitemap and submit it to Google Search Console.",
            )
        )

    # -------------------------------------------------------------
    # 7. HTTPS Security Check
    # -------------------------------------------------------------
    is_https = final_url.lower().startswith("https://")
    if is_https:
        findings.append(
            TechnicalFinding(
                id="https_security",
                title="HTTPS Security",
                status="pass",
                summary="Website is served securely over HTTPS with SSL encryption.",
                why_it_matters="HTTPS is a confirmed Google ranking factor and protects visitor privacy.",
                evidence_found=f"Secure scheme: {final_url}",
                suggested_action="Ensure SSL certificate auto-renews and HTTP-to-HTTPS 301 redirects remain active.",
            )
        )
    else:
        findings.append(
            TechnicalFinding(
                id="https_security",
                title="HTTPS Security",
                status="fail",
                summary="Website is served over insecure HTTP.",
                why_it_matters="Modern browsers mark HTTP sites as 'Not Secure', damaging conversions and search rankings.",
                evidence_found=f"Insecure scheme: {final_url}",
                suggested_action="Install an SSL certificate (e.g. Let's Encrypt or Cloudflare) and enforce HTTPS.",
            )
        )

    # -------------------------------------------------------------
    # 8. Canonical Tag Check
    # -------------------------------------------------------------
    canonical_url = parsed.canonical_url
    if not canonical_url:
        findings.append(
            TechnicalFinding(
                id="canonical_tag",
                title="Canonical Tag",
                status="needs_attention",
                summary="Canonical tag (<link rel='canonical'>) is missing.",
                why_it_matters="Canonical tags prevent duplicate content penalties caused by www vs non-www or trailing slash URL variations.",
                evidence_found="No <link rel='canonical'> detected in <head>.",
                suggested_action=f"Add <link rel='canonical' href='{final_url}'> to prevent duplicate content ambiguity.",
            )
        )
    else:
        # Check domain and protocol consistency
        is_same = is_same_domain(final_url, canonical_url)
        is_canonical_https = canonical_url.lower().startswith("https://")

        if is_same and (is_https == is_canonical_https):
            findings.append(
                TechnicalFinding(
                    id="canonical_tag",
                    title="Canonical Tag",
                    status="pass",
                    summary="Canonical tag is present and internally consistent.",
                    why_it_matters="Directs search engines to index the authoritative URL version of this page.",
                    evidence_found=f"<link rel='canonical' href='{canonical_url}'>",
                    suggested_action="Maintain canonical tag consistency across all subpages.",
                )
            )
        else:
            findings.append(
                TechnicalFinding(
                    id="canonical_tag",
                    title="Canonical Tag",
                    status="needs_attention",
                    summary="Canonical tag URL differs in domain or security scheme from the resolved URL.",
                    why_it_matters="Mismatched canonicals can cause search engines to ignore indexing for the current page.",
                    evidence_found=f"Current URL: {final_url} vs Canonical: {canonical_url}",
                    suggested_action="Update the canonical href attribute to match the authoritative URL.",
                    affected_urls=[canonical_url],
                )
            )

    # -------------------------------------------------------------
    # 9. Mobile Viewport Check
    # -------------------------------------------------------------
    viewport = parsed.viewport_meta
    if not viewport:
        findings.append(
            TechnicalFinding(
                id="mobile_viewport",
                title="Mobile Viewport",
                status="fail",
                summary="Mobile viewport meta tag is missing.",
                why_it_matters="Without a viewport meta tag, mobile devices render pages at desktop scale, failing mobile-first indexing.",
                evidence_found="No <meta name='viewport'> tag detected.",
                suggested_action="Add <meta name='viewport' content='width=device-width, initial-scale=1.0'> to the <head>.",
            )
        )
    elif "width=device-width" in viewport.lower():
        findings.append(
            TechnicalFinding(
                id="mobile_viewport",
                title="Mobile Viewport",
                status="pass",
                summary="Mobile viewport is properly configured for responsive devices.",
                why_it_matters="Google uses mobile-first indexing to rank and render websites on smartphones.",
                evidence_found=f"<meta name='viewport' content='{viewport}'>",
                suggested_action="Ensure all buttons and text maintain 48px+ touch targets and readable fonts.",
            )
        )
    else:
        findings.append(
            TechnicalFinding(
                id="mobile_viewport",
                title="Mobile Viewport",
                status="needs_attention",
                summary="Viewport tag found, but missing standard 'width=device-width' configuration.",
                why_it_matters="Improper viewport values can cause horizontal scrolling or scaling glitches on mobile.",
                evidence_found=f"content='{viewport}'",
                suggested_action="Update viewport tag content to 'width=device-width, initial-scale=1.0'.",
            )
        )

    # -------------------------------------------------------------
    # 10. Context-Aware Structured Data Check
    # -------------------------------------------------------------
    types_found = set(parsed.structured_data_types)

    if category == "healthcare":
        healthcare_matching = types_found.intersection(HEALTHCARE_SCHEMA_TYPES)
        local_matching = types_found.intersection(LOCAL_BUSINESS_SCHEMA_TYPES)

        if healthcare_matching:
            findings.append(
                TechnicalFinding(
                    id="structured_data",
                    title="Structured Data (Schema.org)",
                    status="pass",
                    summary=f"Specialized healthcare structured data ({', '.join(sorted(healthcare_matching))}) is present.",
                    why_it_matters="Healthcare schema enables Google rich results, map pins, and verified clinical entity status.",
                    evidence_found=f"Detected schema types: {parsed.structured_data_types}",
                    suggested_action="Ensure address, telephone, openingHours, and priceRange properties are complete in the JSON-LD.",
                )
            )
        elif local_matching:
            findings.append(
                TechnicalFinding(
                    id="structured_data",
                    title="Structured Data (Schema.org)",
                    status="pass",
                    summary="LocalBusiness schema is present. (Consider refining to MedicalBusiness/Dentist for maximum relevance).",
                    why_it_matters="Enables Google Local pack and map visibility.",
                    evidence_found=f"Detected schema types: {parsed.structured_data_types}",
                    suggested_action="Specialize LocalBusiness to MedicalBusiness or Dentist for richer healthcare entity recognition.",
                )
            )
        elif types_found.intersection(ORGANIZATION_SCHEMA_TYPES):
            findings.append(
                TechnicalFinding(
                    id="structured_data",
                    title="Structured Data (Schema.org)",
                    status="needs_attention",
                    summary="Generic Organization schema found, but missing specialized MedicalBusiness or LocalBusiness markup.",
                    why_it_matters="A local clinic gains significantly higher local map visibility with MedicalBusiness schema than generic Organization.",
                    evidence_found=f"Detected schema types: {parsed.structured_data_types}",
                    suggested_action="Add MedicalBusiness / Dentist schema with clinic address, phone, and opening hours.",
                )
            )
        else:
            findings.append(
                TechnicalFinding(
                    id="structured_data",
                    title="Structured Data (Schema.org)",
                    status="fail",
                    summary="No structured data (schema.org) found on this healthcare/clinic website.",
                    why_it_matters="Missing structured data prevents Google from featuring your clinic in local map packs and rich snippets.",
                    evidence_found="0 schema.org JSON-LD scripts detected.",
                    suggested_action="Add MedicalBusiness or Dentist JSON-LD markup to your homepage.",
                )
            )

    elif category == "local_service":
        local_matching = types_found.intersection(LOCAL_BUSINESS_SCHEMA_TYPES).union(types_found.intersection(HEALTHCARE_SCHEMA_TYPES))

        if local_matching:
            findings.append(
                TechnicalFinding(
                    id="structured_data",
                    title="Structured Data (Schema.org)",
                    status="pass",
                    summary=f"Relevant local service schema ({', '.join(sorted(local_matching))}) is present.",
                    why_it_matters="LocalBusiness schema powers Google Maps integration and local search packs.",
                    evidence_found=f"Detected schema types: {parsed.structured_data_types}",
                    suggested_action="Verify that geo coordinates, address, and telephone are accurate in schema.",
                )
            )
        elif types_found.intersection(ORGANIZATION_SCHEMA_TYPES):
            findings.append(
                TechnicalFinding(
                    id="structured_data",
                    title="Structured Data (Schema.org)",
                    status="needs_attention",
                    summary="Generic Organization schema found, but missing local business markup.",
                    why_it_matters="Local service businesses need LocalBusiness schema to compete for nearby customer searches.",
                    evidence_found=f"Detected schema types: {parsed.structured_data_types}",
                    suggested_action="Add LocalBusiness structured data with service area and contact details.",
                )
            )
        else:
            findings.append(
                TechnicalFinding(
                    id="structured_data",
                    title="Structured Data (Schema.org)",
                    status="fail",
                    summary="No structured data (schema.org) found on this local service business site.",
                    why_it_matters="Competitors with LocalBusiness schema gain prominent placement in local search and map results.",
                    evidence_found="0 schema.org JSON-LD scripts detected.",
                    suggested_action="Add LocalBusiness JSON-LD markup to your homepage.",
                )
            )

    else:
        # General / SaaS / Corporate
        if types_found:
            findings.append(
                TechnicalFinding(
                    id="structured_data",
                    title="Structured Data (Schema.org)",
                    status="pass",
                    summary=f"Structured data ({', '.join(parsed.structured_data_types)}) is present.",
                    why_it_matters="Helps search engines understand entity relationships, brand name, and logo.",
                    evidence_found=f"Detected schema types: {parsed.structured_data_types}",
                    suggested_action="Ensure logo, name, and sameAs social profile links are maintained.",
                )
            )
        else:
            findings.append(
                TechnicalFinding(
                    id="structured_data",
                    title="Structured Data (Schema.org)",
                    status="needs_attention",
                    summary="No structured data found on the website.",
                    why_it_matters="Structured data helps search engines verify your brand identity and knowledge graph entry.",
                    evidence_found="0 schema.org scripts detected.",
                    suggested_action="Add Organization or WebSite JSON-LD structured data.",
                )
            )

    # -------------------------------------------------------------
    # Overall Score & Summary Calculation
    # -------------------------------------------------------------
    passed_count = sum(1 for f in findings if f.status == "pass")
    needs_attention_count = sum(1 for f in findings if f.status == "needs_attention")
    issues_count = sum(1 for f in findings if f.status == "fail")
    total_checks = len(findings)

    # Score calculation out of 100
    if total_checks > 0:
        health_score = int(round(((passed_count * 10) + (needs_attention_count * 5)) / (total_checks * 10) * 100))
    else:
        health_score = 0

    if issues_count == 0 and needs_attention_count == 0:
        summary_text = "Outstanding technical SEO foundation. All core checks passed."
    elif issues_count == 0:
        summary_text = "Good technical foundation with a few recommended optimizations to maximize visibility."
    elif issues_count <= 2:
        summary_text = "Solid foundation, but a few critical issues should be addressed to improve search ranking."
    else:
        summary_text = "Multiple foundational technical SEO issues detected requiring immediate remediation."

    summary = TechnicalSEOSummary(
        passed_count=passed_count,
        needs_attention_count=needs_attention_count,
        issues_count=issues_count,
        total_checks=total_checks,
        health_score=health_score,
        summary_text=summary_text,
    )

    return TechnicalSEOResult(
        summary=summary,
        findings=findings,
        inferred_category=category,
    )
