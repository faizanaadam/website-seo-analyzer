import logging
import asyncio
import random
import time
import re
from typing import Optional, List, Dict, Any, Tuple
from urllib.parse import urlparse
import httpx

from app.config import settings
from app.models import (
    CompetitorModel,
    CompetitorAnalysisModel,
    BusinessContextModel,
    RawFetchData,
    ContentAnalysisResultModel,
)
from app.services.failure_types import FailureCategory, get_user_message

logger = logging.getLogger(__name__)

# Google Places API (New) Endpoints
PLACES_SEARCH_NEW_ENDPOINT = "https://places.googleapis.com/v1/places:searchText"
PLACES_DETAILS_NEW_ENDPOINT = "https://places.googleapis.com/v1/places/{place_id}"

# In-memory LRU-like TTL cache for Places results: {cache_key: (CompetitorAnalysisModel, timestamp)}
_places_cache: Dict[str, Tuple[CompetitorAnalysisModel, float]] = {}
_CACHE_MAX_SIZE = 100

# Category to Google Places search term mapping
CATEGORY_SEARCH_TERMS = {
    "healthcare": "medical clinics",
    "hospitality": "hotels",
    "restaurant": "restaurants",
    "local_business": "auto repair contractors",
    "professional_services": "law firms accounting services",
    "technology": "technology companies",
    "saas": "software companies",
    "ecommerce": "retail stores",
    "education": "schools educational centers",
    "nonprofit": "community organizations",
}


def extract_search_locality(addr: str) -> str:
    """
    Extracts the broader city/locality/region portion from a detailed street address
    so that Google Places text search queries find nearby competitors across the locality
    rather than restricting to a single building/room number.
    """
    clean = " ".join(addr.split())
    parts = [p.strip() for p in clean.split(",") if p.strip()]
    if len(parts) <= 2:
        return clean
    if len(parts) >= 4:
        return ", ".join(parts[-3:])
    elif len(parts) == 3:
        return ", ".join(parts[-2:])
    return clean


def _normalize_cache_key(category: str, location: str) -> str:
    """Normalizes category and location for consistent cache lookups."""
    clean_cat = category.strip().lower()
    clean_loc = location.strip().lower()
    return f"{clean_cat}::{clean_loc}"


def _get_from_cache(category: str, location: str) -> Optional[CompetitorAnalysisModel]:
    """Retrieves a cached competitor analysis if still valid within TTL."""
    key = _normalize_cache_key(category, location)
    if key in _places_cache:
        model, cached_at = _places_cache[key]
        ttl = getattr(settings, "PLACES_CACHE_TTL_SECONDS", 900)
        if time.monotonic() - cached_at < ttl:
            return model
        else:
            del _places_cache[key]
    return None


def _save_to_cache(category: str, location: str, model: CompetitorAnalysisModel) -> None:
    """Caches a successful competitor analysis with timestamp."""
    if model.status not in ("available", "partial"):
        return  # Never cache failures or unavailable results

    if len(_places_cache) >= _CACHE_MAX_SIZE:
        oldest_key = min(_places_cache.keys(), key=lambda k: _places_cache[k][1])
        del _places_cache[oldest_key]

    key = _normalize_cache_key(category, location)
    _places_cache[key] = (model, time.monotonic())


def clear_places_cache() -> None:
    """Clears the in-memory Google Places cache (useful for testing)."""
    _places_cache.clear()


def _classify_timeout(exc: httpx.TimeoutException) -> str:
    """Classify timeout type from httpx exception."""
    exc_name = type(exc).__name__
    if "Connect" in exc_name:
        return FailureCategory.CONNECT_TIMEOUT
    elif "Read" in exc_name:
        return FailureCategory.READ_TIMEOUT
    elif "Pool" in exc_name:
        return FailureCategory.POOL_TIMEOUT
    return FailureCategory.READ_TIMEOUT


def _unavailable(
    category: str,
    reason_override: Optional[str] = None,
    search_cat: Optional[str] = None,
    search_loc: Optional[str] = None,
    request_id: str = "",
) -> CompetitorAnalysisModel:
    """Constructs an unavailable competitor model with safe messaging."""
    user_msg = reason_override or get_user_message("places", category)
    logger.warning(f"[GooglePlaces] request_id={request_id} failure_category={category} reason={user_msg}")
    return CompetitorAnalysisModel(
        status="unavailable",
        search_category=search_cat,
        search_location=search_loc,
        competitors=[],
        strengths=[],
        opportunities=[],
        reason=user_msg,
        limitations=["Local competitor comparison unavailable for this analysis."],
    )


def extract_deterministic_location(
    fetch_data: Optional[RawFetchData],
    content_analysis: Optional[ContentAnalysisResultModel],
) -> Optional[str]:
    """
    Extracts physical business location ONLY from confirmed deterministic signals:
    - Schema.org LocalBusiness / PostalAddress / MedicalClinic
    - Microdata itemprop="address"
    - Explicit physical address detected in verified website HTML / contact info
    Never infers from IP, user location, phone country code alone, or domain name.
    """
    if content_analysis and content_analysis.contact_info and content_analysis.contact_info.address:
        addr = content_analysis.contact_info.address.strip()
        if len(addr) >= 3:
            return addr

    return None


def determine_competitor_eligibility(
    business_context: Optional[BusinessContextModel],
    location: Optional[str],
    is_blocked: bool = False,
) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Determines if local competitor search is appropriate based on deterministic evidence.
    Returns: (is_eligible, search_category, rejection_reason)
    """
    if is_blocked:
        return (
            False,
            None,
            "Automated crawler access was challenged; competitor discovery could not be performed.",
        )

    if not business_context or business_context.category == "unknown" or business_context.reliability == "inconclusive":
        return (
            False,
            None,
            "Local competitor discovery requires a confirmed business category.",
        )

    cat = business_context.category.lower()

    # Digital / SaaS / E-commerce businesses operate nationally/globally without physical storefronts
    if cat in ("technology", "saas", "ecommerce", "education", "nonprofit") and not location:
        return (
            False,
            None,
            "Local competitor analysis requires a verified physical business location. "
            "This website appears to operate primarily as a digital/global service.",
        )

    if not location or len(location.strip()) < 3:
        return (
            False,
            None,
            "Local competitor analysis could not be performed because a reliable physical business address was not identified on the website.",
        )

    # Derive search category term from deterministic classification
    search_term = CATEGORY_SEARCH_TERMS.get(cat, cat.replace("_", " "))
    return (True, search_term, None)


def _extract_domain(url: Optional[str]) -> str:
    """Extracts clean base domain for matching (e.g. 'dayspringind.com')."""
    if not url:
        return ""
    try:
        parsed = urlparse(url if "://" in url else f"http://{url}")
        netloc = parsed.netloc or parsed.path
        return netloc.lower().replace("www.", "").split(":")[0]
    except Exception:
        return ""


def _rank_and_filter_candidates_new_api(
    places_results: List[Dict[str, Any]],
    target_url: str,
    target_name: str,
    target_address: Optional[str] = None,
) -> List[CompetitorModel]:
    """
    Filters out target business and duplicates from Google Places API (New) response,
    then ranks candidates by relevance:
    1. Category/type relevance
    2. Geographic proximity / address presence
    3. Rating (>= 3.0 preferred)
    4. Review count
    5. Website presence
    Selects 3–5 strongest comparable competitors.
    """
    target_domain = _extract_domain(target_url)
    clean_target_name = re.sub(r"[^\w\s]", "", target_name.lower()).strip()

    candidates: List[Dict[str, Any]] = []
    seen_place_ids = set()
    seen_names = set()

    for item in places_results:
        place_id = item.get("id") or item.get("place_id")
        
        # In Places API (New), displayName is an object {"text": "Name", "languageCode": "en"}
        display_name_obj = item.get("displayName")
        if isinstance(display_name_obj, dict):
            name = display_name_obj.get("text", "").strip()
        elif isinstance(display_name_obj, str):
            name = display_name_obj.strip()
        else:
            name = item.get("name", "").strip()

        if not place_id or not name:
            continue

        if place_id in seen_place_ids:
            continue

        clean_name = re.sub(r"[^\w\s]", "", name.lower()).strip()
        if clean_name in seen_names:
            continue

        # Exclude target business itself by website domain
        item_website = item.get("websiteUri") or item.get("website", "")
        item_domain = _extract_domain(item_website)
        if target_domain and item_domain and target_domain == item_domain:
            continue

        # Exclude target business by name match
        if clean_target_name and (clean_name == clean_target_name or (len(clean_target_name) > 4 and clean_target_name in clean_name)):
            continue

        # Exclude target business by address match
        item_address = item.get("formattedAddress") or item.get("formatted_address") or item.get("vicinity") or ""
        if target_address and item_address and (target_address.lower() in item_address.lower() or item_address.lower() in target_address.lower()):
            continue

        rating = item.get("rating")
        try:
            rating_val = float(rating) if rating is not None else None
        except (ValueError, TypeError):
            rating_val = None

        review_count = item.get("userRatingCount") or item.get("user_ratings_total")
        try:
            review_count_val = int(review_count) if review_count is not None else None
        except (ValueError, TypeError):
            review_count_val = None

        types = item.get("types", [])

        # Calculate a comparability score for ranking
        score = 0.0
        if rating_val is not None and rating_val >= 3.0:
            score += rating_val * 2.0
        if review_count_val is not None:
            score += min(15.0, review_count_val / 20.0)
        if item_address:
            score += 3.0
        if item_website:
            score += 2.0

        seen_place_ids.add(place_id)
        seen_names.add(clean_name)

        primary_type = "Local Business"
        if types:
            filtered_types = [t for t in types if t not in ("point_of_interest", "establishment", "health", "service")]
            chosen = filtered_types[0] if filtered_types else types[0]
            primary_type = chosen.replace("_", " ").title()

        candidates.append({
            "place_id": place_id,
            "name": name,
            "rating": rating_val,
            "review_count": review_count_val,
            "address": item_address or None,
            "website_url": item_website or None,
            "category": primary_type,
            "score": score,
        })

    # Sort by comparability score descending
    candidates.sort(key=lambda c: c["score"], reverse=True)

    # Select top 3 to 5 competitors
    selected = candidates[:5]

    competitor_models: List[CompetitorModel] = []
    for c in selected:
        highlight_parts = []
        if c["rating"] and c["review_count"]:
            highlight_parts.append(f"Google rating of {c['rating']} ({c['review_count']} reviews)")
        elif c["rating"]:
            highlight_parts.append(f"Google rating of {c['rating']}")
        if c["website_url"]:
            highlight_parts.append("active web presence")
        elif c["address"]:
            highlight_parts.append("verified physical location")

        highlight_str = f"Established local presence with {', '.join(highlight_parts)}." if highlight_parts else "Verified local competitor."

        competitor_models.append(
            CompetitorModel(
                place_id=c["place_id"],
                name=c["name"],
                rating=c["rating"],
                review_count=c["review_count"],
                address=c["address"],
                distance_km=None,
                website_url=c["website_url"],
                category=c["category"],
                source="google_places",
                highlight=highlight_str,
            )
        )

    return competitor_models


def _derive_competitor_observations(
    competitors: List[CompetitorModel],
) -> Tuple[List[str], List[str]]:
    """
    Derives factual strengths and opportunities strictly based on verified competitor facts.
    Never promises rankings, traffic, or Google Maps positions.
    """
    strengths: List[str] = []
    opportunities: List[str] = []

    valid_ratings = [c.rating for c in competitors if c.rating is not None]
    valid_reviews = [c.review_count for c in competitors if c.review_count is not None]

    if valid_reviews:
        avg_reviews = sum(valid_reviews) // len(valid_reviews)
        max_reviews = max(valid_reviews)
        opportunities.append(
            f"Top local competitors have established Google Maps review volume (averaging ~{avg_reviews} reviews, up to {max_reviews}). Consider a systematic review collection process."
        )

    websites_count = sum(1 for c in competitors if c.website_url)
    if websites_count > 0:
        strengths.append(
            f"Active digital website presence relative to {websites_count} of {len(competitors)} local competitors with indexed web domains."
        )

    opportunities.append(
        "Maintain complete and consistent Name, Address, and Phone (NAP) citations across local directories to match local competitor presence."
    )

    return strengths, opportunities


async def discover_competitors(
    target_url: str,
    business_name: str,
    business_context: Optional[BusinessContextModel],
    fetch_data: Optional[RawFetchData] = None,
    content_analysis: Optional[ContentAnalysisResultModel] = None,
    client: Optional[httpx.AsyncClient] = None,
    api_key: Optional[str] = None,
    request_id: str = "",
    is_blocked: bool = False,
) -> CompetitorAnalysisModel:
    """
    Discovers 3–5 real local competitors using Google Places API (New).

    Guarantees:
    - Gated by deterministic location and category evidence.
    - Uses ONLY Google Places API (New) (https://places.googleapis.com/v1/places:searchText).
    - Digital / SaaS businesses cleanly return unavailable with no fake competitors.
    - Dedicated HTTP client isolation.
    - Jittered retry for transient errors.
    - Zero API key exposure.
    - Safe structured logging without logging keys or headers.
    - Fault-isolated (never crashes the overall analysis pipeline).
    """
    # 1. Deterministic Location Extraction
    location = extract_deterministic_location(fetch_data, content_analysis)

    # 2. Eligibility Gate
    is_eligible, search_category, rejection_reason = determine_competitor_eligibility(
        business_context=business_context,
        location=location,
        is_blocked=is_blocked,
    )

    logger.info(
        f"[GooglePlaces] request_id={request_id} target_url={target_url} "
        f"category={business_context.category if business_context else 'none'} "
        f"location_detected={bool(location)} eligible={is_eligible}"
    )

    if not is_eligible or not search_category or not location:
        return CompetitorAnalysisModel(
            status="unavailable",
            search_category=search_category,
            search_location=location,
            competitors=[],
            strengths=[],
            opportunities=[],
            reason=rejection_reason or "Local competitor discovery is not applicable for this website.",
            limitations=["Local competitor comparison requires verified local business signals."],
        )

    # 3. Check in-memory TTL cache
    cached = _get_from_cache(search_category, location)
    if cached is not None:
        logger.info(f"[GooglePlaces] request_id={request_id} cache_hit=True category={search_category} location={location}")
        return cached

    # 4. Resolve API Key
    effective_key = api_key if api_key is not None else settings.places_key
    if not effective_key or not effective_key.strip():
        return _unavailable(
            FailureCategory.CONFIGURATION_ERROR,
            search_cat=search_category,
            search_loc=location,
            request_id=request_id,
        )

    # 5. Build Places API (New) Request
    search_locality = extract_search_locality(location)
    query_str = f"{search_category} in {search_locality}"
    
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": effective_key.strip(),
        "X-Goog-FieldMask": "places.id,places.displayName,places.formattedAddress,places.location,places.types,places.rating,places.userRatingCount,places.websiteUri",
    }
    
    json_body = {
        "textQuery": query_str,
        "maxResultCount": 10,
    }

    timeout_sec = getattr(settings, "PLACES_TIMEOUT_SECONDS", 10.0)
    max_retries = getattr(settings, "PLACES_MAX_RETRIES", 2)
    deadline = getattr(settings, "PLACES_DEADLINE_SECONDS", 15.0)
    timeout_obj = httpx.Timeout(connect=5.0, read=timeout_sec, write=5.0, pool=5.0)

    own_client = False
    if client is None:
        client = httpx.AsyncClient(timeout=timeout_obj)
        own_client = True

    deadline_start = time.monotonic()

    try:
        for attempt in range(1, max_retries + 1):
            elapsed_total = time.monotonic() - deadline_start
            if elapsed_total >= deadline:
                logger.warning(f"[GooglePlaces] request_id={request_id} deadline_exceeded elapsed={elapsed_total:.1f}s")
                return _unavailable(
                    FailureCategory.DEADLINE_EXCEEDED,
                    search_cat=search_category,
                    search_loc=location,
                    request_id=request_id,
                )

            attempt_start = time.monotonic()
            try:
                logger.info(f"[GooglePlaces] request_id={request_id} attempt={attempt} endpoint=places:searchText query='{query_str}'")
                response = await client.post(PLACES_SEARCH_NEW_ENDPOINT, headers=headers, json=json_body)
                attempt_elapsed = time.monotonic() - attempt_start

                if response.status_code == 200:
                    data = response.json()
                    results = data.get("places", [])

                    if not results:
                        logger.info(f"[GooglePlaces] request_id={request_id} zero_results for query='{query_str}'")
                        return CompetitorAnalysisModel(
                            status="inconclusive",
                            search_category=search_category,
                            search_location=location,
                            competitors=[],
                            strengths=[],
                            opportunities=[],
                            reason="No sufficiently comparable local competitors were found in Google Places for this location.",
                            limitations=["Search returned zero matching places."],
                        )

                    # Filter and rank candidates
                    competitors = _rank_and_filter_candidates_new_api(
                        places_results=results,
                        target_url=target_url,
                        target_name=business_name,
                        target_address=location,
                    )

                    if len(competitors) < 2:
                        return CompetitorAnalysisModel(
                            status="inconclusive",
                            search_category=search_category,
                            search_location=location,
                            competitors=competitors,
                            strengths=[],
                            opportunities=[],
                            reason="Insufficient comparable local competitors were found after filtering out the target business.",
                            limitations=["Fewer than 2 independent local competitors identified."],
                        )

                    strengths, opportunities = _derive_competitor_observations(competitors)

                    analysis_model = CompetitorAnalysisModel(
                        status="available",
                        search_category=search_category,
                        search_location=location,
                        competitors=competitors,
                        strengths=strengths,
                        opportunities=opportunities,
                        reason=None,
                        limitations=[],
                    )

                    _save_to_cache(search_category, location, analysis_model)
                    logger.info(f"[GooglePlaces] request_id={request_id} successfully found {len(competitors)} competitors in {attempt_elapsed:.1f}s")
                    return analysis_model

                elif response.status_code in (401, 403):
                    logger.warning(f"[GooglePlaces] request_id={request_id} auth_error status={response.status_code}")
                    return _unavailable(
                        FailureCategory.AUTHENTICATION_ERROR,
                        search_cat=search_category,
                        search_loc=location,
                        request_id=request_id,
                    )

                elif response.status_code == 429:
                    if attempt < max_retries:
                        delay = (1.0 * (2 ** (attempt - 1))) + random.uniform(0, 0.5)
                        await asyncio.sleep(delay)
                        continue
                    return _unavailable(
                        FailureCategory.RATE_LIMITED,
                        search_cat=search_category,
                        search_loc=location,
                        request_id=request_id,
                    )

                elif response.status_code in (500, 502, 503, 504):
                    if attempt < max_retries:
                        delay = (1.0 * (2 ** (attempt - 1))) + random.uniform(0, 0.5)
                        await asyncio.sleep(delay)
                        continue
                    return _unavailable(
                        FailureCategory.SERVER_ERROR,
                        search_cat=search_category,
                        search_loc=location,
                        request_id=request_id,
                    )

                else:
                    logger.warning(f"[GooglePlaces] request_id={request_id} unexpected status={response.status_code}")
                    return _unavailable(
                        FailureCategory.UNKNOWN_ERROR,
                        search_cat=search_category,
                        search_loc=location,
                        request_id=request_id,
                    )

            except httpx.TimeoutException as timeout_exc:
                category = _classify_timeout(timeout_exc)
                if attempt < max_retries:
                    delay = (1.0 * (2 ** (attempt - 1))) + random.uniform(0, 0.5)
                    await asyncio.sleep(delay)
                    continue
                return _unavailable(
                    category,
                    search_cat=search_category,
                    search_loc=location,
                    request_id=request_id,
                )

            except httpx.NetworkError:
                if attempt < max_retries:
                    delay = (1.0 * (2 ** (attempt - 1))) + random.uniform(0, 0.5)
                    await asyncio.sleep(delay)
                    continue
                return _unavailable(
                    FailureCategory.NETWORK_ERROR,
                    search_cat=search_category,
                    search_loc=location,
                    request_id=request_id,
                )

        return _unavailable(
            FailureCategory.UNKNOWN_ERROR,
            search_cat=search_category,
            search_loc=location,
            request_id=request_id,
        )

    except Exception as exc:
        logger.warning(f"[GooglePlaces] request_id={request_id} unexpected error: {exc}")
        return _unavailable(
            FailureCategory.UNKNOWN_ERROR,
            search_cat=search_category,
            search_loc=location,
            request_id=request_id,
        )
    finally:
        if own_client:
            await client.aclose()
