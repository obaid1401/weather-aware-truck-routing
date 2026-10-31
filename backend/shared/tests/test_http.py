import httpx
import pytest

from shared.http import TIMEOUT, USER_AGENT, get_http_client, send_request
from shared.types import ProviderError, ProviderTimeoutError, ProviderUnavailableError


def client_raising(exc_type: type[httpx.RequestError], message: str = "boom") -> httpx.Client:
    def handler(request: httpx.Request) -> httpx.Response:
        raise exc_type(message, request=request)

    return httpx.Client(transport=httpx.MockTransport(handler))


def test_shared_client_is_reused_and_configured() -> None:
    client = get_http_client()

    assert get_http_client() is client
    assert client.timeout == TIMEOUT
    assert client.timeout.connect == 5.0
    assert client.timeout.read == 15.0
    assert client.headers["User-Agent"] == USER_AGENT


def test_shared_client_sends_user_agent() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200)

    client = httpx.Client(transport=httpx.MockTransport(handler), headers=get_http_client().headers)
    send_request(client, "Provider", "GET", "https://provider.test/")

    assert seen[0].headers["User-Agent"].startswith("weather-aware-truck-routing/")


@pytest.mark.parametrize(
    ("exc_type", "error_type"),
    [
        (httpx.ReadTimeout, ProviderTimeoutError),
        (httpx.ConnectTimeout, ProviderTimeoutError),
        (httpx.ConnectError, ProviderUnavailableError),
        (httpx.RemoteProtocolError, ProviderUnavailableError),
        (httpx.TooManyRedirects, ProviderError),
        (httpx.DecodingError, ProviderError),
    ],
)
def test_request_failures_become_provider_errors(
    exc_type: type[httpx.RequestError], error_type: type[Exception]
) -> None:
    with pytest.raises(error_type) as error:
        send_request(client_raising(exc_type), "Provider", "GET", "https://provider.test/")

    assert error.value.details == {"provider": "Provider"}  # type: ignore[attr-defined]


def test_redirect_loop_is_not_reported_as_unavailable() -> None:
    with pytest.raises(ProviderError) as error:
        send_request(client_raising(httpx.TooManyRedirects), "Provider", "GET", "https://x.test/")

    assert type(error.value) is ProviderError
    assert error.value.message == "Provider returned an invalid response."
