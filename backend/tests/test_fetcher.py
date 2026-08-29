import pytest
import httpx
from app.services.fetcher import fetch_website


@pytest.mark.anyio
async def test_fetch_website_invalid_url():
    result = await fetch_website("not-a-valid-url")
    assert result.success is False
    assert result.error_type == "invalid_url"


@pytest.mark.anyio
async def test_fetch_website_unreachable_domain():
    # Attempting to fetch a nonexistent top-level testing domain
    result = await fetch_website("https://nonexistent-domain-123456789.invalid")
    assert result.success is False
    assert result.error_type == "unreachable_domain"
    assert "connection" in (result.error_message or "").lower()


@pytest.mark.anyio
async def test_fetch_website_mock_redirect():
    # Setup custom mock transport for redirect chain
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url == "http://old-domain.com":
            return httpx.Response(
                301,
                headers={"Location": "https://new-domain.com"},
                request=request,
            )
        elif request.url == "https://new-domain.com":
            return httpx.Response(
                200,
                text="<html><head><title>New Domain</title></head><body><h1>Welcome</h1></body></html>",
                headers={"Content-Type": "text/html; charset=utf-8"},
                request=request,
            )
        return httpx.Response(404, request=request)

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport, follow_redirects=True) as client:
        result = await fetch_website("http://old-domain.com", client=client)
        assert result.success is True
        assert result.final_url == "https://new-domain.com"
        assert result.status_code == 200
        assert result.parsed_data is not None
        assert result.parsed_data.title == "New Domain"


@pytest.mark.anyio
async def test_fetch_website_mock_timeout():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("Read timed out", request=request)

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        result = await fetch_website("https://slow-domain.com", client=client)
        assert result.success is False
        assert result.error_type == "timeout"
        assert "timed out" in (result.error_message or "").lower()


@pytest.mark.anyio
async def test_fetch_website_mock_404():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, text="<html><body>Not Found</body></html>", request=request)

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        result = await fetch_website("https://missing-page.com/404", client=client)
        assert result.success is False
        assert result.status_code == 404
        assert result.error_type == "http_error"
