import json
import logging
import re
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

logger = logging.getLogger(__name__)

OPENAI_CHAT_ENDPOINT = "https://api.openai.com/v1/chat/completions"
OPENAI_TIMEOUT = httpx.Timeout(connect=5.0, read=25.0, write=5.0, pool=10.0)

SYSTEM_PROMPT = """You are an expert Technical SEO and Growth Strategist for the Website SEO & Visibility Analyser.

Your objective is to interpret the supplied deterministic website audit data and generate an executive-level, business-friendly analysis.

CRITICAL ANTI-HALLUCINATION & INTEGRITY RULES:
1. Grounding: Reason ONLY from the supplied factual analysis data. Do NOT fabricate, assume, or invent findings, metrics, URLs, services, or contact details not present in the payload.
2. Fact vs Interpretation: Clearly distinguish observed FACTS (what was detected), INTERPRETATION (why it matters to the business), and RECOMMENDATIONS (specific actions to take).
3. No False Penalties: Do NOT claim Google penalties or search index bans without direct evidence.
4. No Guarantees: Do NOT promise guaranteed #1 rankings or specific numeric revenue gains.
5. Limitations: Explicitly acknowledge missing or unavailable data (e.g., if PageSpeed is unavailable or bot protection limited subpage crawling).
6. Anchor IDs: When recommending an action for a specific technical or content issue, include the exact "anchor_finding_id" (e.g. "image_alt_tags", "meta_description", "schema_org", "dedicated_service_pages_missing", "pagespeed_performance").

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
  ],
  "strengths": [
    "<Observed positive finding supported by data 1>",
    "<Observed positive finding supported by data 2>"
  ],
  "limitations": [
    "<Notice regarding unanalyzed subpages or unavailable third-party metrics if applicable>"
  ]
}
"""

# Topic keyword registry mapping check IDs to related phrases
TOPIC_KEYWORDS: Dict[str, List[str]] = {
    "ssl_https": ["ssl", "https", "tls", "security certificate", "encryption"],
    "mobile_viewport": ["viewport", "mobile friendly", "responsive viewport", "mobile responsive"],
    "meta_description": ["meta description", "description tag", "meta tag"],
    "title_tag": ["title tag", "<title>", "page title", "homepage title"],
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
    "bot_protection_detected": ["bot protection", "waf", "firewall", "akamai", "cloudflare", "challenge", "403 forbidden"],
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
    ):
        self.deficiencies: Dict[str, Dict[str, Any]] = {}
        self.passed_checks: Dict[str, Dict[str, Any]] = {}
        self.confirmed_strengths: List[str] = []

        # 1. Technical SEO checks
        if technical_seo:
            for f in technical_seo.findings:
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

        # 2. Content Analysis deficiencies / strengths
        if content_analysis:
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
        if fetch_data and fetch_data.error_type == "bot_protection_detected":
            self.deficiencies["bot_protection_detected"] = {
                "id": "bot_protection_detected",
                "title": "Bot Protection / WAF Challenge",
                "status": "needs_attention",
                "summary": "Edge security firewall returned challenge status.",
                "suggested_action": "Ensure search engine crawlers are allowed in firewall whitelist.",
                "category": "technical_seo",
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
) -> Dict[str, Any]:
    """
    Constructs a compact factual dictionary strictly from deterministic findings.
    Excludes raw HTML, full source code, sensitive environment variables, and API keys.
    """
    target_url = fetch_data.final_url if fetch_data else "Unknown URL"
    title = fetch_data.parsed_data.title if fetch_data and fetch_data.parsed_data else None

    # Technical SEO summary
    tech_findings: List[Dict[str, Any]] = []
    health_score: Optional[int] = None
    passed_count = 0
    needs_attention_count = 0
    issues_count = 0
    inferred_category = "general"

    if technical_seo:
        health_score = technical_seo.summary.health_score
        passed_count = technical_seo.summary.passed_count
        needs_attention_count = technical_seo.summary.needs_attention_count
        issues_count = technical_seo.summary.issues_count
        inferred_category = technical_seo.inferred_category

        for f in technical_seo.findings:
            tech_findings.append({
                "id": f.id,
                "title": f.title,
                "status": f.status,
                "summary": f.summary,
                "suggested_action": f.suggested_action,
            })

    # Content stats
    content_stats: Dict[str, Any] = {}
    if content_analysis:
        content_stats = {
            "homepage_word_count": content_analysis.homepage_word_count,
            "average_word_count": content_analysis.average_word_count,
            "total_pages_analyzed": content_analysis.total_pages_analyzed,
            "dedicated_service_pages": content_analysis.services_structure.has_dedicated_service_pages,
            "service_pages_count": content_analysis.services_structure.service_pages_count,
            "detected_services": content_analysis.services_structure.detected_services[:8],
            "phones_detected": len(content_analysis.ctas.phones),
            "emails_detected": len(content_analysis.ctas.emails),
            "whatsapp_detected": len(content_analysis.ctas.whatsapp) > 0,
            "booking_providers": content_analysis.ctas.booking_providers,
            "has_address": bool(content_analysis.contact_info.address),
            "has_opening_hours": bool(content_analysis.contact_info.opening_hours),
            "content_summary": content_analysis.summary,
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

    # Diagnostics
    diagnostics = {
        "http_status": fetch_data.status_code if fetch_data else None,
        "bot_protection_detected": fetch_data.error_type == "bot_protection_detected" if fetch_data else False,
        "fetch_error": fetch_data.error_message if fetch_data and not fetch_data.success else None,
    }

    return {
        "target_url": target_url,
        "page_title": title,
        "inferred_category": inferred_category,
        "technical_seo": {
            "health_score": health_score,
            "passed_count": passed_count,
            "needs_attention_count": needs_attention_count,
            "issues_count": issues_count,
            "findings": tech_findings,
        },
        "content_analysis": content_stats,
        "pagespeed": pagespeed_stats,
        "diagnostics": diagnostics,
    }


async def generate_ai_insights(
    technical_seo: Optional[TechnicalSEOResultModel] = None,
    content_analysis: Optional[ContentAnalysisResultModel] = None,
    pagespeed: Optional[PageSpeedResultModel] = None,
    fetch_data: Optional[RawFetchData] = None,
    client: Optional[httpx.AsyncClient] = None,
    api_key: Optional[str] = None,
    model: Optional[str] = None,
) -> AIAnalysisResultModel:
    """
    Generates AI-powered business and SEO insights using OpenAI API.
    Interprets deterministic findings and returns validated Pydantic models.
    Applies deterministic post-validation grounding layer to guarantee zero hallucination.
    """
    # 1. Resolve API key
    effective_key = api_key if api_key is not None else settings.openai_key
    if not effective_key or not effective_key.strip():
        return AIAnalysisResultModel(
            status="unavailable",
            reason="OpenAI API key is not configured.",
        )

    # 2. Build allowed-evidence registry
    registry = GroundingEvidenceRegistry(
        technical_seo=technical_seo,
        content_analysis=content_analysis,
        pagespeed=pagespeed,
        fetch_data=fetch_data,
    )

    # 3. Build compact factual payload
    payload_data = build_compact_factual_payload(
        technical_seo=technical_seo,
        content_analysis=content_analysis,
        pagespeed=pagespeed,
        fetch_data=fetch_data,
    )

    effective_model = model or settings.openai_model

    request_body = {
        "model": effective_model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": f"Here is the factual audit data for the website:\n```json\n{json.dumps(payload_data, indent=2)}\n```\nGenerate the structured AI insights JSON."
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

    own_client = False
    if client is None:
        client = httpx.AsyncClient(timeout=OPENAI_TIMEOUT)
        own_client = True

    try:
        response = await client.post(
            OPENAI_CHAT_ENDPOINT,
            headers=headers,
            json=request_body,
        )

        if response.status_code == 200:
            resp_json = response.json()
            choices = resp_json.get("choices", [])
            if not choices:
                return AIAnalysisResultModel(
                    status="unavailable",
                    reason="OpenAI returned an empty choice response.",
                )

            raw_content = choices[0].get("message", {}).get("content", "")
            if not raw_content:
                return AIAnalysisResultModel(
                    status="unavailable",
                    reason="OpenAI returned empty message content.",
                )

            try:
                parsed_data = json.loads(raw_content)
                # Ensure status is set
                if "status" not in parsed_data:
                    parsed_data["status"] = "available"

                # Validate with Pydantic
                validated_model = AIAnalysisResultModel(**parsed_data)

                # Execute deterministic post-validation grounding layer
                grounded_model = post_validate_ai_insights(validated_model, registry)
                return grounded_model

            except json.JSONDecodeError as json_err:
                logger.warning(f"Malformed JSON from OpenAI: {json_err}")
                return AIAnalysisResultModel(
                    status="unavailable",
                    reason="AI insights response was not valid JSON.",
                )
            except Exception as val_err:
                logger.warning(f"Pydantic validation error for AI response: {val_err}")
                return AIAnalysisResultModel(
                    status="unavailable",
                    reason=f"Failed to validate AI response structure: {str(val_err)}",
                )

        elif response.status_code in (401, 403):
            err_msg = "OpenAI API key is invalid or lacks required permissions."
            try:
                err_body = response.json().get("error", {})
                if err_body.get("message"):
                    err_msg = err_body["message"]
            except Exception:
                pass
            return AIAnalysisResultModel(
                status="unavailable",
                reason=err_msg,
            )

        elif response.status_code == 429:
            return AIAnalysisResultModel(
                status="unavailable",
                reason="OpenAI API rate limit or quota exceeded.",
            )

        else:
            return AIAnalysisResultModel(
                status="unavailable",
                reason=f"OpenAI API returned unexpected status code HTTP {response.status_code}.",
            )

    except httpx.TimeoutException:
        return AIAnalysisResultModel(
            status="unavailable",
            reason="OpenAI API request timed out.",
        )
    except httpx.ConnectError:
        return AIAnalysisResultModel(
            status="unavailable",
            reason="Could not connect to OpenAI API server.",
        )
    except Exception as exc:
        logger.warning(f"Unexpected error in AI insights generation: {exc}")
        return AIAnalysisResultModel(
            status="unavailable",
            reason=f"An unexpected error occurred during AI analysis: {str(exc)}",
        )
    finally:
        if own_client:
            await client.aclose()
