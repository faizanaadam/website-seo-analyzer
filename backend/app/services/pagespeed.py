import logging
import asyncio
from typing import Optional, Dict, Any
import httpx

from app.config import settings
from app.models import PageSpeedResultModel, PageSpeedMetricsModel

logger = logging.getLogger(__name__)

PAGESPEED_API_ENDPOINT = "https://pagespeedonline.googleapis.com/pagespeedonline/v5/runPagespeed"


async def get_pagespeed_insights(
    url: str,
    client: Optional[httpx.AsyncClient] = None,
    api_key: Optional[str] = None,
) -> PageSpeedResultModel:
    """
    Fetches Google PageSpeed Insights (mobile strategy) for a target URL.
    Extracts performance score and Core Web Vitals (FCP, LCP, CLS, INP, TBT).
    Gracefully degrades if the API key is absent, quota is exceeded, or request times out.
    Applies controlled retries for transient failures with exponential backoff.
    """
    # 1. Resolve API Key
    effective_key = api_key if api_key is not None else settings.pagespeed_key
    if not effective_key or not effective_key.strip():
        return PageSpeedResultModel(
            status="unavailable",
            performance_score=None,
            metrics=None,
            reason="Google PageSpeed API key is not configured.",
        )

    # 2. Build Request Parameters
    params = {
        "url": url,
        "strategy": "mobile",
        "category": "performance",
        "key": effective_key.strip(),
    }

    timeout_sec = settings.PAGESPEED_TIMEOUT_SECONDS
    max_retries = max(1, settings.PAGESPEED_MAX_RETRIES)
    timeout_obj = httpx.Timeout(connect=5.0, read=timeout_sec, write=5.0, pool=10.0)

    own_client = False
    if client is None:
        client = httpx.AsyncClient(timeout=timeout_obj)
        own_client = True

    try:
        for attempt in range(1, max_retries + 1):
            try:
                response = await client.get(PAGESPEED_API_ENDPOINT, params=params)

                if response.status_code == 200:
                    if attempt > 1:
                        logger.info(f"PageSpeed request succeeded on attempt {attempt}")

                    data = response.json()
                    lighthouse = data.get("lighthouseResult", {})
                    categories = lighthouse.get("categories", {})
                    perf_cat = categories.get("performance", {})

                    # Performance score (0-100)
                    perf_score_raw = perf_cat.get("score")
                    performance_score = int(round(perf_score_raw * 100)) if perf_score_raw is not None else None

                    # Audits
                    audits = lighthouse.get("audits", {})

                    fcp = audits.get("first-contentful-paint", {}).get("displayValue")
                    lcp = audits.get("largest-contentful-paint", {}).get("displayValue")
                    tbt = audits.get("total-blocking-time", {}).get("displayValue")

                    # CLS (Cumulative Layout Shift)
                    cls_audit = audits.get("cumulative-layout-shift", {})
                    cls_val: Optional[float] = None
                    if "numericValue" in cls_audit and isinstance(cls_audit["numericValue"], (int, float)):
                        cls_val = round(float(cls_audit["numericValue"]), 3)
                    elif "displayValue" in cls_audit:
                        try:
                            cls_val = round(float(cls_audit["displayValue"]), 3)
                        except (ValueError, TypeError):
                            pass

                    # INP (Interaction to Next Paint)
                    inp_audit = (
                        audits.get("interaction-to-next-paint")
                        or audits.get("experimental-interaction-to-next-paint")
                        or audits.get("interactive")
                    )
                    inp = inp_audit.get("displayValue") if inp_audit else None

                    metrics = PageSpeedMetricsModel(
                        fcp=fcp,
                        lcp=lcp,
                        cls=cls_val,
                        inp=inp,
                        tbt=tbt,
                    )

                    return PageSpeedResultModel(
                        status="available",
                        performance_score=performance_score,
                        metrics=metrics,
                        reason=None,
                    )

                # Non-transient errors: fail fast, DO NOT retry
                elif response.status_code == 400:
                    logger.warning("Google PageSpeed API bad request (HTTP 400). Not retrying.")
                    return PageSpeedResultModel(
                        status="unavailable",
                        performance_score=None,
                        metrics=None,
                        reason="Google PageSpeed API bad request: invalid URL or parameters.",
                    )

                elif response.status_code in (401, 403):
                    logger.warning("Google PageSpeed API authentication/permission error (HTTP 401/403). Not retrying.")
                    return PageSpeedResultModel(
                        status="unavailable",
                        performance_score=None,
                        metrics=None,
                        reason="Google PageSpeed API key is invalid or lacks required permissions.",
                    )

                # Transient errors (HTTP 429, 500, 502, 503, 504)
                elif response.status_code in (429, 500, 502, 503, 504):
                    is_rate_limit = response.status_code == 429
                    fail_type = "rate limit (HTTP 429)" if is_rate_limit else f"server error (HTTP {response.status_code})"

                    if attempt < max_retries:
                        logger.info(f"PageSpeed request attempt {attempt} failed ({fail_type}). Retrying...")
                        await asyncio.sleep(0.5 * attempt)
                        continue
                    else:
                        logger.warning(f"PageSpeed request failed after {max_retries} attempts ({fail_type}).")
                        return PageSpeedResultModel(
                            status="unavailable",
                            performance_score=None,
                            metrics=None,
                            reason="Google PageSpeed API quota or rate limit was reached." if is_rate_limit else "Google PageSpeed API is temporarily unavailable.",
                        )

                else:
                    return PageSpeedResultModel(
                        status="unavailable",
                        performance_score=None,
                        metrics=None,
                        reason=f"Google PageSpeed API returned unexpected status code HTTP {response.status_code}.",
                    )

            except (httpx.TimeoutException, httpx.NetworkError) as transient_exc:
                err_kind = "timed out" if isinstance(transient_exc, httpx.TimeoutException) else "network error"
                if attempt < max_retries:
                    logger.info(f"PageSpeed request attempt {attempt} {err_kind}. Retrying...")
                    await asyncio.sleep(0.5 * attempt)
                    continue
                else:
                    logger.warning(f"PageSpeed request {err_kind} after {max_retries} attempts.")
                    return PageSpeedResultModel(
                        status="unavailable",
                        performance_score=None,
                        metrics=None,
                        reason=f"Google PageSpeed API request {err_kind} after retry.",
                    )

        return PageSpeedResultModel(
            status="unavailable",
            performance_score=None,
            metrics=None,
            reason="Google PageSpeed API is temporarily unavailable.",
        )

    except Exception as exc:
        logger.warning(f"Unexpected error in PageSpeed integration: {exc}")
        return PageSpeedResultModel(
            status="unavailable",
            performance_score=None,
            metrics=None,
            reason="Google PageSpeed API is temporarily unavailable.",
        )
    finally:
        if own_client:
            await client.aclose()
