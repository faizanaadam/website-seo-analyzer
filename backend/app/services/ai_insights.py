import json
import logging
from typing import Optional, Dict, Any, List
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
      "estimated_effort": "quick" | "moderate" | "significant"
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
    Degrades gracefully if OpenAI is unconfigured, times out, or fails.
    """
    # 1. Resolve API key
    effective_key = api_key if api_key is not None else settings.openai_key
    if not effective_key or not effective_key.strip():
        return AIAnalysisResultModel(
            status="unavailable",
            reason="OpenAI API key is not configured.",
        )

    # 2. Build compact factual payload
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
                return validated_model

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
