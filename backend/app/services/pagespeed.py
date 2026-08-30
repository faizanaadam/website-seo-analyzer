import logging
import asyncio
import random
import time
from typing import Optional
import httpx

from app.config import settings
from app.models import PageSpeedResultModel, PageSpeedMetricsModel
from app.services.failure_types import FailureCategory, get_user_message

logger = logging.getLogger(__name__)

PAGESPEED_API_ENDPOINT = "https://pagespeedonline.googleapis.com/pagespeedonline/v5/runPagespeed"


# In-memory LRU-like TTL cache for PageSpeed results: {cache_key: (PageSpeedResultModel, timestamp)}
_pagespeed_cache: dict[str, tuple[PageSpeedResultModel, float]] = {}
_CACHE_MAX_SIZE = 100


def _normalize_cache_key(url: str, strategy: str = "mobile") -> str:
    """Normalizes URL for consistent cache lookups."""
    clean_url = url.strip().rstrip("/").lower()
    return f"{clean_url}::{strategy}"


def _get_from_cache(url: str, strategy: str = "mobile") -> Optional[PageSpeedResultModel]:
    """Retrieves a cached PageSpeed result if still valid within TTL."""
    key = _normalize_cache_key(url, strategy)
    if key in _pagespeed_cache:
        model, cached_at = _pagespeed_cache[key]
        ttl = getattr(settings, "PAGESPEED_CACHE_TTL_SECONDS", 600)
        if time.monotonic() - cached_at < ttl:
            return model
        else:
            # Expired
            del _pagespeed_cache[key]
    return None


def _save_to_cache(url: str, model: PageSpeedResultModel, strategy: str = "mobile") -> None:
    """Caches a successful PageSpeed result with timestamp."""
    if model.status != "available":
        return  # Never cache failures or unavailable results

    # Bound cache size
    if len(_pagespeed_cache) >= _CACHE_MAX_SIZE:
        oldest_key = min(_pagespeed_cache.keys(), key=lambda k: _pagespeed_cache[k][1])
        del _pagespeed_cache[oldest_key]

    key = _normalize_cache_key(url, strategy)
    _pagespeed_cache[key] = (model, time.monotonic())


def clear_pagespeed_cache() -> None:
    """Clears the in-memory PageSpeed cache (useful for testing)."""
    _pagespeed_cache.clear()


def _classify_timeout(exc: httpx.TimeoutException) -> str:
    """Classify the specific type of timeout from the httpx exception."""
    exc_name = type(exc).__name__
    if "Connect" in exc_name:
        return FailureCategory.CONNECT_TIMEOUT
    elif "Read" in exc_name:
        return FailureCategory.READ_TIMEOUT
    elif "Pool" in exc_name:
        return FailureCategory.POOL_TIMEOUT
    return FailureCategory.READ_TIMEOUT


def _unavailable(category: str, request_id: str = "") -> PageSpeedResultModel:
    """Construct an unavailable PageSpeed result with structured failure info."""
    user_msg = get_user_message("pagespeed", category)
    logger.warning(f"[PageSpeed] request_id={request_id} failure_category={category} reason={user_msg}")
    return PageSpeedResultModel(
        status="unavailable",
        performance_score=None,
        metrics=None,
        reason=user_msg,
    )


async def get_pagespeed_insights(
    url: str,
    client: Optional[httpx.AsyncClient] = None,
    api_key: Optional[str] = None,
    request_id: str = "",
) -> PageSpeedResultModel:
    """
    Fetches Google PageSpeed Insights (mobile strategy) for a target URL.
    Extracts performance score and Core Web Vitals (FCP, LCP, CLS, INP, TBT).

    Architecture:
    - In-memory TTL cache (default 10 minutes) avoids duplicate slow audits on repeated requests.
    - Creates its own httpx.AsyncClient with appropriate timeouts (not shared with crawl/AI).
    - Applies controlled retries for transient failures with exponential backoff + jitter.
    - Enforces a 60-second overall deadline across all attempts.
    - Classifies failures into structured categories for logging.
    - Returns safe user-facing messages.
    """
    # 0. Check in-memory cache
    cached_result = _get_from_cache(url, strategy="mobile")
    if cached_result is not None:
        logger.info(f"[PageSpeed] request_id={request_id} cache_hit=True url={url}")
        return cached_result

    # 1. Resolve API Key
    effective_key = api_key if api_key is not None else settings.pagespeed_key
    if not effective_key or not effective_key.strip():
        return _unavailable(FailureCategory.CONFIGURATION_ERROR, request_id)

    # 2. Build Request Parameters
    params = {
        "url": url,
        "strategy": "mobile",
        "category": "performance",
        "key": effective_key.strip(),
    }

    timeout_sec = settings.PAGESPEED_TIMEOUT_SECONDS
    max_retries = max(1, settings.PAGESPEED_MAX_RETRIES)
    deadline = settings.PAGESPEED_DEADLINE_SECONDS
    timeout_obj = httpx.Timeout(connect=10.0, read=timeout_sec, write=5.0, pool=10.0)

    # 3. Use provided client or create a dedicated one (never share with crawl/AI)
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
                    f"[PageSpeed] request_id={request_id} deadline_exceeded "
                    f"total_elapsed={elapsed_total:.1f}s deadline={deadline}s"
                )
                return _unavailable(FailureCategory.DEADLINE_EXCEEDED, request_id)

            attempt_start = time.monotonic()
            try:
                response = await client.get(PAGESPEED_API_ENDPOINT, params=params)
                attempt_elapsed = time.monotonic() - attempt_start

                if response.status_code == 200:
                    logger.info(
                        f"[PageSpeed] request_id={request_id} attempt={attempt} "
                        f"elapsed={attempt_elapsed:.1f}s result=success"
                    )

                    data = response.json()
                    lighthouse = data.get("lighthouseResult", {})
                    categories = lighthouse.get("categories", {})
                    perf_cat = categories.get("performance", {})

                    perf_score_raw = perf_cat.get("score")
                    performance_score = int(round(perf_score_raw * 100)) if perf_score_raw is not None else None

                    audits = lighthouse.get("audits", {})
                    fcp = audits.get("first-contentful-paint", {}).get("displayValue")
                    lcp = audits.get("largest-contentful-paint", {}).get("displayValue")
                    tbt = audits.get("total-blocking-time", {}).get("displayValue")

                    cls_audit = audits.get("cumulative-layout-shift", {})
                    cls_val: Optional[float] = None
                    if "numericValue" in cls_audit and isinstance(cls_audit["numericValue"], (int, float)):
                        cls_val = round(float(cls_audit["numericValue"]), 3)
                    elif "displayValue" in cls_audit:
                        try:
                            cls_val = round(float(cls_audit["displayValue"]), 3)
                        except (ValueError, TypeError):
                            pass

                    inp_audit = (
                        audits.get("interaction-to-next-paint")
                        or audits.get("experimental-interaction-to-next-paint")
                        or audits.get("interactive")
                    )
                    inp = inp_audit.get("displayValue") if inp_audit else None

                    metrics = PageSpeedMetricsModel(
                        fcp=fcp, lcp=lcp, cls=cls_val, inp=inp, tbt=tbt,
                    )

                    result_model = PageSpeedResultModel(
                        status="available",
                        performance_score=performance_score,
                        metrics=metrics,
                        reason=None,
                    )
                    _save_to_cache(url, result_model, strategy="mobile")
                    return result_model

                # --- Non-transient errors: fail fast, DO NOT retry ---
                elif response.status_code == 400:
                    logger.warning(
                        f"[PageSpeed] request_id={request_id} attempt={attempt} "
                        f"elapsed={attempt_elapsed:.1f}s result=bad_request"
                    )
                    return _unavailable(FailureCategory.INVALID_REQUEST, request_id)

                elif response.status_code in (401, 403):
                    logger.warning(
                        f"[PageSpeed] request_id={request_id} attempt={attempt} "
                        f"elapsed={attempt_elapsed:.1f}s result=auth_error status={response.status_code}"
                    )
                    return _unavailable(FailureCategory.AUTHENTICATION_ERROR, request_id)

                # --- Transient errors: retry with backoff + jitter ---
                elif response.status_code == 429:
                    logger.info(
                        f"[PageSpeed] request_id={request_id} attempt={attempt} "
                        f"elapsed={attempt_elapsed:.1f}s result=rate_limited"
                    )
                    if attempt < max_retries:
                        delay = (1.0 * (2 ** (attempt - 1))) + random.uniform(0, 0.5)
                        await asyncio.sleep(delay)
                        continue
                    return _unavailable(FailureCategory.RATE_LIMITED, request_id)

                elif response.status_code in (500, 502, 503, 504):
                    # Examine the response body for Lighthouse-specific errors
                    error_body = ""
                    try:
                        error_data = response.json()
                        error_body = error_data.get("error", {}).get("message", "")
                    except Exception:
                        pass

                    is_lighthouse_error = "lighthouse" in error_body.lower()
                    category = FailureCategory.UPSTREAM_UNAVAILABLE if is_lighthouse_error else FailureCategory.SERVER_ERROR

                    logger.info(
                        f"[PageSpeed] request_id={request_id} attempt={attempt} "
                        f"elapsed={attempt_elapsed:.1f}s result=server_error "
                        f"status={response.status_code} lighthouse_error={is_lighthouse_error} "
                        f"error_hint={error_body[:120]}"
                    )

                    if attempt < max_retries:
                        delay = (1.0 * (2 ** (attempt - 1))) + random.uniform(0, 0.5)
                        await asyncio.sleep(delay)
                        continue
                    return _unavailable(category, request_id)

                else:
                    logger.warning(
                        f"[PageSpeed] request_id={request_id} attempt={attempt} "
                        f"elapsed={attempt_elapsed:.1f}s result=unexpected_status status={response.status_code}"
                    )
                    return _unavailable(FailureCategory.UNKNOWN_ERROR, request_id)

            except httpx.TimeoutException as timeout_exc:
                attempt_elapsed = time.monotonic() - attempt_start
                category = _classify_timeout(timeout_exc)
                logger.info(
                    f"[PageSpeed] request_id={request_id} attempt={attempt} "
                    f"elapsed={attempt_elapsed:.1f}s result=timeout category={category}"
                )
                if attempt < max_retries:
                    delay = (1.0 * (2 ** (attempt - 1))) + random.uniform(0, 0.5)
                    await asyncio.sleep(delay)
                    continue
                return _unavailable(category, request_id)

            except httpx.NetworkError as net_exc:
                attempt_elapsed = time.monotonic() - attempt_start
                logger.info(
                    f"[PageSpeed] request_id={request_id} attempt={attempt} "
                    f"elapsed={attempt_elapsed:.1f}s result=network_error error={type(net_exc).__name__}"
                )
                if attempt < max_retries:
                    delay = (1.0 * (2 ** (attempt - 1))) + random.uniform(0, 0.5)
                    await asyncio.sleep(delay)
                    continue
                return _unavailable(FailureCategory.NETWORK_ERROR, request_id)

        return _unavailable(FailureCategory.UNKNOWN_ERROR, request_id)

    except Exception as exc:
        logger.warning(f"[PageSpeed] request_id={request_id} unexpected_error={exc}")
        return _unavailable(FailureCategory.UNKNOWN_ERROR, request_id)
    finally:
        if own_client:
            await client.aclose()
