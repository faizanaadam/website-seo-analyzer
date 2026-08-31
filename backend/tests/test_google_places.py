import pytest
import httpx
from unittest.mock import patch, MagicMock

from app.models import (
    BusinessContextModel,
    ContentAnalysisResultModel,
    ContactInfoModel,
    CTAModel,
    ServiceStructureModel,
    CompetitorAnalysisModel,
)
from app.services.google_places import (
    extract_deterministic_location,
    determine_competitor_eligibility,
    discover_competitors,
    _rank_and_filter_candidates,
    _derive_competitor_observations,
    clear_places_cache,
    _places_cache,
)


@pytest.fixture(autouse=True)
def reset_cache():
    """Automatically clear in-memory cache before every test."""
    clear_places_cache()


def make_mock_content(address: str = None) -> ContentAnalysisResultModel:
    """Helper to construct valid ContentAnalysisResultModel for testing."""
    return ContentAnalysisResultModel(
        pages_analyzed=[],
        total_pages_analyzed=1,
        homepage_word_count=500,
        average_word_count=500,
        contact_info=ContactInfoModel(
            address=address,
            phones=[],
            emails=[],
        ),
        ctas=CTAModel(),
        services_structure=ServiceStructureModel(
            has_dedicated_service_pages=True,
            services_mainly_on_homepage=False,
            service_pages_count=3,
        ),
        summary="Sample website content",
        is_inconclusive=False,
    )


def test_extract_deterministic_location_from_contact_info():
    content = make_mock_content(address="123 Main St, Austin, TX 78701")
    loc = extract_deterministic_location(fetch_data=None, content_analysis=content)
    assert loc == "123 Main St, Austin, TX 78701"


def test_extract_deterministic_location_missing():
    content = make_mock_content(address=None)
    loc = extract_deterministic_location(fetch_data=None, content_analysis=content)
    assert loc is None


def test_eligibility_gating_digital_saas_without_storefront():
    # Digital / SaaS website (e.g. theneuralake.com)
    biz_ctx = BusinessContextModel(
        category="technology",
        confidence="high",
        evidence=["AI and cloud data lake solutions"],
        reliability="factual",
    )
    is_eligible, search_cat, reason = determine_competitor_eligibility(
        business_context=biz_ctx,
        location=None,
    )
    assert is_eligible is False
    assert search_cat is None
    assert "digital/global service" in reason


def test_eligibility_gating_generic_example():
    # Generic / Unknown website (e.g. example.com)
    biz_ctx = BusinessContextModel(
        category="unknown",
        confidence="none",
        evidence=["No business signals"],
        reliability="inconclusive",
    )
    is_eligible, search_cat, reason = determine_competitor_eligibility(
        business_context=biz_ctx,
        location=None,
    )
    assert is_eligible is False
    assert search_cat is None
    assert "requires a confirmed business category" in reason


def test_eligibility_gating_local_business_with_address():
    biz_ctx = BusinessContextModel(
        category="local_business",
        confidence="high",
        evidence=["Auto repair and brake service"],
        reliability="factual",
    )
    is_eligible, search_cat, reason = determine_competitor_eligibility(
        business_context=biz_ctx,
        location="450 Sutter St, San Francisco, CA",
    )
    assert is_eligible is True
    assert "auto repair" in search_cat
    assert reason is None


def test_eligibility_gating_hospitality_with_address():
    biz_ctx = BusinessContextModel(
        category="hospitality",
        confidence="high",
        evidence=["Luxury hotel and resort suites"],
        reliability="factual",
    )
    is_eligible, search_cat, reason = determine_competitor_eligibility(
        business_context=biz_ctx,
        location="Apollo Bunder, Mumbai, Maharashtra 400001",
    )
    assert is_eligible is True
    assert "hotel" in search_cat
    assert reason is None


def test_eligibility_gating_blocked_crawler():
    biz_ctx = BusinessContextModel(
        category="healthcare",
        confidence="high",
        evidence=["Dental clinic"],
        reliability="factual",
    )
    is_eligible, search_cat, reason = determine_competitor_eligibility(
        business_context=biz_ctx,
        location="123 Main St",
        is_blocked=True,
    )
    assert is_eligible is False
    assert "crawler access was challenged" in reason


def test_rank_and_filter_candidates_target_exclusion():
    places_raw = [
        {
            "place_id": "target_id",
            "name": "Apex Auto Care",
            "rating": 4.9,
            "user_ratings_total": 350,
            "formatted_address": "100 Broadway, New York, NY",
            "website": "https://apexautocare.com",
            "types": ["car_repair", "point_of_interest"],
        },
        {
            "place_id": "comp_1",
            "name": "Broadway Auto Clinic",
            "rating": 4.8,
            "user_ratings_total": 210,
            "formatted_address": "120 Broadway, New York, NY",
            "website": "https://broadwayautoclinic.com",
            "types": ["car_repair", "point_of_interest"],
        },
        {
            "place_id": "comp_2",
            "name": "Manhattan Master Mechanics",
            "rating": 4.6,
            "user_ratings_total": 95,
            "formatted_address": "200 5th Ave, New York, NY",
            "website": "https://manhattanmechanics.com",
            "types": ["car_repair", "point_of_interest"],
        },
        {
            "place_id": "comp_3",
            "name": "Downtown Tire & Brake",
            "rating": 4.5,
            "user_ratings_total": 140,
            "formatted_address": "50 Wall St, New York, NY",
            "website": None,
            "types": ["car_repair"],
        },
    ]

    competitors = _rank_and_filter_candidates(
        places_results=places_raw,
        target_url="https://apexautocare.com",
        target_name="Apex Auto Care",
        target_address="100 Broadway, New York, NY",
    )

    assert len(competitors) == 3
    # Apex Auto Care must be excluded
    assert all(c.name != "Apex Auto Care" for c in competitors)
    assert all(c.place_id != "target_id" for c in competitors)
    assert competitors[0].name == "Broadway Auto Clinic"
    assert competitors[0].rating == 4.8
    assert competitors[0].review_count == 210


@pytest.mark.anyio
async def test_discover_competitors_gated_out_digital_site():
    # theneuralake.com should cleanly return unavailable without calling Places API
    biz_ctx = BusinessContextModel(
        category="technology",
        confidence="high",
        evidence=["AI Lakehouse platform"],
        reliability="factual",
    )

    result = await discover_competitors(
        target_url="https://theneuralake.com",
        business_name="Neuralake",
        business_context=biz_ctx,
        fetch_data=None,
        content_analysis=None,
        api_key="fake_key",
    )

    assert result.status == "unavailable"
    assert len(result.competitors) == 0
    assert "digital/global service" in result.reason


@pytest.mark.anyio
async def test_discover_competitors_success_mocked():
    biz_ctx = BusinessContextModel(
        category="local_business",
        confidence="high",
        evidence=["Automotive repair"],
        reliability="factual",
    )
    content = make_mock_content(address="100 Broadway, New York, NY")

    mock_places_response = {
        "status": "OK",
        "results": [
            {
                "place_id": "p_target",
                "name": "Target Auto",
                "rating": 4.9,
                "user_ratings_total": 50,
                "formatted_address": "100 Broadway, New York, NY",
                "types": ["car_repair"],
            },
            {
                "place_id": "p_1",
                "name": "City Auto Care",
                "rating": 4.8,
                "user_ratings_total": 120,
                "formatted_address": "110 Broadway, New York, NY",
                "website": "https://cityautocare.com",
                "types": ["car_repair"],
            },
            {
                "place_id": "p_2",
                "name": "NYC Brake & Muffler",
                "rating": 4.7,
                "user_ratings_total": 85,
                "formatted_address": "150 Broadway, New York, NY",
                "website": "https://nycbrakes.com",
                "types": ["car_repair"],
            },
        ],
    }

    mock_client = httpx.AsyncClient(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(200, json=mock_places_response)
        )
    )

    result = await discover_competitors(
        target_url="https://targetauto.com",
        business_name="Target Auto",
        business_context=biz_ctx,
        content_analysis=content,
        client=mock_client,
        api_key="test_places_key",
    )

    assert result.status == "available"
    assert len(result.competitors) == 2
    assert result.competitors[0].name == "City Auto Care"
    assert result.competitors[1].name == "NYC Brake & Muffler"
    assert len(result.opportunities) > 0


@pytest.mark.anyio
async def test_discover_competitors_caching():
    biz_ctx = BusinessContextModel(
        category="hospitality",
        confidence="high",
        evidence=["Luxury hotel"],
        reliability="factual",
    )
    content = make_mock_content(address="Apollo Bunder, Mumbai, India")

    mock_places_response = {
        "status": "OK",
        "results": [
            {
                "place_id": "h_1",
                "name": "The Oberoi Mumbai",
                "rating": 4.9,
                "user_ratings_total": 4500,
                "formatted_address": "Nariman Point, Mumbai, India",
                "types": ["lodging"],
            },
            {
                "place_id": "h_2",
                "name": "Trident Hotel Mumbai",
                "rating": 4.7,
                "user_ratings_total": 3200,
                "formatted_address": "Nariman Point, Mumbai, India",
                "types": ["lodging"],
            },
        ],
    }

    mock_client = httpx.AsyncClient(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(200, json=mock_places_response)
        )
    )

    # First call: hits mock transport and saves to cache
    res1 = await discover_competitors(
        target_url="https://tajhotels.com",
        business_name="Taj Mahal Palace",
        business_context=biz_ctx,
        content_analysis=content,
        client=mock_client,
        api_key="test_places_key",
    )
    assert res1.status == "available"
    assert len(_places_cache) == 1

    # Second call: returns cached result immediately without using client
    res2 = await discover_competitors(
        target_url="https://tajhotels.com",
        business_name="Taj Mahal Palace",
        business_context=biz_ctx,
        content_analysis=content,
        client=None,  # No client passed
        api_key="test_places_key",
    )
    assert res2.status == "available"
    assert res2.competitors[0].name == "The Oberoi Mumbai"


@pytest.mark.anyio
async def test_discover_competitors_api_key_missing():
    biz_ctx = BusinessContextModel(
        category="local_business",
        confidence="high",
        evidence=["Plumbing service"],
        reliability="factual",
    )
    content = make_mock_content(address="789 Pine St, Seattle, WA")

    # Pass empty api_key string
    result = await discover_competitors(
        target_url="https://seattleplumbing.com",
        business_name="Seattle Plumbing",
        business_context=biz_ctx,
        content_analysis=content,
        api_key="",
    )
    assert result.status == "unavailable"
    assert "not configured" in result.reason
