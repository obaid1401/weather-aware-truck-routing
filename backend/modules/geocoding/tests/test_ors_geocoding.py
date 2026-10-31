from collections.abc import Callable
from typing import Any

import httpx
import pytest
from django.core.exceptions import ImproperlyConfigured
from django.test.utils import override_settings

from modules.geocoding.services.ors_geocoding import OrsGeocodingService
from shared.http import get_http_client
from shared.types import (
    GeocodingAmbiguousError,
    GeocodingNotFoundError,
    Location,
    ProviderError,
    ProviderRateLimitError,
    ProviderTimeoutError,
    ProviderUnavailableError,
)

API_KEY = "test-ors-key"


def feature(label: str, latitude: float, longitude: float, confidence: float) -> dict[str, Any]:
    return {
        "type": "Feature",
        "geometry": {"type": "Point", "coordinates": [longitude, latitude]},
        "properties": {"label": label, "confidence": confidence},
    }


def service(handler: Callable[[httpx.Request], httpx.Response]) -> OrsGeocodingService:
    client = httpx.Client(transport=httpx.MockTransport(handler))
    return OrsGeocodingService(client, api_key=API_KEY)


def respond_with(*features: dict[str, Any]) -> Callable[[httpx.Request], httpx.Response]:
    return lambda request: httpx.Response(200, json={"features": list(features)})


# Shapes observed from the live ORS API.
DENVER = [
    feature("Denver, CO, USA", 39.741, -104.986, 0.6),
    feature("Denver County, CO, USA", 39.741, -104.987, 1),
]
SPRINGFIELD_IL = [
    feature("Springfield Township, IL, USA", 39.861, -89.696, 1),
    feature("Springfield, IL, USA", 39.861, -89.696, 1),
    feature("Springfield, IL, USA", 39.797, -89.646, 1),
]
SPRINGFIELD = [
    feature("Springfield, MO, USA", 37.197, -93.281, 1),
    feature("Springfield, MA, USA", 42.118, -72.540, 1),
    feature("Springfield, OH, USA", 39.930, -83.795, 1),
    feature("Springfield, OR, USA", 44.054, -122.983, 1),
    feature("Springfield, VA, USA", 38.777, -77.186, 1),
    feature("Springfield, TN, USA", 36.491, -86.875, 1),
]


def test_sends_query_with_key_in_header_not_url() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json={"features": DENVER})

    service(handler).geocode("Denver, CO", "origin")

    (request,) = requests
    assert request.method == "GET"
    assert request.url.path == "/geocode/search"
    assert request.url.params["text"] == "Denver, CO"
    assert request.headers["Authorization"] == API_KEY
    assert API_KEY not in str(request.url)


def test_lower_confidence_result_in_same_place_is_not_selected() -> None:
    # The provider ranks the 0.6 match first, but only the 1.0 match is plausible.
    location = service(respond_with(*DENVER)).geocode("Denver, CO", "origin")

    assert location == Location("Denver County, CO, USA", 39.741, -104.987)


def test_nearby_low_confidence_result_never_replaces_the_confident_match() -> None:
    # Review scenario: a low-confidence street ranked first, ~9 miles from the exact match.
    location = service(
        respond_with(
            feature("Main St, Littleton, CO, USA", 39.613, -105.017, 0.4),
            feature("1600 Pennsylvania St, Denver, CO, USA", 39.741, -104.981, 1),
        )
    ).geocode("1600 Pennsylvania St, Denver", "origin")

    assert location.label == "1600 Pennsylvania St, Denver, CO, USA"


def test_confidence_exactly_at_the_margin_is_plausible() -> None:
    # 0.8 - 0.1 is 0.7000000000000001 in floating point; 0.7 must still count.
    with pytest.raises(GeocodingAmbiguousError):
        service(
            respond_with(
                feature("Portland, OR, USA", 45.533, -122.650, 0.8),
                feature("Portland, ME, USA", 43.661, -70.255, 0.7),
            )
        ).geocode("Portland", "origin")


def test_confidence_just_outside_the_margin_is_not_plausible() -> None:
    location = service(
        respond_with(
            feature("Portland, OR, USA", 45.533, -122.650, 0.8),
            feature("Portland, ME, USA", 43.661, -70.255, 0.69),
        )
    ).geocode("Portland", "origin")

    assert location.label == "Portland, OR, USA"


def test_distinct_places_25_miles_apart_or_less_are_the_same_place() -> None:
    # Denver to Boulder is ~24 miles; Denver to Castle Rock is ~26 miles.
    location = service(
        respond_with(
            feature("Denver, CO, USA", 39.741, -104.986, 1),
            feature("Boulder, CO, USA", 40.016, -105.260, 1),
        )
    ).geocode("Denver", "origin")
    assert location.label == "Denver, CO, USA"

    with pytest.raises(GeocodingAmbiguousError):
        service(
            respond_with(
                feature("Denver, CO, USA", 39.741, -104.986, 1),
                feature("Castle Rock, CO, USA", 39.372, -104.856, 1),
            )
        ).geocode("Denver", "origin")


def test_near_duplicate_results_are_not_ambiguous() -> None:
    location = service(respond_with(*SPRINGFIELD_IL)).geocode("Springfield, IL", "origin")

    assert location.label == "Springfield Township, IL, USA"


def test_distant_results_with_similar_confidence_are_ambiguous() -> None:
    with pytest.raises(GeocodingAmbiguousError) as error:
        service(respond_with(*SPRINGFIELD)).geocode("Springfield", "destination")

    details = error.value.details
    assert details["field"] == "destination"
    assert len(details["candidates"]) == 5
    assert details["candidates"][0] == {
        "label": "Springfield, MO, USA",
        "latitude": 37.197,
        "longitude": -93.281,
    }


def test_distant_low_confidence_results_are_ignored() -> None:
    location = service(
        respond_with(
            feature("Portland, OR, USA", 45.533, -122.650, 1),
            feature("Portland, Jamaica", 18.120, -76.536, 0.3),
        )
    ).geocode("Portland, OR", "origin")

    assert location.label == "Portland, OR, USA"


def test_no_results_raise_not_found() -> None:
    with pytest.raises(GeocodingNotFoundError) as error:
        service(respond_with()).geocode("zzqxqv nowhere", "origin")

    assert error.value.details == {"field": "origin"}


@pytest.mark.parametrize(
    "body",
    [
        {},
        {"features": "nope"},
        {"features": [{"geometry": {"coordinates": [-104.9, 39.7]}, "properties": {}}]},
        {"features": [feature("Bad", 95.0, -104.9, 1)]},
        {"features": [feature("", 39.7, -104.9, 1)]},
        {"features": [feature("Denver", 39.7, -104.9, "high")]},  # type: ignore[arg-type]
    ],
)
def test_malformed_responses_raise_provider_error(body: Any) -> None:
    with pytest.raises(ProviderError):
        service(lambda request: httpx.Response(200, json=body)).geocode("Denver", "origin")


def test_non_json_response_raises_provider_error() -> None:
    with pytest.raises(ProviderError):
        service(lambda request: httpx.Response(200, text="<html>")).geocode("Denver", "origin")


@pytest.mark.parametrize(
    ("status", "error_type"),
    [
        (429, ProviderRateLimitError),
        (403, ProviderError),
        (401, ProviderError),
        (400, ProviderError),
        (500, ProviderError),
        (502, ProviderUnavailableError),
        (503, ProviderUnavailableError),
        (504, ProviderUnavailableError),
    ],
)
def test_http_errors_map_to_provider_errors(status: int, error_type: type[Exception]) -> None:
    with pytest.raises(error_type) as error:
        service(lambda request: httpx.Response(status, json={"error": "x"})).geocode("D", "origin")

    assert error.value.details["provider"] == "OpenRouteService"  # type: ignore[attr-defined]


def test_rate_limit_includes_retry_after() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(429, headers={"Retry-After": "30"})

    with pytest.raises(ProviderRateLimitError) as error:
        service(handler).geocode("Denver", "origin")

    assert error.value.details["retry_after_seconds"] == 30


def test_timeout_raises_provider_timeout() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("timed out", request=request)

    with pytest.raises(ProviderTimeoutError):
        service(handler).geocode("Denver", "origin")


def test_connection_failure_raises_provider_unavailable() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("refused", request=request)

    with pytest.raises(ProviderUnavailableError):
        service(handler).geocode("Denver", "origin")


@override_settings(ORS_API_KEY="from-settings")
def test_api_key_is_read_from_settings() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json={"features": DENVER})

    OrsGeocodingService(httpx.Client(transport=httpx.MockTransport(handler))).geocode("D", "o")

    assert requests[0].headers["Authorization"] == "from-settings"


def test_uses_the_shared_configured_client_by_default() -> None:
    assert OrsGeocodingService(api_key=API_KEY)._client is get_http_client()


@override_settings(ORS_API_KEY="")
def test_missing_api_key_is_a_configuration_error() -> None:
    with pytest.raises(ImproperlyConfigured):
        OrsGeocodingService(httpx.Client())
