import logging
from typing import Optional, Dict, Any
import httpx

from app.config import settings
from app.models import PageSpeedResultModel, PageSpeedMetricsModel

logger = logging.getLogger(__name__)

PAGESPEED_API_ENDPOINT = "https://pagespeedonline.googleapis.com/pagespeedonline/v5/runPagespeed"
PAGESPEED_TIMEOUT = httpx.Timeout(connect=5.0, read=20.0, write=5.0, pool=10.0)


async def get_pagespeed_insights(
    url: str,
    client: Optional[httpx.AsyncClient] = None,
    api_key: Optional[str] = None,
) -> PageSpeedResultModel:
    """
    Fetches Google PageSpeed Insights (mobile strategy) for a target URL.
    Extracts performance score and Core Web Vitals (FCP, LCP, CLS, INP, TBT).
    Gracefully degrades if the API key is absent, quota is exceeded, or request times out.
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

    own_client = False
    if client is None:
        client = httpx.AsyncClient(timeout=PAGESPEED_TIMEOUT)
        own_client = True

    try:
        response = await client.get(PAGESPEED_API_ENDPOINT, params=params)

        if response.status_code == 200:
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

        elif response.status_code == 400:
            error_msg = "Invalid URL or parameters provided to PageSpeed API."
            try:
                err_data = response.json().get("error", {})
                error_msg = err_data.get("message", error_msg)
            except Exception:
                pass
            return PageSpeedResultModel(
                status="unavailable",
                performance_score=None,
                metrics=None,
                reason=f"Google PageSpeed API bad request: {error_msg}",
            )

        elif response.status_code in (401, 403):
            error_msg = "Google PageSpeed API key is invalid or lacks required permissions."
            try:
                err_data = response.json().get("error", {})
                msg = err_data.get("message", "")
                if "quota" in msg.lower():
                    error_msg = "Google PageSpeed API quota limit reached."
                elif msg:
                    error_msg = msg
            except Exception:
                pass
            return PageSpeedResultModel(
                status="unavailable",
                performance_score=None,
                metrics=None,
                reason=error_msg,
            )

        elif response.status_code == 429:
            return PageSpeedResultModel(
                status="unavailable",
                performance_score=None,
                metrics=None,
                reason="Google PageSpeed API rate limit or quota exceeded.",
            )

        elif response.status_code >= 500:
            return PageSpeedResultModel(
                status="unavailable",
                performance_score=None,
                metrics=None,
                reason=f"Google PageSpeed service encountered a temporary error (HTTP {response.status_code}).",
            )

        else:
            return PageSpeedResultModel(
                status="unavailable",
                performance_score=None,
                metrics=None,
                reason=f"Google PageSpeed API returned unexpected status code HTTP {response.status_code}.",
            )

    except httpx.TimeoutException:
        return PageSpeedResultModel(
            status="unavailable",
            performance_score=None,
            metrics=None,
            reason="Google PageSpeed API request timed out.",
        )
    except httpx.ConnectError:
        return PageSpeedResultModel(
            status="unavailable",
            performance_score=None,
            metrics=None,
            reason="Could not connect to Google PageSpeed API server.",
        )
    except Exception as exc:
        logger.warning(f"Unexpected error in PageSpeed integration: {exc}")
        return PageSpeedResultModel(
            status="unavailable",
            performance_score=None,
            metrics=None,
            reason=f"An unexpected error occurred during PageSpeed analysis: {str(exc)}",
        )
    finally:
        if own_client:
            await client.aclose()
