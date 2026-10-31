"""HTTP helpers shared by the provider integrations.

They convert transport failures, HTTP error statuses, and unreadable responses into the
shared provider errors, so each integration only handles its provider-specific cases.
"""

import functools
import logging
from typing import Any

import httpx

from shared.types import (
    ProviderError,
    ProviderRateLimitError,
    ProviderTimeoutError,
    ProviderUnavailableError,
)

logger = logging.getLogger(__name__)

TIMEOUT = httpx.Timeout(15.0, connect=5.0)
# Public providers (notably the FOSSGIS Valhalla server) ask clients to identify themselves.
USER_AGENT = (
    "weather-aware-truck-routing/1.0 (+https://github.com/obaid1401/weather-aware-truck-routing)"
)


@functools.cache
def get_http_client() -> httpx.Client:
    """Returns the process-wide client used by provider integrations by default.

    One client keeps connection pools warm across requests and applies the timeout and
    User-Agent everywhere. `httpx.Client` is safe to share between threads.
    """
    return httpx.Client(timeout=TIMEOUT, headers={"User-Agent": USER_AGENT})


def send_request(
    client: httpx.Client, provider: str, method: str, url: str, **kwargs: Any
) -> httpx.Response:
    details = {"provider": provider}
    try:
        return client.request(method, url, **kwargs)
    except httpx.TimeoutException as exc:
        raise ProviderTimeoutError(f"{provider} did not respond in time.", details=details) from exc
    except httpx.TransportError as exc:
        raise ProviderUnavailableError(
            f"{provider} could not be reached.", details=details
        ) from exc
    except httpx.RequestError as exc:
        # For example, a redirect loop or an undecodable response body.
        logger.warning("%s request failed: %r", provider, exc)
        raise ProviderError(f"{provider} returned an invalid response.", details=details) from exc


def raise_for_status(response: httpx.Response, provider: str) -> None:
    status = response.status_code
    if status < 400:
        return

    logger.warning("%s returned HTTP %s: %s", provider, status, response.text[:500])
    details: dict[str, Any] = {"provider": provider}

    if status == 429:
        retry_after = response.headers.get("Retry-After", "")
        if retry_after.isdigit():
            details["retry_after_seconds"] = int(retry_after)
        raise ProviderRateLimitError(
            f"{provider} request limit was reached. Try again later.", details=details
        )
    if status in (502, 503, 504):
        raise ProviderUnavailableError(
            f"{provider} is temporarily unavailable. Try again later.", details=details
        )
    if status in (401, 403):
        raise ProviderError(f"{provider} rejected the request credentials.", details=details)
    raise ProviderError(f"{provider} returned an error (HTTP {status}).", details=details)


def parse_json(response: httpx.Response, provider: str) -> Any:
    try:
        return response.json()
    except ValueError as exc:
        raise invalid_response_error(provider, "response body is not JSON") from exc


def invalid_response_error(provider: str, reason: str) -> ProviderError:
    logger.warning("%s returned an invalid response: %s", provider, reason)
    return ProviderError(
        f"{provider} returned an invalid response.", details={"provider": provider}
    )
