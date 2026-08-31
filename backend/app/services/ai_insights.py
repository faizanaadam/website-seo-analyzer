import asyncio
import json
import logging
import random
import re
import time
from typing import Optional, Dict, Any, List, Set, Tuple
import httpx

from app.config import settings
from app.models import (
    AIAnalysisResultModel,
    AIRecommendationModel,
    TechnicalSEOResultModel,
    ContentAnalysisResultModel,
    PageSpeedResultModel,
    RawFetchData,
)
from app.services.failure_types import FailureCategory, get_user_message

logger = logging.getLogger(__name__)

OPENAI_CHAT_ENDPOINT = "https://api.openai.com/v1/chat/completions"

SYSTEM_PROMPT = """You are an expert Technical SEO and Growth Strategist for the Website SEO & Visibility Analyser.

Your objective is to interpret the supplied deterministic website audit data and generate an executive-level, business-friendly analysis.

CRITICAL ANTI-HALLUCINATION & INTEGRITY RULES:
1. Grounding & Deterministic Context: The payload includes deterministic "business_context", "service_context", and "audience_context". You MUST treat this deterministic context as factual ground truth. You must NOT override the business category, or invent services, customer demographics, physical locations, local presence, or competitors.
2. Local SEO Gating: Do NOT recommend Google Business Profile (GBP), Google Maps, or local customer reviews unless "has_local_presence" is TRUE or "business_context.category" is explicitly local_business / healthcare / restaurant. For technology, SaaS, eCommerce, and unknown businesses, recommend digital, technical, content, or solution-oriented initiatives.
3. Fact vs Interpretation: Clearly distinguish observed FACTS (what was detected), INTERPRETATION (why it matters to the business), and RECOMMENDATIONS (specific actions to take).
4. No False Penalties or Guarantees: Do NOT claim Google penalties without direct evidence. Do NOT promise guaranteed #1 rankings or specific numeric revenue gains.
5. Limitations & Blocked Access: If the website returned an HTTP 403, 429, or bot protection challenge (content_accessible is false), state: "Automated access was challenged by edge security. We could not verify whether verified search engine crawlers such as Googlebot or Bingbot experience the same restriction." Recommend reviewing CDN/WAF logs and verified bot policies. Do NOT claim that search engine bots are definitely blocked, and do not recommend on-page content fixes.
6. Anchor IDs: When recommending an action for a specific technical or content issue, include the exact "anchor_finding_id" (e.g. "bot_protection_detected", "image_alt_tags", "meta_description", "schema_org", "dedicated_service_pages_missing", "pagespeed_performance").

OUTPUT FORMAT:
You MUST respond with a valid JSON object strictly matching this schema:
{
  "status": "available",
  "overall_assessment": "excellent" | "good" | "moderate" | "needs_improvement" | "critical",
  "executive_summary": "<Concise 2-3 sentence executive assessment tailored to the business>",
  "top_priorities": [
    {
      "title": "<Concise recommendation title>",
      "priority": "critical" | "high" | "medium" | "low",
      "category": "technical_seo" | "content" | "performance" | "visibility" | "conversion",
      "explanation": "<Why this finding was flagged based on the data>",
      "business_impact": "<How addressing this helps organic search visibility or conversions>",
      "recommended_action": "<Clear, step-by-step action>",
      "estimated_effort": "quick" | "moderate" | "significant",
      "anchor_finding_id": "<ID of the finding being addressed or null>"
    }
  ],
  "quick_wins": [
    "<Actionable quick fix supported by findings 1>",
    "<Actionable quick fix supported by findings 2>"
  "quickWins": ["<1-2 quick win actions that can be done in under a day>"],
  "strengths": ["<2-3 genuine strengths confirmed in the audit data>"],
  "limitations": ["<Any caveats or external data gaps>"]
}"""

# Keywords used to match AI recommendation topics to deterministic check IDs
TOPIC_KEYWORDS = {
    "title_tag": ["title tag", "meta title", "page title", "title length", "optimize title", "change title"],
    "meta_description": ["meta description", "meta desc", "description tag", "description length", "add a meta description"],
    "ssl_https": ["https", "ssl", "tls", "security certificate", "secure protocol"],
    "https_ssl": ["https", "ssl", "tls", "security certificate", "secure protocol"],
    "canonical_url": ["canonical", "rel=canonical", "canonical tag", "duplicate url"],
    "mobile_viewport": ["viewport", "mobile responsive", "mobile viewport", "mobile readiness"],
    "h1_heading": ["h1", "heading structure", "main heading", "h1 tag", "heading tag"],
    "image_alt_tags": ["alt tag", "alt text", "alt attribute", "image accessibility", "image alt", "images missing alt"],
    "schema_org": ["schema", "structured data", "json-ld", "microdata", "rich snippet", "localbusiness"],
    "robots_txt": ["robots.txt", "robots txt"],
    "sitemap_xml": ["sitemap.xml", "xml sitemap", "sitemap"],
    "dedicated_service_pages_missing": ["service page", "procedure page", "dedicated page", "service subpage", "individual service"],
    "content_thin_homepage": ["thin content", "word count", "content depth", "homepage copy", "more copy", "homepage word"],
    "cta_missing": ["cta", "call to action", "call-to-action", "phone link", "booking link", "contact form", "appointment", "online booking"],
    "address_missing": ["address", "physical location", "street address", "google maps"],
    "pagespeed_performance": ["pagespeed", "core web vitals", "lcp", "cls", "tbt", "inp", "fcp", "page speed", "loading speed", "slow mobile"],
    "bot_protection_detected": ["bot protection", "waf", "firewall", "akamai", "cloudflare", "challenge", "403 forbidden", "crawler access", "bot access", "whitelist"],
    "competitor_review_gap": ["review", "reviews", "google maps", "competitors", "local competition", "reputation"],
}


class GroundingEvidenceRegistry:
    """
    Allowed-evidence registry built strictly from deterministic evaluation results.
    Tracks observed deficiencies, passed checks, and confirmed strengths.
    """
    def __init__(
        self,
        technical_seo: Optional[TechnicalSEOResultModel] = None,
        content_analysis: Optional[ContentAnalysisResultModel] = None,
        pagespeed: Optional[PageSpeedResultModel] = None,
        fetch_data: Optional[RawFetchData] = None,
        competitors: Optional[CompetitorAnalysisModel] = None,
    ):
        self.deficiencies: Dict[str, Dict[str, Any]] = {}
        self.passed_checks: Dict[str, Dict[str, Any]] = {}
        self.confirmed_strengths: List[str] = []

        is_blocked = (
            (fetch_data and (not fetch_data.content_accessible or fetch_data.error_type == "bot_protection_detected" or fetch_data.status_code in (403, 429)))
            or (content_analysis and content_analysis.is_inconclusive)
            or (technical_seo and technical_seo.summary.is_content_blocked)
        )

        # 1. Technical SEO checks
        if technical_seo:
            for f in technical_seo.findings:
                # Do not register inconclusive findings as real deficiencies of the site
                if getattr(f, "is_inconclusive", False):
                    continue

                if f.status in ("fail", "needs_attention"):
                    self.deficiencies[f.id] = {
                        "id": f.id,
                        "title": f.title,
                        "status": f.status,
                        "summary": f.summary,
                        "suggested_action": f.suggested_action,
                        "category": "technical_seo",
                    }
                elif f.status == "pass":
                    self.passed_checks[f.id] = {
                        "id": f.id,
                        "title": f.title,
                        "summary": f.summary,
                        "category": "technical_seo",
                    }
                    self.confirmed_strengths.append(f"{f.title}: Confirmed passing in technical audit")

        # 2. Content Analysis deficiencies / strengths (only if content was reliably accessible)
        if content_analysis and not is_blocked:
            if not content_analysis.services_structure.has_dedicated_service_pages:
                self.deficiencies["dedicated_service_pages_missing"] = {
                    "id": "dedicated_service_pages_missing",
                    "title": "Dedicated Service Pages",
                    "status": "needs_attention",
                    "summary": "Services are presented primarily on a single page.",
                    "suggested_action": "Create dedicated individual pages for core services.",
                    "category": "content",
                }
            else:
                self.passed_checks["dedicated_service_pages_missing"] = {"title": "Dedicated Service Pages Present"}
                self.confirmed_strengths.append("Dedicated landing pages for individual services")

            if content_analysis.homepage_word_count < 300:
                self.deficiencies["content_thin_homepage"] = {
                    "id": "content_thin_homepage",
                    "title": "Homepage Word Count",
                    "status": "needs_attention",
                    "summary": f"Homepage word count ({content_analysis.homepage_word_count} words) is below recommended depth.",
                    "suggested_action": "Expand homepage copy with detailed descriptions and FAQs.",
                    "category": "content",
                }
            else:
                self.passed_checks["content_thin_homepage"] = {"title": "Comprehensive Content Depth"}
                self.confirmed_strengths.append(f"Healthy homepage copy depth ({content_analysis.homepage_word_count} words)")

            has_cta = bool(
                content_analysis.ctas.phones
                or content_analysis.ctas.emails
                or content_analysis.ctas.booking_providers
                or content_analysis.ctas.whatsapp
            )
            if not has_cta:
                self.deficiencies["cta_missing"] = {
                    "id": "cta_missing",
                    "title": "Direct Conversion CTAs",
                    "status": "needs_attention",
                    "summary": "No direct phone, email, or online appointment booking CTA detected.",
                    "suggested_action": "Add prominent click-to-call phone and booking call-to-actions.",
                    "category": "conversion",
                }
            else:
                self.passed_checks["cta_missing"] = {"title": "Active Contact / Booking CTAs"}
                self.confirmed_strengths.append("Direct contact and booking pathways present")

            if not content_analysis.contact_info.address:
                self.deficiencies["address_missing"] = {
                    "id": "address_missing",
                    "title": "Physical Address",
                    "status": "needs_attention",
                    "summary": "No physical address found in structured data or visible copy.",
                    "suggested_action": "Add complete physical address to footer and Schema markup.",
                    "category": "visibility",
                }
            else:
                self.passed_checks["address_missing"] = {"title": "Physical Address Detected"}
                self.confirmed_strengths.append("Verified physical business address")

        # 3. PageSpeed Deficiencies / Strengths
        if pagespeed and pagespeed.status == "available":
            score = pagespeed.performance_score
            if score is not None:
                if score < 85:
                    self.deficiencies["pagespeed_performance"] = {
                        "id": "pagespeed_performance",
                        "title": "Google PageSpeed Performance",
                        "status": "fail" if score < 50 else "needs_attention",
                        "summary": f"Mobile performance score is {score}/100.",
                        "suggested_action": "Optimize images and defer render-blocking JavaScript.",
                        "category": "performance",
                    }
                else:
                    self.passed_checks["pagespeed_performance"] = {"title": "Fast Mobile Performance"}
                    self.confirmed_strengths.append(f"Fast Google PageSpeed mobile score ({score}/100)")

        # 4. Bot Protection Challenge
        if is_blocked:
            self.deficiencies["bot_protection_detected"] = {
                "id": "bot_protection_detected",
                "title": "Bot Protection & Crawler Access (WAF)",
                "status": "needs_attention",
                "summary": "Edge security firewall returned a challenge or blocked response on crawler access.",
                "suggested_action": "Ensure search engine crawlers (Googlebot, Bingbot) are whitelisted in CDN/WAF rules.",
                "category": "technical_seo",
            }

        # 5. Competitor Intelligence Evidence (from Google Places)
        if competitors and competitors.status == "available" and competitors.competitors:
            comp_count = len(competitors.competitors)
            self.confirmed_strengths.append(f"Mapped {comp_count} comparable local competitors via Google Places")
            reviews = [c.review_count for c in competitors.competitors if c.review_count is not None]
            if reviews:
                avg_rev = sum(reviews) // len(reviews)
                if avg_rev >= 15:
                    self.deficiencies["competitor_review_gap"] = {
                        "id": "competitor_review_gap",
                        "title": "Local Competitor Review Presence",
                        "status": "needs_attention",
                        "summary": f"Local competitors average ~{avg_rev} Google reviews.",
                        "suggested_action": "Implement a proactive Google Review collection workflow to match local market prominence.",
                        "category": "visibility",
                    }


def match_text_to_check_id(text: str) -> Optional[str]:
    """Matches text against topic keywords to identify relevant check ID."""
    lower_text = text.lower()
    for check_id, keywords in TOPIC_KEYWORDS.items():
        for kw in keywords:
            if kw in lower_text:
                return check_id
    return None


def post_validate_ai_insights(
    ai_result: AIAnalysisResultModel,
    registry: GroundingEvidenceRegistry,
) -> AIAnalysisResultModel:
    """
    Deterministic post-validation layer:
    1. Validates every AI recommendation against active deficiencies.
    2. Drops recommendations that contradict passed checks (e.g. recommending SSL fix when SSL is valid).
    3. Resolves and assigns anchor_finding_id.
    4. Validates strengths against actual passed checks and confirmed positive metrics.
    5. Validates quick wins against grounded findings.
    6. Ensures fail-safe fallback without crashing the analysis.
    """
    try:
        if ai_result.status != "available":
            return ai_result

        # =========================================================================
        # 1. GROUND TOP PRIORITIES / RECOMMENDATIONS
        # =========================================================================
        grounded_priorities: List[AIRecommendationModel] = []

        for rec in ai_result.top_priorities:
            combined_text = f"{rec.title} {rec.explanation} {rec.recommended_action} {rec.anchor_finding_id or ''}"
            detected_id = rec.anchor_finding_id if (rec.anchor_finding_id in registry.deficiencies or rec.anchor_finding_id in registry.passed_checks) else match_text_to_check_id(combined_text)

            # Contradiction check: Is this recommendation trying to fix an already PASSED check?
            if detected_id and detected_id in registry.passed_checks and detected_id not in registry.deficiencies:
                logger.info(f"Discarding contradictory AI recommendation targeting passed check '{detected_id}': {rec.title}")
                continue

            # Grounding check: Does this recommendation correspond to an actual deficiency?
            if detected_id and detected_id in registry.deficiencies:
                rec.anchor_finding_id = detected_id
                grounded_priorities.append(rec)
            else:
                logger.info(f"Discarding ungrounded AI recommendation without deterministic anchor: {rec.title}")
                continue

        # Fallback if all AI recommendations were filtered out as hallucinations/contradictions
        if not grounded_priorities and registry.deficiencies:
            for def_id, def_info in list(registry.deficiencies.items())[:3]:
                grounded_priorities.append(
                    AIRecommendationModel(
                        title=f"Address {def_info['title']}",
                        priority="high" if def_info.get("status") == "fail" else "medium",
                        category=def_info.get("category", "technical_seo"),
                        explanation=def_info.get("summary", "Flagged during website audit."),
                        business_impact="Addressing this issue directly improves search visibility and user experience.",
                        recommended_action=def_info.get("suggested_action", "Implement suggested fix."),
                        estimated_effort="moderate",
                        anchor_finding_id=def_id,
                    )
                )

        # =========================================================================
        # 2. GROUND STRENGTHS
        # =========================================================================
        grounded_strengths: List[str] = []

        for strength_text in ai_result.strengths:
            detected_id = match_text_to_check_id(strength_text)

            # Contradiction check: Does this strength claim a check that actually FAILED?
            if detected_id and detected_id in registry.deficiencies:
                logger.info(f"Discarding false AI strength claiming failed check '{detected_id}': {strength_text}")
                continue

            # Verification check: Does this strength align with passed checks or general site structure?
            if detected_id and detected_id in registry.passed_checks:
                grounded_strengths.append(strength_text)
            elif not detected_id and any(cs.lower() in strength_text.lower() for cs in ["https", "ssl", "mobile", "responsive", "content", "clear", "clean"]):
                # Retain plausible positive statements that don't contradict deficiencies
                grounded_strengths.append(strength_text)
            elif detected_id is None:
                grounded_strengths.append(strength_text)

        # Fallback if all strengths were discarded
        if not grounded_strengths and registry.confirmed_strengths:
            grounded_strengths = registry.confirmed_strengths[:4]

        # =========================================================================
        # 3. GROUND QUICK WINS
        # =========================================================================
        grounded_quick_wins: List[str] = []

        for qw in ai_result.quick_wins:
            detected_id = match_text_to_check_id(qw)
            # Contradiction check
            if detected_id and detected_id in registry.passed_checks and detected_id not in registry.deficiencies:
                logger.info(f"Discarding contradictory quick win targeting passed check '{detected_id}': {qw}")
                continue

            if detected_id and detected_id in registry.deficiencies:
                grounded_quick_wins.append(qw)
            elif not detected_id:
                grounded_quick_wins.append(qw)

        # Fallback if empty
        if not grounded_quick_wins and registry.deficiencies:
            for def_id, def_info in list(registry.deficiencies.items())[:2]:
                grounded_quick_wins.append(f"Resolve {def_info['title']}: {def_info.get('suggested_action', 'Update configuration.')}")

        # Update validated model
        ai_result.top_priorities = grounded_priorities
        ai_result.strengths = grounded_strengths
        ai_result.quick_wins = grounded_quick_wins

        return ai_result

    except Exception as exc:
        logger.warning(f"Error during deterministic grounding post-validation: {exc}")
        # Fail-safe: return original model rather than crashing
        return ai_result


def build_compact_factual_payload(
    technical_seo: Optional[TechnicalSEOResultModel] = None,
    content_analysis: Optional[ContentAnalysisResultModel] = None,
    pagespeed: Optional[PageSpeedResultModel] = None,
    fetch_data: Optional[RawFetchData] = None,
    context_intelligence: Optional[ContextIntelligenceResultModel] = None,
    competitors: Optional[CompetitorAnalysisModel] = None,
) -> Dict[str, Any]:
    """
    Constructs a compact factual dictionary strictly from deterministic findings.
    Excludes raw HTML, full source code, sensitive environment variables, and API keys.
    """
    target_url = fetch_data.final_url if fetch_data else "Unknown URL"
    title = fetch_data.parsed_data.title if fetch_data and fetch_data.parsed_data else None

    # Derive or use context intelligence
    if not context_intelligence:
        from app.services.context_analysis import evaluate_context_intelligence
        context_intelligence = evaluate_context_intelligence(fetch_data=fetch_data, content_analysis=content_analysis)

    biz_ctx = context_intelligence.business_context
    aud_ctx = context_intelligence.audience_context
    has_local_presence = (
        biz_ctx.category in ("local_business", "healthcare", "restaurant", "hospitality", "professional_services")
        or bool(content_analysis and content_analysis.contact_info.address)
    )

    # Technical SEO summary
    tech_findings: List[Dict[str, Any]] = []
    health_score: Optional[int] = None
    passed_count = 0
    needs_attention_count = 0
    issues_count = 0

    if technical_seo:
        health_score = technical_seo.summary.health_score
        passed_count = technical_seo.summary.passed_count
        needs_attention_count = technical_seo.summary.needs_attention_count
        issues_count = technical_seo.summary.issues_count

        for f in technical_seo.findings:
            tech_findings.append({
                "id": f.id,
                "title": f.title,
                "status": f.status,
                "summary": f.summary,
                "suggested_action": f.suggested_action,
            })

    # Content & Service stats
    content_stats: Dict[str, Any] = {}
    service_ctx: Dict[str, Any] = {}
    if content_analysis:
        content_stats = {
            "homepage_word_count": content_analysis.homepage_word_count,
            "average_word_count": content_analysis.average_word_count,
            "total_pages_analyzed": content_analysis.total_pages_analyzed,
            "phones_detected": len(content_analysis.ctas.phones),
            "emails_detected": len(content_analysis.ctas.emails),
            "whatsapp_detected": len(content_analysis.ctas.whatsapp) > 0,
            "booking_providers": content_analysis.ctas.booking_providers,
            "has_address": bool(content_analysis.contact_info.address),
            "has_opening_hours": bool(content_analysis.contact_info.opening_hours),
            "content_summary": content_analysis.summary,
            "is_inconclusive": content_analysis.is_inconclusive,
        }
        service_ctx = {
            "detected_services": content_analysis.services_structure.detected_services[:8],
            "architecture": content_analysis.services_structure.service_architecture,
            "confidence": content_analysis.services_structure.service_detection_confidence,
            "has_dedicated_pages": content_analysis.services_structure.has_dedicated_service_pages,
            "service_pages_count": content_analysis.services_structure.service_pages_count,
        }

    # PageSpeed stats
    pagespeed_stats: Dict[str, Any] = {
        "status": pagespeed.status if pagespeed else "unavailable",
        "performance_score": pagespeed.performance_score if pagespeed else None,
        "fcp": pagespeed.metrics.fcp if pagespeed and pagespeed.metrics else None,
        "lcp": pagespeed.metrics.lcp if pagespeed and pagespeed.metrics else None,
        "cls": pagespeed.metrics.cls if pagespeed and pagespeed.metrics else None,
        "tbt": pagespeed.metrics.tbt if pagespeed and pagespeed.metrics else None,
        "inp": pagespeed.metrics.inp if pagespeed and pagespeed.metrics else None,
        "reason": pagespeed.reason if pagespeed else None,
    }

    # Competitors stats (from Google Places)
    competitors_stats: Dict[str, Any] = {
        "status": competitors.status if competitors else "unavailable",
    }
    if competitors and competitors.status == "available" and competitors.competitors:
        competitors_stats["count"] = len(competitors.competitors)
        competitors_stats["search_location"] = competitors.search_location
        competitors_stats["search_category"] = competitors.search_category
        competitors_stats["top_competitors"] = [
            {
                "name": c.name,
                "rating": c.rating,
                "review_count": c.review_count,
                "has_website": bool(c.website_url),
                "address": c.address,
            }
            for c in competitors.competitors[:5]
        ]
    elif competitors:
        competitors_stats["reason"] = competitors.reason

    # Diagnostics
    diagnostics = {
        "http_status": fetch_data.status_code if fetch_data else None,
        "content_accessible": getattr(fetch_data, "content_accessible", True) if fetch_data else True,
        "bot_protection_detected": (
            fetch_data.error_type == "bot_protection_detected"
            or (fetch_data.status_code in (403, 429))
            or not getattr(fetch_data, "content_accessible", True)
        ) if fetch_data else False,
        "fetch_error": fetch_data.error_message if fetch_data and not fetch_data.success else None,
    }

    category_val = biz_ctx.category if biz_ctx.category != "unknown" else (technical_seo.inferred_category if technical_seo else "unknown")

    return {
        "target_url": target_url,
        "page_title": title,
        "inferred_category": category_val,
        "business_context": {
            "category": category_val,
            "confidence": biz_ctx.confidence,
            "evidence": biz_ctx.evidence,
            "reliability": biz_ctx.reliability,
        },
        "audience_context": {
            "target_audience": aud_ctx.target_audience,
            "confidence": aud_ctx.confidence,
            "reliability": aud_ctx.reliability,
        },
        "service_context": service_ctx,
        "has_local_presence": has_local_presence,
        "technical_seo": {
            "health_score": health_score,
            "passed_count": passed_count,
            "needs_attention_count": needs_attention_count,
            "issues_count": issues_count,
            "findings": tech_findings,
        },
        "content_analysis": content_stats,
        "pagespeed": pagespeed_stats,
        "competitors": competitors_stats,
        "diagnostics": diagnostics,
    }


def _ai_unavailable(category: str, request_id: str = "") -> AIAnalysisResultModel:
    """Construct an unavailable AI result with structured failure info."""
    user_msg = get_user_message("openai", category)
    logger.warning(f"[OpenAI] request_id={request_id} failure_category={category} reason={user_msg}")
    return AIAnalysisResultModel(
        status="unavailable",
        reason=user_msg,
    )


def _classify_ai_timeout(exc: httpx.TimeoutException) -> str:
    """Classify the specific type of timeout from the httpx exception."""
    exc_name = type(exc).__name__
    if "Connect" in exc_name:
        return FailureCategory.CONNECT_TIMEOUT
    elif "Read" in exc_name:
        return FailureCategory.READ_TIMEOUT
    elif "Pool" in exc_name:
        return FailureCategory.POOL_TIMEOUT
    return FailureCategory.READ_TIMEOUT


async def generate_ai_insights(
    technical_seo: Optional[TechnicalSEOResultModel] = None,
    content_analysis: Optional[ContentAnalysisResultModel] = None,
    pagespeed: Optional[PageSpeedResultModel] = None,
    fetch_data: Optional[RawFetchData] = None,
    context_intelligence: Optional[ContextIntelligenceResultModel] = None,
    competitors: Optional[CompetitorAnalysisModel] = None,
    client: Optional[httpx.AsyncClient] = None,
    api_key: Optional[str] = None,
    model: Optional[str] = None,
    request_id: str = "",
) -> AIAnalysisResultModel:
    """
    Generates AI-powered business and SEO insights using OpenAI API.
    Interprets deterministic findings and returns validated Pydantic models.
    Applies deterministic post-validation grounding layer to guarantee zero hallucination.

    Architecture:
    - Creates its own httpx.AsyncClient with appropriate timeouts (not shared with crawl/PageSpeed).
    - Applies controlled retries for transient failures with exponential backoff + jitter.
    - Enforces a 45-second overall deadline across all attempts.
    - Classifies failures into structured categories for logging.
    - Returns safe user-facing messages.
    """
    # 1. Resolve API key
    effective_key = api_key if api_key is not None else settings.openai_key
    if not effective_key or not effective_key.strip():
        return _ai_unavailable(FailureCategory.CONFIGURATION_ERROR, request_id)

    # 2. Build allowed-evidence registry
    registry = GroundingEvidenceRegistry(
        technical_seo=technical_seo,
        content_analysis=content_analysis,
        pagespeed=pagespeed,
        fetch_data=fetch_data,
        competitors=competitors,
    )

    # 3. Build compact factual payload
    payload_data = build_compact_factual_payload(
        technical_seo=technical_seo,
        content_analysis=content_analysis,
        pagespeed=pagespeed,
        fetch_data=fetch_data,
        context_intelligence=context_intelligence,
        competitors=competitors,
    )

    effective_model = model or settings.openai_model

    request_body = {
        "model": effective_model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": f"Here is the factual audit data for the website:\n```json\n{json.dumps(payload_data, separators=(',', ':'))}\n```\nGenerate the structured AI insights JSON."
            }
        ],
        "response_format": {"type": "json_object"},
        "temperature": 0.2,
        "max_tokens": 1200,
    }

    headers = {
        "Authorization": f"Bearer {effective_key.strip()}",
        "Content-Type": "application/json",
    }

    timeout_sec = settings.OPENAI_TIMEOUT_SECONDS
    max_retries = max(1, settings.OPENAI_MAX_RETRIES)
    deadline = settings.OPENAI_DEADLINE_SECONDS
    timeout_obj = httpx.Timeout(connect=10.0, read=timeout_sec, write=5.0, pool=10.0)

    # Always create own client — never share with crawl/PageSpeed to prevent pool starvation
    own_client = False
    if client is None:
        client = httpx.AsyncClient(timeout=timeout_obj)
        own_client = True

    deadline_start = time.monotonic()

    try:
        for attempt in range(1, max_retries + 1):
            # Check overall deadline before each attempt
            elapsed_total = time.monotonic() - deadline_start
            if elapsed_total >= deadline:
                logger.warning(
                    f"[OpenAI] request_id={request_id} deadline_exceeded "
                    f"total_elapsed={elapsed_total:.1f}s deadline={deadline}s"
                )
                return _ai_unavailable(FailureCategory.DEADLINE_EXCEEDED, request_id)

            attempt_start = time.monotonic()
            try:
                response = await client.post(
                    OPENAI_CHAT_ENDPOINT,
                    headers=headers,
                    json=request_body,
                )
                attempt_elapsed = time.monotonic() - attempt_start

                if response.status_code == 200:
                    usage = response.json().get("usage", {})
                    logger.info(
                        f"[OpenAI] request_id={request_id} attempt={attempt} "
                        f"elapsed={attempt_elapsed:.1f}s result=success "
                        f"prompt_tokens={usage.get('prompt_tokens')} "
                        f"completion_tokens={usage.get('completion_tokens')}"
                    )

                    resp_json = response.json()
                    choices = resp_json.get("choices", [])
                    if not choices:
                        return _ai_unavailable(FailureCategory.MALFORMED_RESPONSE, request_id)

                    raw_content = choices[0].get("message", {}).get("content", "")
                    if not raw_content:
                        return _ai_unavailable(FailureCategory.MALFORMED_RESPONSE, request_id)

                    try:
                        parsed_data = json.loads(raw_content)
                        if "status" not in parsed_data:
                            parsed_data["status"] = "available"

                        # Validate with Pydantic
                        validated_model = AIAnalysisResultModel(**parsed_data)

                        # Execute deterministic post-validation grounding layer
                        grounded_model = post_validate_ai_insights(validated_model, registry)
                        return grounded_model

                    except json.JSONDecodeError as json_err:
                        logger.warning(f"[OpenAI] request_id={request_id} malformed_json: {json_err}")
                        return _ai_unavailable(FailureCategory.MALFORMED_RESPONSE, request_id)
                    except Exception as val_err:
                        logger.warning(f"[OpenAI] request_id={request_id} validation_error: {val_err}")
                        return _ai_unavailable(FailureCategory.VALIDATION_ERROR, request_id)

                # Non-transient errors: fail fast, DO NOT retry
                elif response.status_code in (401, 403):
                    logger.warning(
                        f"[OpenAI] request_id={request_id} attempt={attempt} "
                        f"elapsed={attempt_elapsed:.1f}s result=auth_error status={response.status_code}"
                    )
                    return _ai_unavailable(FailureCategory.AUTHENTICATION_ERROR, request_id)

                elif response.status_code == 400:
                    logger.warning(
                        f"[OpenAI] request_id={request_id} attempt={attempt} "
                        f"elapsed={attempt_elapsed:.1f}s result=bad_request"
                    )
                    return _ai_unavailable(FailureCategory.INVALID_REQUEST, request_id)

                # Transient errors (HTTP 429, 500, 502, 503, 504)
                elif response.status_code in (429, 500, 502, 503, 504):
                    is_rate_limit = response.status_code == 429
                    category = FailureCategory.RATE_LIMITED if is_rate_limit else FailureCategory.SERVER_ERROR

                    logger.info(
                        f"[OpenAI] request_id={request_id} attempt={attempt} "
                        f"elapsed={attempt_elapsed:.1f}s result={'rate_limited' if is_rate_limit else 'server_error'} "
                        f"status={response.status_code}"
                    )

                    if attempt < max_retries:
                        delay = (1.0 * (2 ** (attempt - 1))) + random.uniform(0, 0.5)
                        await asyncio.sleep(delay)
                        continue
                    return _ai_unavailable(category, request_id)

                else:
                    logger.warning(
                        f"[OpenAI] request_id={request_id} attempt={attempt} "
                        f"elapsed={attempt_elapsed:.1f}s result=unexpected_status status={response.status_code}"
                    )
                    return _ai_unavailable(FailureCategory.UNKNOWN_ERROR, request_id)

            except httpx.TimeoutException as timeout_exc:
                attempt_elapsed = time.monotonic() - attempt_start
                category = _classify_ai_timeout(timeout_exc)
                logger.info(
                    f"[OpenAI] request_id={request_id} attempt={attempt} "
                    f"elapsed={attempt_elapsed:.1f}s result=timeout category={category}"
                )
                if attempt < max_retries:
                    delay = (1.0 * (2 ** (attempt - 1))) + random.uniform(0, 0.5)
                    await asyncio.sleep(delay)
                    continue
                return _ai_unavailable(category, request_id)

            except httpx.NetworkError as net_exc:
                attempt_elapsed = time.monotonic() - attempt_start
                logger.info(
                    f"[OpenAI] request_id={request_id} attempt={attempt} "
                    f"elapsed={attempt_elapsed:.1f}s result=network_error error={type(net_exc).__name__}"
                )
                if attempt < max_retries:
                    delay = (1.0 * (2 ** (attempt - 1))) + random.uniform(0, 0.5)
                    await asyncio.sleep(delay)
                    continue
                return _ai_unavailable(FailureCategory.NETWORK_ERROR, request_id)

        return _ai_unavailable(FailureCategory.UNKNOWN_ERROR, request_id)

    except Exception as exc:
        logger.warning(f"[OpenAI] request_id={request_id} unexpected_error={exc}")
        return _ai_unavailable(FailureCategory.UNKNOWN_ERROR, request_id)
    finally:
        if own_client:
            await client.aclose()


