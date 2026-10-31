import json
from collections.abc import Callable, Sequence
from typing import Any

import httpx
import pytest
from django.core.exceptions import ImproperlyConfigured
from django.test.utils import override_settings

from modules.routing.services.valhalla_routing import ValhallaRoutingService, decode_polyline6
from shared.http import get_http_client
from shared.types import (
    Coordinate,
    Location,
    NoRouteFoundError,
    ProviderError,
    ProviderRateLimitError,
    ProviderTimeoutError,
    ProviderUnavailableError,
    RouteStep,
)

BASE_URL = "https://valhalla.test"
DENVER = Location("Denver, CO, USA", 39.7392, -104.9903)
SALT_LAKE_CITY = Location("Salt Lake City, UT, USA", 40.7608, -111.8910)
SHAPE = [
    Coordinate(39.741001, -104.986118),
    Coordinate(40.1, -107.5),
    Coordinate(40.773, -111.934231),
]


def encode_polyline6(coordinates: Sequence[Coordinate]) -> str:
    """Reference encoder used to build test fixtures."""
    output, previous = [], (0, 0)
    for coordinate in coordinates:
        current = (round(coordinate.latitude * 1e6), round(coordinate.longitude * 1e6))
        for value in (current[0] - previous[0], current[1] - previous[1]):
            value = ~(value << 1) if value < 0 else value << 1
            while value >= 0x20:
                output.append(chr((0x20 | (value & 0x1F)) + 63))
                value >>= 5
            output.append(chr(value + 63))
        previous = current
    return "".join(output)


def trip(
    length: float = 536.2207,
    time: float = 28580.761,
    shape: Sequence[Coordinate] = SHAPE,
    maneuvers: list[dict[str, Any]] | None = None,
    units: str = "miles",
) -> dict[str, Any]:
    if maneuvers is None:
        maneuvers = [
            {"begin_shape_index": 0, "end_shape_index": 1, "length": 200.5, "time": 10000.0},
            {"begin_shape_index": 1, "end_shape_index": 2, "length": 335.7207, "time": 18580.761},
            {"begin_shape_index": 2, "end_shape_index": 2, "length": 0.0, "time": 0.0},
        ]
    return {
        "units": units,
        "summary": {"length": length, "time": time},
        "legs": [{"shape": encode_polyline6(shape), "maneuvers": maneuvers}],
    }


def response(*trips: dict[str, Any]) -> dict[str, Any]:
    body: dict[str, Any] = {"trip": trips[0]}
    if len(trips) > 1:
        body["alternates"] = [{"trip": t} for t in trips[1:]]
    return body


class Recorder:
    def __init__(self, respond: httpx.Response) -> None:
        self.respond = respond
        self.requests: list[httpx.Request] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        return self.respond


def service(handler: Callable[[httpx.Request], httpx.Response]) -> ValhallaRoutingService:
    client = httpx.Client(transport=httpx.MockTransport(handler))
    return ValhallaRoutingService(client, base_url=BASE_URL)


def valhalla_error(code: int, message: str) -> httpx.Response:
    return httpx.Response(
        400,
        json={"error_code": code, "error": message, "status_code": 400, "status": "Bad Request"},
    )


# Polyline decoding


def test_decodes_known_polyline() -> None:
    # Google's reference polyline; read with precision 6 the values are 10 times smaller.
    assert decode_polyline6("_p~iF~ps|U_ulLnnqC_mqNvxq`@") == (
        Coordinate(3.85, -12.02),
        Coordinate(4.07, -12.095),
        Coordinate(4.3252, -12.6453),
    )


def test_decoding_round_trips_six_decimal_places() -> None:
    assert decode_polyline6(encode_polyline6(SHAPE)) == tuple(SHAPE)
    assert decode_polyline6("") == ()


@pytest.mark.parametrize("encoded", [None, 42, "_p~iF~ps|", "_p~iF", "a b", "\x7f\x7f"])
def test_invalid_polylines_are_rejected(encoded: object) -> None:
    with pytest.raises(ValueError):
        decode_polyline6(encoded)


def test_out_of_range_polyline_positions_are_rejected() -> None:
    with pytest.raises(ValueError):
        decode_polyline6(encode_polyline6([Coordinate(95.0, 0.0)]))


# Requests and normalization


def test_requests_truck_costing_with_two_alternates() -> None:
    recorder = Recorder(httpx.Response(200, json=response(trip(), trip(), trip())))

    service(recorder).get_routes(DENVER, SALT_LAKE_CITY)

    (request,) = recorder.requests
    assert request.method == "POST"
    assert str(request.url) == f"{BASE_URL}/route"
    assert json.loads(request.content) == {
        "locations": [{"lat": 39.7392, "lon": -104.9903}, {"lat": 40.7608, "lon": -111.891}],
        "costing": "truck",
        "alternates": 2,
        "units": "miles",
    }


def test_primary_and_alternates_are_returned_in_provider_order() -> None:
    body = response(trip(length=536.2), trip(length=527.2), trip(length=492.9))

    result = service(Recorder(httpx.Response(200, json=body))).get_routes(DENVER, SALT_LAKE_CITY)

    assert [r.id for r in result.routes] == ["route-1", "route-2", "route-3"]
    assert [r.label for r in result.routes] == ["Route A", "Route B", "Route C"]
    assert [r.distance_miles for r in result.routes] == [536.2, 527.2, 492.9]
    assert result.warnings == ()


def test_route_is_normalized_into_shared_types() -> None:
    body = response(trip())

    route = service(Recorder(httpx.Response(200, json=body))).get_routes(DENVER, SALT_LAKE_CITY)
    route = route.routes[0]

    assert route.geometry == tuple(SHAPE)
    assert route.distance_miles == 536.2207
    assert route.duration_seconds == 28580.761
    assert route.steps == (
        RouteStep(0, 1, 200.5, 10000.0),
        RouteStep(1, 2, 335.7207, 18580.761),
        RouteStep(2, 2, 0.0, 0.0),
    )


@pytest.mark.parametrize("count", [1, 2])
def test_fewer_routes_than_requested_are_reported_not_fabricated(count: int) -> None:
    body = response(*[trip()] * count)

    result = service(Recorder(httpx.Response(200, json=body))).get_routes(DENVER, SALT_LAKE_CITY)

    assert len(result.routes) == count
    assert result.warnings == (
        f"The routing provider returned {count} of up to 3 requested routes. "
        "Only genuine provider routes are shown.",
    )


def test_extra_alternates_beyond_three_are_ignored() -> None:
    body = response(*[trip()] * 4)

    result = service(Recorder(httpx.Response(200, json=body))).get_routes(DENVER, SALT_LAKE_CITY)

    assert len(result.routes) == 3


def test_same_origin_and_destination_is_rejected_without_a_request() -> None:
    recorder = Recorder(httpx.Response(200, json=response(trip())))

    with pytest.raises(NoRouteFoundError) as error:
        service(recorder).get_routes(DENVER, DENVER)

    assert error.value.message == "The origin and destination are the same location."
    assert recorder.requests == []


# Provider errors (codes and messages observed on the public FOSSGIS server)


@pytest.mark.parametrize(
    ("code", "provider_message", "message"),
    [
        (
            170,
            "Locations are in unconnected regions. Go check/edit the map at osm.org",
            "The origin and destination are not connected by roads.",
        ),
        (
            171,
            "No suitable edges near location",
            "No road was found near the origin or destination.",
        ),
        (
            442,
            "No path could be found for input",
            "No truck route could be found between the origin and destination.",
        ),
    ],
)
def test_no_route_errors(code: int, provider_message: str, message: str) -> None:
    with pytest.raises(NoRouteFoundError) as error:
        service(Recorder(valhalla_error(code, provider_message))).get_routes(DENVER, SALT_LAKE_CITY)

    assert error.value.code == "ROUTE_NOT_FOUND"
    assert error.value.message == message
    assert error.value.details == {"provider_code": code}


def test_distance_limit_error() -> None:
    error_response = valhalla_error(
        154, "Path distance exceeds the max distance limit: 1500000 meters"
    )

    with pytest.raises(NoRouteFoundError) as error:
        service(Recorder(error_response)).get_routes(DENVER, SALT_LAKE_CITY)

    assert error.value.code == "ROUTE_DISTANCE_LIMIT"
    assert error.value.details == {"provider_code": 154}


@pytest.mark.parametrize(
    "error_response",
    [
        valhalla_error(100, "Failed to parse json request"),
        httpx.Response(400, text="not json"),
        # Non-integer codes, including unhashable ones, must not crash the lookup.
        httpx.Response(400, json={"error_code": [170]}),
        httpx.Response(400, json={"error_code": {}}),
        httpx.Response(400, json={"error_code": "170"}),
        httpx.Response(400, json={"error_code": True}),
        httpx.Response(400, json=["not", "an", "object"]),
    ],
)
def test_other_bad_requests_are_provider_errors(error_response: httpx.Response) -> None:
    with pytest.raises(ProviderError):
        service(Recorder(error_response)).get_routes(DENVER, SALT_LAKE_CITY)


@pytest.mark.parametrize(
    ("status", "error_type"),
    [(429, ProviderRateLimitError), (500, ProviderError), (503, ProviderUnavailableError)],
)
def test_http_errors_map_to_provider_errors(status: int, error_type: type[Exception]) -> None:
    with pytest.raises(error_type):
        service(Recorder(httpx.Response(status))).get_routes(DENVER, SALT_LAKE_CITY)


def test_timeout_is_reported() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("timed out", request=request)

    with pytest.raises(ProviderTimeoutError):
        service(handler).get_routes(DENVER, SALT_LAKE_CITY)


def maneuver(start: int, end: int, length: float = 1.0, time: float = 1.0) -> dict[str, Any]:
    return {"begin_shape_index": start, "end_shape_index": end, "length": length, "time": time}


@pytest.mark.parametrize(
    "body",
    [
        {},
        {"trip": "nope"},
        {"trip": {**trip(), "legs": []}},
        {"trip": {**trip(), "legs": [trip()["legs"][0]] * 2}},
        {"trip": {**trip(), "legs": [{"shape": 7, "maneuvers": []}]}},
        response(trip(units="kilometers")),
        response(trip(shape=SHAPE[:1])),
        response(trip(length=0)),
        response(trip(time=-1)),
        response(trip(maneuvers=[maneuver(0, 9)])),
        response(trip(maneuvers=[maneuver(2, 1)])),
        response(trip(maneuvers=[maneuver(0, 1, length=-1)])),
        response(trip(maneuvers=[{"begin_shape_index": 0}])),
        {"trip": trip(), "alternates": [{"no_trip": True}]},
    ],
)
def test_malformed_responses_raise_provider_error(body: Any) -> None:
    with pytest.raises(ProviderError):
        service(Recorder(httpx.Response(200, json=body))).get_routes(DENVER, SALT_LAKE_CITY)


# Configuration


@override_settings(VALHALLA_BASE_URL="https://configured.example/")
def test_base_url_is_read_from_settings() -> None:
    recorder = Recorder(httpx.Response(200, json=response(trip())))

    ValhallaRoutingService(httpx.Client(transport=httpx.MockTransport(recorder))).get_routes(
        DENVER, SALT_LAKE_CITY
    )

    assert str(recorder.requests[0].url) == "https://configured.example/route"


def test_uses_the_shared_configured_client_by_default() -> None:
    assert ValhallaRoutingService(base_url=BASE_URL)._client is get_http_client()


@override_settings(VALHALLA_BASE_URL="")
def test_missing_base_url_is_a_configuration_error() -> None:
    with pytest.raises(ImproperlyConfigured):
        ValhallaRoutingService(httpx.Client())
