import re
from typing import List, Dict, Any, Optional, Tuple, Set

from app.models import (
    BusinessContextModel,
    AudienceContextModel,
    ContextIntelligenceResultModel,
    ParsedHTMLModel,
    RawFetchData,
    ContentAnalysisResultModel,
)

# Taxonomy definitions with schema types, exact keyword matches, and topic phrase patterns
CATEGORY_SIGNALS = {
    "technology": {
        "schemas": {"SoftwareApplication", "WebApplication", "TechArticle", "APIReference"},
        "keywords": [
            "ai", "artificial intelligence", "machine learning", "deep learning", "neural",
            "automation", "software", "cloud", "api", "developer", "platform", "analytics",
            "data platform", "infrastructure", "devops", "cybersecurity", "database", "llm",
            "enterprise software", "sdk", "algorithm", "data lake", "data science"
        ],
        "label": "Technology & Software",
    },
    "saas": {
        "schemas": {"SoftwareApplication", "WebApplication"},
        "keywords": [
            "saas", "software as a service", "pricing plan", "monthly subscription", "free trial",
            "cloud software", "b2b software", "dashboard", "integrations", "enterprise plan", "sign up free"
        ],
        "label": "SaaS & Cloud Software",
    },
    "healthcare": {
        "schemas": {
            "MedicalBusiness", "Dentist", "Physician", "MedicalClinic", "Hospital",
            "Pharmacy", "DiagnosticLab", "MedicalCondition", "HealthAndBeautyBusiness"
        },
        "keywords": [
            "dental", "dentist", "teeth", "clinic", "doctor", "physician", "orthodont",
            "medical", "hospital", "surgery", "patient", "health", "therapy", "chiropract",
            "optometr", "pediatric", "implant", "invisalign", "dermatol", "healthcare"
        ],
        "label": "Healthcare & Medical Services",
    },
    "hospitality": {
        "schemas": {"Hotel", "LodgingBusiness", "Resort", "Motel", "Hostel", "BedAndBreakfast"},
        "keywords": [
            "hotel", "hotels", "resort", "resorts", "luxury hotel", "suites", "rooms",
            "palace", "villas", "check-in", "check-out", "concierge", "accommodation",
            "hospitality", "stay with us", "room booking"
        ],
        "label": "Hospitality & Lodging",
    },
    "restaurant": {
        "schemas": {"Restaurant", "FoodEstablishment", "CafeOrCoffeeShop", "BarOrPub", "Bakery", "FastFoodRestaurant"},
        "keywords": [
            "menu", "dining", "cuisine", "chef", "dishes", "wine", "cocktails", "breakfast",
            "lunch", "dinner", "reservations", "takeaway", "appetizers", "entrees", "restaurant", "cafe"
        ],
        "label": "Restaurant & Dining",
    },
    "local_business": {
        "schemas": {
            "LocalBusiness", "AutomotiveBusiness", "AutoRepair", "HomeAndConstructionBusiness",
            "Plumber", "HVACBusiness", "Electrician", "RoofingContractor", "BeautySalon",
            "HairSalon", "DryCleaningOrLaundry", "Locksmith"
        },
        "keywords": [
            "auto repair", "mechanic", "plumber", "plumbing", "hvac", "electrician",
            "roofing", "contractor", "pest control", "locksmith", "towing", "landscaping",
            "garage", "car care", "oil change", "emergency service", "near you"
        ],
        "label": "Local Trade & Service Business",
    },
    "professional_services": {
        "schemas": {"LegalService", "Attorney", "AccountingService", "FinancialService", "ConsultingService"},
        "keywords": [
            "law firm", "attorney", "lawyer", "legal services", "litigation", "accounting",
            "tax consulting", "financial advisory", "cpa", "management consulting", "advisory services",
            "wealth management", "audit firm"
        ],
        "label": "Professional & Advisory Services",
    },
    "ecommerce": {
        "schemas": {"Product", "Offer", "AggregateOffer", "Store", "ItemAvailability"},
        "keywords": [
            "add to cart", "buy now", "shop now", "free shipping", "checkout", "price",
            "cart", "discount code", "order now", "product catalog", "store"
        ],
        "label": "E-Commerce & Online Retail",
    },
    "education": {
        "schemas": {"EducationalOrganization", "School", "CollegeOrUniversity", "Course"},
        "keywords": [
            "university", "college", "school", "academy", "curriculum", "students",
            "admissions", "tuition", "degrees", "courses", "faculty", "campus"
        ],
        "label": "Education & Academic Institution",
    },
    "nonprofit": {
        "schemas": {"NGO", "NonprofitOrganization"},
        "keywords": [
            "non-profit", "nonprofit", "charity", "donate", "donation", "volunteer",
            "foundation", "mission", "advocacy", "501(c)(3)", "philanthropy"
        ],
        "label": "Non-Profit & Community Organization",
    },
}


def classify_business_context(
    parsed: Optional[ParsedHTMLModel],
    url: str = "",
    content_analysis: Optional[ContentAnalysisResultModel] = None,
    is_blocked: bool = False,
) -> BusinessContextModel:
    """
    Deterministically infers the business category and industry from observable evidence.
    Does NOT rely primarily on domain name. If evidence is insufficient, returns "unknown".
    """
    if is_blocked or not parsed:
        return BusinessContextModel(
            category="unknown",
            confidence="low",
            evidence=["Automated crawler access was challenged; observable page content was inaccessible."],
            reliability="inconclusive",
        )

    # Collect observable text pieces
    title = (parsed.title or "").lower()
    meta_desc = (parsed.meta_description or "").lower()
    h1s = [h.lower() for h in (parsed.h1_tags or [])]
    h2s = [h.lower() for h in (parsed.h2_tags or [])]
    h3s = [h.lower() for h in (parsed.h3_tags or [])]
    headings_text = " ".join(h1s + h2s + h3s)
    snippet = (parsed.visible_text_snippet or "").lower()
    word_count = parsed.visible_word_count or 0

    # Collect schema types
    schema_types = set(parsed.structured_data_types or [])

    # Check for empty or illustrative/generic pages (e.g. example.com)
    is_illustrative_or_empty = (
        word_count < 60 and ("illustrative" in snippet or "example domain" in title or "example.com" in url)
    )
    if is_illustrative_or_empty:
        return BusinessContextModel(
            category="unknown",
            confidence="low",
            evidence=["Insufficient observable commercial or industry content (illustrative or empty page)."],
            reliability="limited",
        )

    scores: Dict[str, int] = {}
    evidence_map: Dict[str, List[str]] = {}

    for cat_key, cat_data in CATEGORY_SIGNALS.items():
        score = 0
        evidences: List[str] = []

        # 1. Check Schema.org types (Weight: +3)
        matching_schemas = schema_types.intersection(cat_data["schemas"])
        if matching_schemas:
            score += 3
            evidences.append(f"Structured Data Schema type(s): {', '.join(sorted(matching_schemas))}")

        # 2. Check Title (Weight: +2)
        title_matches = [kw for kw in cat_data["keywords"] if re.search(rf"\b{re.escape(kw)}\b", title)]
        if title_matches:
            score += 2
            evidences.append(f"Page title references {', '.join(title_matches[:2])}")

        # 3. Check Headings (Weight: +2)
        heading_matches = [kw for kw in cat_data["keywords"] if re.search(rf"\b{re.escape(kw)}\b", headings_text)]
        if heading_matches:
            score += 2
            evidences.append(f"Headings mention {', '.join(heading_matches[:3])}")

        # 4. Check Meta Description (Weight: +1)
        meta_matches = [kw for kw in cat_data["keywords"] if re.search(rf"\b{re.escape(kw)}\b", meta_desc)]
        if meta_matches:
            score += 1
            evidences.append(f"Meta description contains {', '.join(meta_matches[:2])}")

        # 5. Check Visible Text Snippet (Weight: +1 per multiple occurrences)
        snippet_matches = [kw for kw in cat_data["keywords"] if re.search(rf"\b{re.escape(kw)}\b", snippet)]
        if len(snippet_matches) >= 2:
            score += 2
            evidences.append(f"Visible body text repeatedly discusses {', '.join(snippet_matches[:3])}")
        elif len(snippet_matches) == 1:
            score += 1

        if score > 0:
            scores[cat_key] = score
            evidence_map[cat_key] = evidences

    if not scores:
        return BusinessContextModel(
            category="unknown",
            confidence="low",
            evidence=["Insufficient observable keywords or schema markup to classify business category."],
            reliability="limited",
        )

    # Sort categories by score
    sorted_cats = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    best_cat, best_score = sorted_cats[0]
    best_evidences = evidence_map.get(best_cat, [])

    # Threshold checks for confidence
    if best_score >= 5 and len(best_evidences) >= 2:
        confidence = "high"
        reliability = "reliable"
    elif best_score >= 3:
        confidence = "medium"
        reliability = "reliable"
    else:
        # Score is too weak or solitary keyword match
        return BusinessContextModel(
            category="unknown",
            confidence="low",
            evidence=[f"Weak signals detected ({', '.join(best_evidences)}) but insufficient to reliably categorize."],
            reliability="limited",
        )

    return BusinessContextModel(
        category=best_cat,
        confidence=confidence,
        evidence=best_evidences[:4],
        reliability=reliability,
    )


def infer_target_audience(
    business_context: BusinessContextModel,
    parsed: Optional[ParsedHTMLModel],
    content_analysis: Optional[ContentAnalysisResultModel] = None,
    is_blocked: bool = False,
) -> AudienceContextModel:
    """
    Deterministically derives the target audience from business category, visible offerings, and customer cues.
    Never invents demographics or assumes local customers without evidence.
    """
    if is_blocked:
        return AudienceContextModel(
            target_audience="Inconclusive",
            confidence="low",
            evidence=["Automated access was challenged; audience cannot be determined."],
            reliability="inconclusive",
        )

    cat = business_context.category
    conf = business_context.confidence

    if cat == "unknown" or conf == "low" or not parsed:
        return AudienceContextModel(
            target_audience="Inconclusive",
            confidence="low",
            evidence=["Insufficient observable website content to reliably determine the intended audience."],
            reliability="inconclusive",
        )

    snippet = (parsed.visible_text_snippet or "").lower()
    address = content_analysis.contact_info.address if content_analysis else None

    # Check for local business cues
    if cat in ("local_business", "healthcare", "restaurant"):
        if address:
            return AudienceContextModel(
                target_audience=f"Local residents and clients in {address} seeking {cat.replace('_', ' ')} services",
                confidence="high",
                evidence=[
                    f"Confirmed physical business address: '{address}'",
                    f"Industry classification: {cat}",
                ],
                reliability="reliable",
            )
        else:
            return AudienceContextModel(
                target_audience=f"Patients and local clients seeking {cat.replace('_', ' ')} services",
                confidence="medium",
                evidence=[f"Observed {cat} terminology in website structure"],
                reliability="reliable",
            )

    if cat in ("technology", "saas"):
        is_enterprise = any(w in snippet for w in ["enterprise", "b2b", "compliance", "teams", "organizations", "data teams"])
        if is_enterprise:
            return AudienceContextModel(
                target_audience="Engineering teams, technical decision-makers, and enterprise organizations evaluating software and AI solutions",
                confidence=conf,
                evidence=business_context.evidence + ["Enterprise/B2B terminology detected in website content"],
                reliability="reliable",
            )
        else:
            return AudienceContextModel(
                target_audience="Businesses, technical professionals, and developers looking for software and automation platforms",
                confidence=conf,
                evidence=business_context.evidence,
                reliability="reliable",
            )

    if cat == "hospitality":
        return AudienceContextModel(
            target_audience="Travelers, tourists, and guests seeking hotel accommodations, luxury suites, and hospitality experiences",
            confidence=conf,
            evidence=business_context.evidence,
            reliability="reliable",
        )

    if cat == "professional_services":
        return AudienceContextModel(
            target_audience="Corporate clients and individuals requiring specialized legal, financial, or management advisory services",
            confidence=conf,
            evidence=business_context.evidence,
            reliability="reliable",
        )

    if cat == "ecommerce":
        return AudienceContextModel(
            target_audience="Online consumers and retail shoppers looking to purchase products online",
            confidence=conf,
            evidence=business_context.evidence,
            reliability="reliable",
        )

    if cat == "education":
        return AudienceContextModel(
            target_audience="Prospective students, parents, and academic professionals seeking degree programs and courses",
            confidence=conf,
            evidence=business_context.evidence,
            reliability="reliable",
        )

    if cat == "nonprofit":
        return AudienceContextModel(
            target_audience="Donors, volunteers, community partners, and beneficiaries supporting the organization's mission",
            confidence=conf,
            evidence=business_context.evidence,
            reliability="reliable",
        )

    return AudienceContextModel(
        target_audience="Inconclusive",
        confidence="low",
        evidence=["Insufficient observable signals to reliably characterize target audience."],
        reliability="inconclusive",
    )


def evaluate_context_intelligence(
    fetch_data: Optional[RawFetchData],
    content_analysis: Optional[ContentAnalysisResultModel] = None,
) -> ContextIntelligenceResultModel:
    """
    Primary entrypoint for evaluating context intelligence (business categorization & audience inference).
    """
    is_blocked = (
        fetch_data is None
        or not getattr(fetch_data, "content_accessible", True)
        or fetch_data.error_type == "bot_protection_detected"
        or (fetch_data.status_code in (403, 429))
    )

    parsed = fetch_data.parsed_data if fetch_data else None
    url = fetch_data.final_url if fetch_data else ""

    business_ctx = classify_business_context(
        parsed=parsed,
        url=url,
        content_analysis=content_analysis,
        is_blocked=is_blocked,
    )

    audience_ctx = infer_target_audience(
        business_context=business_ctx,
        parsed=parsed,
        content_analysis=content_analysis,
        is_blocked=is_blocked,
    )

    return ContextIntelligenceResultModel(
        business_context=business_ctx,
        audience_context=audience_ctx,
    )
