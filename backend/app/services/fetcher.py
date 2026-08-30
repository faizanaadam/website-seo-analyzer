import time
import httpx
from typing import Optional, Dict, Any, List
from app.utils.url_helpers import normalize_url, resolve_url
from app.services.html_parser import parse_html, ParsedHTMLData

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)

DEFAULT_HEADERS = {
    "User-Agent": DEFAULT_USER_AGENT,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Cache-Control": "no-cache",
    "Pragma": "no-cache",
}

DEFAULT_TIMEOUT = httpx.Timeout(connect=6.0, read=10.0, write=5.0, pool=10.0)


class FetchResult:
    def __init__(
        self,
        success: bool,
        initial_url: str,
        final_url: Optional[str] = None,
        status_code: Optional[int] = None,
        response_time_ms: Optional[int] = None,
        content_type: Optional[str] = None,
        redirect_chain: Optional[List[str]] = None,
        raw_html: Optional[str] = None,
        parsed_data: Optional[ParsedHTMLData] = None,
        robots_txt_present: bool = False,
        sitemap_xml_present: bool = False,
        content_accessible: bool = True,
        content_reliability: str = "reliable",
        error_type: Optional[str] = None,
        error_message: Optional[str] = None,
    ):
        self.success = success
        self.initial_url = initial_url
        self.final_url = final_url or initial_url
        self.status_code = status_code
        self.response_time_ms = response_time_ms
        self.content_type = content_type
        self.redirect_chain = redirect_chain or []
        self.raw_html = raw_html
        self.parsed_data = parsed_data
        self.robots_txt_present = robots_txt_present
        self.sitemap_xml_present = sitemap_xml_present
        self.content_accessible = content_accessible
        self.content_reliability = content_reliability
        self.error_type = error_type
        self.error_message = error_message

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "initial_url": self.initial_url,
            "final_url": self.final_url,
            "status_code": self.status_code,
            "response_time_ms": self.response_time_ms,
            "content_type": self.content_type,
            "redirect_chain": self.redirect_chain,
            "robots_txt_present": self.robots_txt_present,
            "sitemap_xml_present": self.sitemap_xml_present,
            "content_accessible": self.content_accessible,
            "content_reliability": self.content_reliability,
            "parsed_data": self.parsed_data.to_dict() if self.parsed_data else None,
            "error_type": self.error_type,
            "error_message": self.error_message,
        }


async def fetch_website(raw_url: str, client: Optional[httpx.AsyncClient] = None) -> FetchResult:
    """
    Fetches and parses a website safely with redirects, timeouts, and error handling.
    """
    # 1. Normalize user input URL
    try:
        normalized_url = normalize_url(raw_url)
    except ValueError as val_err:
        return FetchResult(
            success=False,
            initial_url=raw_url,
            content_accessible=False,
            content_reliability="unreliable",
            error_type="invalid_url",
            error_message=str(val_err),
        )

    own_client = False
    if client is None:
        client = httpx.AsyncClient(
            headers=DEFAULT_HEADERS,
            timeout=DEFAULT_TIMEOUT,
            follow_redirects=True,
            max_redirects=5,
            verify=False,  # Allow sites with self-signed / slightly misconfigured certs while noting it
        )
        own_client = True

    start_time = time.time()
    try:
        response = await client.get(normalized_url)
        elapsed_ms = int((time.time() - start_time) * 1000)

        # Collect redirect history
        redirect_chain = [str(r.url) for r in response.history]
        final_url = str(response.url)
        content_type = response.headers.get("content-type", "")

        # Check for bot block / WAF challenges (e.g. 403 Forbidden, 429 Rate Limit, Cloudflare, Akamai)
        lower_text = response.text.lower() if response.text else ""
        is_bot_blocked = (
            response.status_code in (403, 429)
            or (
                response.status_code in (503, 401)
                and (
                    "cloudflare" in lower_text
                    or "bot" in lower_text
                    or "access denied" in lower_text
                    or "edgesuite" in lower_text
                    or "akamai" in lower_text
                    or "incapsula" in lower_text
                    or "datadome" in lower_text
                    or "security challenge" in lower_text
                )
            )
        )
        if is_bot_blocked:
            parsed_data = parse_html(response.text, final_url)
            # Parallel check robots.txt and sitemap.xml
            robots_present, sitemap_present = await check_robots_and_sitemap(final_url, client)

            return FetchResult(
                success=True,
                initial_url=normalized_url,
                final_url=final_url,
                status_code=response.status_code,
                response_time_ms=elapsed_ms,
                content_type=content_type,
                redirect_chain=redirect_chain,
                raw_html=response.text,
                parsed_data=parsed_data,
                robots_txt_present=robots_present,
                sitemap_xml_present=sitemap_present,
                content_accessible=False,
                content_reliability="unreliable",
                error_type="bot_protection_detected",
                error_message=f"Website returned an automated access or bot-protection challenge (HTTP {response.status_code}). Page content cannot be treated as actual website copy.",
            )

        # Check for HTTP errors (404, 500, etc.)
        if response.status_code >= 400:
            parsed_data = parse_html(response.text, final_url) if response.text else None
            return FetchResult(
                success=False,
                initial_url=normalized_url,
                final_url=final_url,
                status_code=response.status_code,
                response_time_ms=elapsed_ms,
                content_type=content_type,
                redirect_chain=redirect_chain,
                raw_html=response.text,
                parsed_data=parsed_data,
                content_accessible=False,
                content_reliability="unreliable",
                error_type="http_error",
                error_message=f"Server returned HTTP status code {response.status_code}",
            )

        # Parse HTML
        parsed_data = parse_html(response.text, final_url)

        # 2. Check for robots.txt & sitemap.xml
        robots_present, sitemap_present = await check_robots_and_sitemap(final_url, client)

        return FetchResult(
            success=True,
            initial_url=normalized_url,
            final_url=final_url,
            status_code=response.status_code,
            response_time_ms=elapsed_ms,
            content_type=content_type,
            redirect_chain=redirect_chain,
            raw_html=response.text,
            parsed_data=parsed_data,
            robots_txt_present=robots_present,
            sitemap_xml_present=sitemap_present,
        )

    except httpx.ConnectError:
        return FetchResult(
            success=False,
            initial_url=normalized_url,
            error_type="unreachable_domain",
            error_message="Could not establish connection to the domain. Verify domain name and DNS status.",
        )
    except httpx.TimeoutException:
        return FetchResult(
            success=False,
            initial_url=normalized_url,
            error_type="timeout",
            error_message="Connection timed out after 10 seconds. The server may be experiencing downtime or excessive load.",
        )
    except httpx.SSLError as ssl_err:
        return FetchResult(
            success=False,
            initial_url=normalized_url,
            error_type="ssl_error",
            error_message=f"SSL certificate handshake failed: {str(ssl_err)}",
        )
    except Exception as exc:
        return FetchResult(
            success=False,
            initial_url=normalized_url,
            error_type="fetch_exception",
            error_message=f"An unexpected error occurred while fetching the website: {str(exc)}",
        )
    finally:
        if own_client:
            await client.aclose()


async def check_robots_and_sitemap(base_url: str, client: httpx.AsyncClient) -> tuple[bool, bool]:
    """
    Checks if /robots.txt and /sitemap.xml exist and return HTTP 200.
    """
    robots_url = resolve_url(base_url, "/robots.txt")
    sitemap_url = resolve_url(base_url, "/sitemap.xml")

    robots_present = False
    sitemap_present = False

    if robots_url:
        try:
            res = await client.get(robots_url, timeout=4.0)
            if res.status_code == 200 and "user-agent" in res.text.lower():
                robots_present = True
        except Exception:
            pass

    if sitemap_url:
        try:
            res = await client.get(sitemap_url, timeout=4.0)
            if res.status_code == 200 and ("<urlset" in res.text or "<sitemapindex" in res.text):
                sitemap_present = True
        except Exception:
            pass

    return robots_present, sitemap_present
