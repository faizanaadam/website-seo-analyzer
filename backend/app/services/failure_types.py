"""
Structured failure classification for external API integrations.

Internal failure categories are used for precise logging and diagnostics.
Each category maps to a safe, human-readable message for the frontend.
"""


class FailureCategory:
    """Internal failure categories for structured error classification."""
    CONFIGURATION_ERROR = "configuration_error"
    AUTHENTICATION_ERROR = "authentication_error"
    INVALID_REQUEST = "invalid_request"
    CONNECT_TIMEOUT = "connect_timeout"
    READ_TIMEOUT = "read_timeout"
    POOL_TIMEOUT = "pool_timeout"
    NETWORK_ERROR = "network_error"
    RATE_LIMITED = "rate_limited"
    SERVER_ERROR = "server_error"
    UPSTREAM_UNAVAILABLE = "upstream_unavailable"
    MALFORMED_RESPONSE = "malformed_response"
    VALIDATION_ERROR = "validation_error"
    DEADLINE_EXCEEDED = "deadline_exceeded"
    UNKNOWN_ERROR = "unknown_error"


# Safe user-facing messages per service and failure category
OPENAI_USER_MESSAGES = {
    FailureCategory.CONFIGURATION_ERROR: "OpenAI API key is not configured.",
    FailureCategory.AUTHENTICATION_ERROR: "OpenAI API key is invalid or lacks required permissions.",
    FailureCategory.INVALID_REQUEST: "OpenAI API returned a bad request error.",
    FailureCategory.CONNECT_TIMEOUT: "Could not connect to the OpenAI service within the allowed time.",
    FailureCategory.READ_TIMEOUT: "OpenAI service did not respond within the allowed time after retry.",
    FailureCategory.POOL_TIMEOUT: "OpenAI service did not respond within the allowed time after retry.",
    FailureCategory.NETWORK_ERROR: "Could not reach the OpenAI service due to a network issue.",
    FailureCategory.RATE_LIMITED: "OpenAI API rate limit or quota was reached.",
    FailureCategory.SERVER_ERROR: "OpenAI service is temporarily unavailable.",
    FailureCategory.UPSTREAM_UNAVAILABLE: "OpenAI service is temporarily unavailable.",
    FailureCategory.MALFORMED_RESPONSE: "AI insights response was not valid JSON.",
    FailureCategory.VALIDATION_ERROR: "AI insights response did not match the expected format.",
    FailureCategory.DEADLINE_EXCEEDED: "AI analysis could not complete within the overall time budget.",
    FailureCategory.UNKNOWN_ERROR: "AI insights could not be generated at this time.",
}

PAGESPEED_USER_MESSAGES = {
    FailureCategory.CONFIGURATION_ERROR: "Google PageSpeed API key is not configured.",
    FailureCategory.AUTHENTICATION_ERROR: "Google PageSpeed API key is invalid or lacks required permissions.",
    FailureCategory.INVALID_REQUEST: "Google PageSpeed API bad request: invalid URL or parameters.",
    FailureCategory.CONNECT_TIMEOUT: "Could not connect to the Google PageSpeed service within the allowed time.",
    FailureCategory.READ_TIMEOUT: "Google PageSpeed did not return performance data within the allowed time after retry.",
    FailureCategory.POOL_TIMEOUT: "Google PageSpeed did not return performance data within the allowed time after retry.",
    FailureCategory.NETWORK_ERROR: "Could not reach the Google PageSpeed service due to a network issue.",
    FailureCategory.RATE_LIMITED: "Google PageSpeed API quota or rate limit was reached.",
    FailureCategory.SERVER_ERROR: "Google PageSpeed service encountered an internal error while analyzing this website.",
    FailureCategory.UPSTREAM_UNAVAILABLE: "Google PageSpeed service could not complete analysis for this website.",
    FailureCategory.MALFORMED_RESPONSE: "Google PageSpeed returned an unexpected response format.",
    FailureCategory.VALIDATION_ERROR: "Google PageSpeed returned an unexpected response format.",
    FailureCategory.DEADLINE_EXCEEDED: "Google PageSpeed analysis could not complete within the overall time budget.",
    FailureCategory.UNKNOWN_ERROR: "Google PageSpeed is temporarily unavailable.",
}

PLACES_USER_MESSAGES = {
    FailureCategory.CONFIGURATION_ERROR: "Google Places API key is not configured.",
    FailureCategory.AUTHENTICATION_ERROR: "Google Places API key is invalid or lacks required permissions.",
    FailureCategory.INVALID_REQUEST: "Google Places API returned a bad request error.",
    FailureCategory.CONNECT_TIMEOUT: "Could not connect to the Google Places service within the allowed time.",
    FailureCategory.READ_TIMEOUT: "Google Places did not return competitor data within the allowed time.",
    FailureCategory.POOL_TIMEOUT: "Google Places did not return competitor data within the allowed time.",
    FailureCategory.NETWORK_ERROR: "Could not reach the Google Places service due to a network issue.",
    FailureCategory.RATE_LIMITED: "Google Places API quota or rate limit was reached.",
    FailureCategory.SERVER_ERROR: "Google Places service encountered a temporary error.",
    FailureCategory.UPSTREAM_UNAVAILABLE: "Google Places service could not retrieve competitor data at this time.",
    FailureCategory.MALFORMED_RESPONSE: "Google Places returned an unexpected response format.",
    FailureCategory.VALIDATION_ERROR: "Google Places response did not match the expected format.",
    FailureCategory.DEADLINE_EXCEEDED: "Google Places competitor discovery exceeded the time budget.",
    FailureCategory.UNKNOWN_ERROR: "Local competitor data could not be retrieved at this time.",
}


def get_user_message(service: str, category: str) -> str:
    """Returns the safe user-facing message for a given service and failure category."""
    if service == "openai":
        return OPENAI_USER_MESSAGES.get(category, OPENAI_USER_MESSAGES[FailureCategory.UNKNOWN_ERROR])
    elif service == "pagespeed":
        return PAGESPEED_USER_MESSAGES.get(category, PAGESPEED_USER_MESSAGES[FailureCategory.UNKNOWN_ERROR])
    elif service == "places":
        return PLACES_USER_MESSAGES.get(category, PLACES_USER_MESSAGES[FailureCategory.UNKNOWN_ERROR])
    return "Service temporarily unavailable."
