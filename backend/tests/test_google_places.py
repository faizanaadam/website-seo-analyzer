import pytest
from unittest.mock import patch, MagicMock
import httpx
from bs4 import BeautifulSoup

from app.models import (
    BusinessContextModel,
    ContentAnalysisResultModel,
    ContactInfoModel,
    CTAModel,
    ServiceStructureModel,
    CompetitorAnalysisModel,
    CompetitorModel,
    RawFetchData,
)
from app.services.google_places import (
    extract_deterministic_location,
    determine_competitor_eligibility,
    _rank_and_filter_candidates_new_api,
    discover_competitors,
    clear_places_cache,
    _places_cache,
    PLACES_SEARCH_NEW_ENDPOINT,
)
from app.services.content_analysis import extract_ctas_and_contact


def make_mock_content(address: str = None) -> ContentAnalysisResultModel:
    return ContentAnalysisResultModel(
        pages_analyzed=[],
        total_pages_analyzed=1,
        homepage_word_count=500,
        average_word_count=500,
        contact_info=ContactInfoModel(
            phones=[],
            emails=[],
            address=address,
            opening_hours=None,
        ),
        ctas=CTAModel(),
        services_structure=ServiceStructureModel(
            has_dedicated_service_pages=True,
            services_mainly_on_homepage=False,
            service_pages_count=2,
            detected_services=["Service A"],
        ),
        summary="Mock summary",
    )


@pytest.fixture(autouse=True)
def reset_cache():
    clear_places_cache()
    yield
    clear_places_cache()


def test_extract_deterministic_location_from_contact_info():
    content = make_mock_content(address="123 Health Ave, Suite 400, Chicago, IL 60601")
    loc = extract_deterministic_location(fetch_data=None, content_analysis=content)
    assert loc == "123 Health Ave, Suite 400, Chicago, IL 60601"


def test_extract_deterministic_location_missing():
    content = make_mock_content(address=None)
    loc = extract_deterministic_location(fetch_data=None, content_analysis=content)
    assert loc is None


def test_schema_org_medical_clinic_address_detection():
    html = """
    <html>
    <head>
        <script type="application/ld+json">
        {
            "@context": "https://schema.org",
            "@type": "MedicalClinic",
            "name": "DaySpring Multispeciality Clinic",
            "address": {
                "@type": "PostalAddress",
                "streetAddress": "JJ Square, M P Pylee Road",
                "addressLocality": "Kochi",
                "addressRegion": "Kerala",
                "postalCode": "682020",
                "addressCountry": "India"
            }
        }
        </script>
    </head>
    <body><h1>Welcome</h1></body>
    </html>
    """
    soup = BeautifulSoup(html, "html.parser")
    res = extract_ctas_and_contact(soup, "https://dayspringind.com", "https://dayspringind.com")
    assert res["address"] is not None
    assert "Kochi" in res["address"]
    assert "682020" in res["address"]


def test_schema_org_graph_postal_address_detection():
    html = """
    <html>
    <head>
        <script type="application/ld+json">
        {
            "@context": "https://schema.org",
            "@graph": [
                {
                    "@type": "PostalAddress",
                    "streetAddress": "54/1285-B JJ Square",
                    "addressLocality": "Kochi",
                    "addressRegion": "Kerala",
                    "postalCode": "682020"
                }
            ]
        }
        </script>
    </head>
    <body><h1>Clinic</h1></body>
    </html>
    """
    soup = BeautifulSoup(html, "html.parser")
    res = extract_ctas_and_contact(soup, "https://dayspringind.com", "https://dayspringind.com")
    assert res["address"] is not None
    assert "54/1285-B JJ Square" in res["address"]


def test_visible_html_address_detection():
    html = """
    <html>
    <body>
        <div class="footer-contact">
            <span class="elementor-icon-list-text">54/1285-B first Floor JJ Square, M P Pylee Road, Main Avenue, Kadavanthra P.O, Jawahar Nagar, Kochi, Kerala 682020</span>
        </div>
    </body>
    </html>
    """
    soup = BeautifulSoup(html, "html.parser")
    res = extract_ctas_and_contact(soup, "https://dayspringind.com", "https://dayspringind.com")
    assert res["address"] is not None
    assert "JJ Square" in res["address"]
    assert "682020" in res["address"]


def test_semantic_address_tag_detection():
    html = """
    <html>
    <body>
        <address>
            742 Evergreen Terrace, Springfield, OR 97477
        </address>
    </body>
    </html>
    """
    soup = BeautifulSoup(html, "html.parser")
    res = extract_ctas_and_contact(soup, "https://simpsons.com", "https://simpsons.com")
    assert res["address"] == "742 Evergreen Terrace, Springfield, OR 97477"


def test_eligibility_gating_digital_saas_without_storefront():
    biz_ctx = BusinessContextModel(
        category="saas",
        confidence="high",
        evidence=["Cloud platform"],
        reliability="factual",
    )
    is_eligible, search_cat, reason = determine_competitor_eligibility(
        business_context=biz_ctx,
        location=None,
        is_blocked=False,
    )
    assert is_eligible is False
    assert search_cat is None
    assert "digital/global service" in reason


def test_eligibility_gating_generic_example():
    biz_ctx = BusinessContextModel(
        category="unknown",
        confidence="low",
        evidence=[],
        reliability="inconclusive",
    )
    is_eligible, search_cat, reason = determine_competitor_eligibility(
        business_context=biz_ctx,
        location=None,
        is_blocked=False,
    )
    assert is_eligible is False
    assert "requires a confirmed business category" in reason


def test_eligibility_gating_local_business_with_address():
    biz_ctx = BusinessContextModel(
        category="local_business",
        confidence="high",
        evidence=["Auto repair service"],
        reliability="factual",
    )
    is_eligible, search_cat, reason = determine_competitor_eligibility(
        business_context=biz_ctx,
        location="123 Main St, Austin, TX",
        is_blocked=False,
    )
    assert is_eligible is True
    assert "auto repair" in search_cat
    assert reason is None


def test_eligibility_gating_healthcare_with_address():
    biz_ctx = BusinessContextModel(
        category="healthcare",
        confidence="high",
        evidence=["Medical clinic in Kochi"],
        reliability="factual",
    )
    is_eligible, search_cat, reason = determine_competitor_eligibility(
        business_context=biz_ctx,
        location="54/1285-B JJ Square, Kochi, Kerala 682020",
        is_blocked=False,
    )
    assert is_eligible is True
    assert "clinic" in search_cat
    assert reason is None


def test_eligibility_gating_blocked_crawler():
    biz_ctx = BusinessContextModel(
        category="healthcare",
        confidence="high",
        evidence=["Clinic"],
        reliability="factual",
    )
    is_eligible, search_cat, reason = determine_competitor_eligibility(
        business_context=biz_ctx,
        location="123 Main St",
        is_blocked=True,
    )
    assert is_eligible is False
    assert "crawler access was challenged" in reason


def test_rank_and_filter_candidates_places_new_api():
    places_raw = [
        {
            "id": "target_id",
            "displayName": {"text": "Apex Auto Care"},
            "rating": 4.9,
            "userRatingCount": 350,
            "formattedAddress": "100 Broadway, New York, NY",
            "websiteUri": "https://apexautocare.com",
            "types": ["car_repair", "point_of_interest"],
        },
        {
            "id": "comp_1",
            "displayName": {"text": "Broadway Auto Clinic"},
            "rating": 4.8,
            "userRatingCount": 210,
            "formattedAddress": "120 Broadway, New York, NY",
            "websiteUri": "https://broadwayautoclinic.com",
            "types": ["car_repair", "point_of_interest"],
        },
        {
            "id": "comp_2",
            "displayName": {"text": "Manhattan Master Mechanics"},
            "rating": 4.6,
            "userRatingCount": 95,
            "formattedAddress": "200 5th Ave, New York, NY",
            "websiteUri": "https://manhattanmechanics.com",
            "types": ["car_repair", "point_of_interest"],
        },
        {
            "id": "comp_3",
            "displayName": {"text": "Downtown Tire & Brake"},
            "rating": 4.5,
            "userRatingCount": 140,
            "formattedAddress": "50 Wall St, New York, NY",
            "websiteUri": None,
            "types": ["car_repair"],
        },
    ]

    competitors = _rank_and_filter_candidates_new_api(
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
async def test_discover_competitors_places_new_api_success():
    biz_ctx = BusinessContextModel(
        category="healthcare",
        confidence="high",
        evidence=["Medical clinic"],
        reliability="factual",
    )
    content = make_mock_content(address="54/1285-B JJ Square, Kochi, Kerala 682020")

    mock_places_response = {
        "places": [
            {
                "id": "target_id",
                "displayName": {"text": "DaySpring Multispeciality Clinic"},
                "rating": 4.9,
                "userRatingCount": 1209,
                "formattedAddress": "54/1285-B JJ Square, Kochi, Kerala 682020",
                "websiteUri": "https://www.dayspringind.com",
                "types": ["medical_clinic"],
            },
            {
                "id": "comp_1",
                "displayName": {"text": "True Life Medical Centre"},
                "rating": 4.4,
                "userRatingCount": 180,
                "formattedAddress": "Subhash Chandra Bose Rd, Kochi, Kerala 682019",
                "websiteUri": "https://truelifemedicalcentre.com",
                "types": ["medical_clinic"],
            },
            {
                "id": "comp_2",
                "displayName": {"text": "Ernakulam Medical Centre"},
                "rating": 4.5,
                "userRatingCount": 4350,
                "formattedAddress": "NH 66, Palarivattom, Kochi, Kerala 682028",
                "websiteUri": "https://www.emccochin.com",
                "types": ["medical_clinic"],
            },
        ]
    }

    recorded_headers = {}
    recorded_json = {}

    def handler(request: httpx.Request):
        nonlocal recorded_headers, recorded_json
        recorded_headers = dict(request.headers)
        import json
        recorded_json = json.loads(request.read())
        return httpx.Response(200, json=mock_places_response)

    mock_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))

    result = await discover_competitors(
        target_url="https://www.dayspringind.com",
        business_name="DaySpring Multispeciality Clinic",
        business_context=biz_ctx,
        content_analysis=content,
        client=mock_client,
        api_key="test_places_key",
    )

    # Verify Places API (New) Headers
    assert recorded_headers.get("x-goog-api-key") == "test_places_key"
    assert "places.id" in recorded_headers.get("x-goog-fieldmask", "")
    assert "places.displayName" in recorded_headers.get("x-goog-fieldmask", "")

    # Verify Places API (New) Body
    assert "textQuery" in recorded_json
    assert "Kochi" in recorded_json["textQuery"]

    # Verify result
    assert result.status == "available"
    assert len(result.competitors) == 2
    assert all(c.name != "DaySpring Multispeciality Clinic" for c in result.competitors)
    assert result.competitors[0].name in ("True Life Medical Centre", "Ernakulam Medical Centre")
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
        "places": [
            {
                "id": "h_1",
                "displayName": {"text": "The Oberoi Mumbai"},
                "rating": 4.9,
                "userRatingCount": 4500,
                "formattedAddress": "Nariman Point, Mumbai, India",
                "types": ["lodging"],
            },
            {
                "id": "h_2",
                "displayName": {"text": "Trident Hotel Mumbai"},
                "rating": 4.7,
                "userRatingCount": 3200,
                "formattedAddress": "Nariman Point, Mumbai, India",
                "types": ["lodging"],
            },
        ]
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
        client=None,
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

    result = await discover_competitors(
        target_url="https://seattleplumbing.com",
        business_name="Seattle Plumbing",
        business_context=biz_ctx,
        content_analysis=content,
        api_key="",
    )
    assert result.status == "unavailable"
    assert "not configured" in result.reason
