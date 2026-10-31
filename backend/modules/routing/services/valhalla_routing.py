"""Valhalla truck routing (`/route` with `truck` costing)."""

import string
from dataclasses import dataclass
from typing import Any

import httpx
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

from shared.geo import distance_miles
from shared.http import (
    get_http_client,
    invalid_response_error,
    parse_json,
    raise_for_status,
    send_request,
)
from shared.types import Coordinate, Location, NoRouteFoundError, Route, RouteStep
from shared.validation import finite_number

PROVIDER = "Valhalla"
MAX_ROUTES = 3

# Origin and destination closer than this are treated as the same point.
SAME_POINT_MILES = 0.1

# Valhalla encodes route shapes as polylines with six decimal places.
POLYLINE_PRECISION = 1e6

# Valhalla no-route errors (HTTP 400). 170 and 171 were observed on the public FOSSGIS
# server; 442 ("No path could be found for input") is Valhalla's documented general
# no-route error, for example when truck restrictions block every path.
NO_ROUTE_MESSAGES = {
    170: "The origin and destination are not connected by roads.",
    171: "No road was found near the origin or destination.",
    442: "No truck route could be found between the origin and destination.",
}
DISTANCE_LIMIT_CODE = 154
DISTANCE_LIMIT_MESSAGE = "The trip exceeds the routing server's maximum truck route distance."


@dataclass(frozen=True)
class RoutingResult:
    routes: tuple[Route, ...]
    warnings: tuple[str, ...]


class ValhallaRoutingService:
    def __init__(self, client: httpx.Client | None = None, base_url: str | None = None) -> None:
        self._client = client or get_http_client()
        base_url = base_url if base_url is not None else settings.VALHALLA_BASE_URL
        if not base_url:
            raise ImproperlyConfigured("VALHALLA_BASE_URL is not set.")
        self._route_url = f"{base_url.rstrip('/')}/route"

    def get_routes(self, origin: Location, destination: Location) -> RoutingResult:
        """Returns up to three genuine provider routes, in provider order."""
        if distance_miles(origin.coordinate, destination.coordinate) < SAME_POINT_MILES:
            raise NoRouteFoundError("The origin and destination are the same location.")

        response = send_request(
            self._client,
            PROVIDER,
            "POST",
            self._route_url,
            json={
                "locations": [
                    {"lat": origin.latitude, "lon": origin.longitude},
                    {"lat": destination.latitude, "lon": destination.longitude},
                ],
                "costing": "truck",
                "alternates": MAX_ROUTES - 1,
                "units": "miles",
            },
        )
        _raise_for_no_route(response)
        raise_for_status(response, PROVIDER)
        routes = _parse_routes(parse_json(response, PROVIDER))

        warnings: tuple[str, ...] = ()
        if len(routes) < MAX_ROUTES:
            warnings = (
                f"The routing provider returned {len(routes)} of up to {MAX_ROUTES} requested "
                "routes. Only genuine provider routes are shown.",
            )
        return RoutingResult(routes, warnings)


def _raise_for_no_route(response: httpx.Response) -> None:
    if response.status_code != 400:
        return
    try:
        code = response.json()["error_code"]
    except (ValueError, KeyError, TypeError):
        return
    # Ignore non-integer codes (which may be unhashable); raise_for_status reports them.
    if not isinstance(code, int) or isinstance(code, bool):
        return
    if code in NO_ROUTE_MESSAGES:
        raise NoRouteFoundError(NO_ROUTE_MESSAGES[code], details={"provider_code": code})
    if code == DISTANCE_LIMIT_CODE:
        raise NoRouteFoundError(
            DISTANCE_LIMIT_MESSAGE,
            details={"provider_code": code},
            code="ROUTE_DISTANCE_LIMIT",
        )


def _parse_routes(data: Any) -> tuple[Route, ...]:
    try:
        trips = [data["trip"], *(alternate["trip"] for alternate in data.get("alternates", []))]
        return tuple(_parse_trip(trip, index) for index, trip in enumerate(trips[:MAX_ROUTES]))
    except (AttributeError, KeyError, TypeError, ValueError) as exc:
        raise invalid_response_error(PROVIDER, f"malformed route: {exc}") from exc


def _parse_trip(trip: Any, index: int) -> Route:
    if trip["units"] != "miles":
        raise ValueError(f"unexpected units {trip['units']!r}")
    legs = trip["legs"]
    if len(legs) != 1:
        raise ValueError(f"expected one leg, got {len(legs)}")

    geometry = decode_polyline6(legs[0]["shape"])
    if len(geometry) < 2:
        raise ValueError("route geometry has fewer than two points")

    distance = finite_number(trip["summary"]["length"])
    duration = finite_number(trip["summary"]["time"])
    if distance <= 0 or duration <= 0:
        raise ValueError("route distance and duration must be positive")

    return Route(
        id=f"route-{index + 1}",
        label=f"Route {string.ascii_uppercase[index]}",
        geometry=geometry,
        distance_miles=distance,
        duration_seconds=duration,
        steps=tuple(_parse_maneuver(m, len(geometry)) for m in legs[0]["maneuvers"]),
    )


def _parse_maneuver(maneuver: Any, point_count: int) -> RouteStep:
    start_index, end_index = maneuver["begin_shape_index"], maneuver["end_shape_index"]
    if not (
        isinstance(start_index, int)
        and isinstance(end_index, int)
        and 0 <= start_index <= end_index < point_count
    ):
        raise ValueError(f"maneuver shape indexes out of range: {start_index!r}, {end_index!r}")
    distance = finite_number(maneuver["length"])
    duration = finite_number(maneuver["time"])
    if distance < 0 or duration < 0:
        raise ValueError("maneuver length and time must not be negative")
    return RouteStep(start_index, end_index, distance, duration)


def decode_polyline6(encoded: object) -> tuple[Coordinate, ...]:
    """Decodes an encoded polyline (precision 6, latitude first) into coordinates."""
    if not isinstance(encoded, str):
        raise ValueError(f"expected an encoded polyline string, got {type(encoded).__name__}")

    values: list[int] = []
    result = shift = 0
    for char in encoded:
        chunk = ord(char) - 63
        if not 0 <= chunk < 64:
            raise ValueError(f"invalid polyline character {char!r}")
        result |= (chunk & 0x1F) << shift
        shift += 5
        if chunk < 0x20:
            values.append(~(result >> 1) if result & 1 else result >> 1)
            result = shift = 0
    if shift or len(values) % 2:
        raise ValueError("truncated polyline")

    coordinates = []
    latitude = longitude = 0
    for latitude_delta, longitude_delta in zip(values[::2], values[1::2], strict=True):
        latitude += latitude_delta
        longitude += longitude_delta
        coordinate = Coordinate(latitude / POLYLINE_PRECISION, longitude / POLYLINE_PRECISION)
        if not (-90 <= coordinate.latitude <= 90 and -180 <= coordinate.longitude <= 180):
            raise ValueError(f"polyline position out of range: {coordinate}")
        coordinates.append(coordinate)
    return tuple(coordinates)
