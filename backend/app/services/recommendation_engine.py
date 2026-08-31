from typing import List, Dict, Any, Optional

from app.models import (
    BusinessContextModel,
    ServiceStructureModel,
    TechnicalFindingModel,
)


def get_title_suggested_action(category: str, has_local_evidence: bool, title_len: int) -> str:
    """Returns context-aware suggested action for page title issues."""
    if title_len == 0:
        if has_local_evidence:
            return "Add a descriptive 30–60 character <title> tag containing your business name, primary service, and location."
        elif category in ("technology", "saas"):
            return "Add a descriptive 30–60 character <title> tag communicating your product/platform name and core capability."
        else:
            return "Add a descriptive 30–60 character <title> tag clearly describing the page's primary purpose and content."
    elif title_len < 25:
        if has_local_evidence:
            return "Consider including the business name, primary service, and relevant location where appropriate."
        elif category in ("technology", "saas", "professional_services", "ecommerce"):
            return "Consider including the business or product name and primary service or value proposition."
        else:
            return "Expand the title to clearly describe the page's primary purpose and content."
    else:
        return "Shorten title to between 30 and 60 characters to prevent search engine truncation."


def get_meta_desc_suggested_action(category: str, has_local_evidence: bool, is_missing: bool) -> str:
    """Returns context-aware suggested action for meta description."""
    if is_missing:
        if has_local_evidence:
            return "Add a compelling 120–160 character meta description outlining your services, local service area, and call to action."
        elif category in ("technology", "saas"):
            return "Add a concise 120–160 character description summarizing your software capabilities and primary value proposition."
        else:
            return "Add a compelling 120–160 character meta description outlining your primary offerings and call to action."
    else:
        return "Optimize meta description length to between 120 and 160 characters with a clear call to action."


def get_structured_data_suggested_action(category: str, has_local_evidence: bool) -> str:
    """Returns context-aware suggested action for schema.org structured data."""
    if category == "healthcare":
        return "Add MedicalBusiness or Dentist JSON-LD markup to your homepage."
    elif has_local_evidence or category in ("local_business", "restaurant"):
        return "Add LocalBusiness JSON-LD markup with verified address, phone, and opening hours."
    elif category in ("technology", "saas"):
        return "Add SoftwareApplication, WebSite, or Organization JSON-LD markup."
    elif category == "ecommerce":
        return "Add Product and AggregateOffer JSON-LD structured data."
    elif category == "hospitality":
        return "Add Hotel or LodgingBusiness JSON-LD structured data."
    else:
        return "Add Organization or WebSite JSON-LD structured data to establish verified entity identity."


def generate_strategic_projects(
    business_context: BusinessContextModel,
    has_local_evidence: bool,
    services_structure: Optional[ServiceStructureModel] = None,
    is_blocked: bool = False,
    competitors: Optional[Any] = None,
) -> List[Dict[str, Any]]:
    """
    Generates tailored, context-aware strategic long-term projects (Bigger Projects).
    Never recommends Google Reviews or Google Business Profile unless verified local evidence exists.
    """
    projects: List[Dict[str, Any]] = []
    cat = business_context.category

    # 1. WAF / Bot challenge
    if is_blocked:
        projects.append({
            "id": "bp-waf-policy",
            "title": "Audit CDN & WAF search engine crawler whitelist policies",
            "impact": "High",
            "estimatedEffort": "1–2 days",
            "why": "Review CDN/WAF logs and verified bot rules to confirm that legitimate search engine crawlers (Googlebot, Bingbot) can access public content.",
        })

    # 2. Local Business Projects (Strictly gated by local evidence)
    if has_local_evidence:
        projects.append({
            "id": "bp-local-gmb",
            "title": "Optimize Google Business Profile and local citation consistency",
            "impact": "High",
            "estimatedEffort": "1–2 weeks",
            "why": "Local map pack rankings and nearby customer conversions depend heavily on verified Google Business Profile signals and citation accuracy.",
        })
        
        review_why = "Customer reviews and response rates on Google Maps directly influence local search prominence and client trust."
        if competitors and getattr(competitors, "status", None) == "available" and competitors.competitors:
            avg_reviews = sum(c.review_count for c in competitors.competitors if c.review_count) // max(1, sum(1 for c in competitors.competitors if c.review_count))
            if avg_reviews > 10:
                review_why = f"Top local competitors in {competitors.search_location or 'your area'} average ~{avg_reviews} Google reviews. A systematic review collection workflow strengthens local map pack prominence."

        projects.append({
            "id": "bp-local-reviews",
            "title": "Establish a systematic Google Review collection workflow",
            "impact": "High",
            "estimatedEffort": "1–2 weeks",
            "why": review_why,
        })

    # 3. Technology / SaaS / AI Projects
    elif cat in ("technology", "saas"):
        projects.append({
            "id": "bp-tech-solutions",
            "title": "Build dedicated solution and use-case landing pages",
            "impact": "High",
            "estimatedEffort": "2–4 weeks",
            "why": "Enterprise buyers and engineering teams search by specific use cases, integrations, and pain points rather than broad category terms.",
        })
        projects.append({
            "id": "bp-tech-docs",
            "title": "Publish technical thought leadership, documentation, and case studies",
            "impact": "High",
            "estimatedEffort": "2–3 weeks",
            "why": "In-depth architecture overviews, developer guides, and verifiable client case studies drive high-intent organic B2B search traffic.",
        })

    # 4. Hospitality / Travel Projects
    elif cat == "hospitality":
        projects.append({
            "id": "bp-hosp-booking",
            "title": "Optimize direct room booking funnel and accommodation schema",
            "impact": "High",
            "estimatedEffort": "2–3 weeks",
            "why": "Direct reservations generate higher margin and capture search queries for luxury rooms, suites, and venue amenities.",
        })
        projects.append({
            "id": "bp-hosp-local-guides",
            "title": "Create localized destination and area attraction guides",
            "impact": "Medium",
            "estimatedEffort": "2–4 weeks",
            "why": "Travelers frequently search for area guides, dining, and local experiences when selecting luxury hotels and resorts.",
        })

    # 5. Professional Services Projects
    elif cat == "professional_services":
        projects.append({
            "id": "bp-prof-expertise",
            "title": "Develop dedicated practice area and consultant profile pages",
            "impact": "High",
            "estimatedEffort": "2–3 weeks",
            "why": "Prospective advisory clients evaluate individual partner credentials, proven track records, and niche practice specialization.",
        })

    # 6. E-Commerce Projects
    elif cat == "ecommerce":
        projects.append({
            "id": "bp-ecom-categories",
            "title": "Enhance category taxonomy, faceted navigation, and product schema",
            "impact": "High",
            "estimatedEffort": "2–4 weeks",
            "why": "Search engines require structured category hierarchies and rich snippet pricing data to index large e-commerce catalogs.",
        })

    # 7. Service Architecture (if homepage-centric and services exist)
    if services_structure and not services_structure.has_dedicated_service_pages and not is_blocked:
        projects.append({
            "id": "bp-dedicated-pages",
            "title": "Build dedicated landing pages for individual service offerings",
            "impact": "High",
            "estimatedEffort": "2–4 weeks",
            "why": "Dedicated service subpages enable search engines to rank specific offerings for high-intent user searches.",
        })

    # 8. Fallback / Universal Project if list is too small
    if len(projects) < 2:
        projects.append({
            "id": "bp-content-depth",
            "title": "Expand content depth and topic authority across core pages",
            "impact": "Medium",
            "estimatedEffort": "2–3 weeks",
            "why": "Comprehensive content addressing user search intent improves organic search rankings and topical authority.",
        })

    return projects[:3]
