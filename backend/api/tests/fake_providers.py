"""A fake HTTP backend that answers like ORS geocoding, Valhalla, and Open-Meteo, so the
API can be tested end to end through the real services without network access."""

import json
from collections.abc import Callable, Sequence
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx

DENVER = (39.741, -104.986)
SALT_LAKE_CITY = (40.773, -111.934)
GEOMETRY = [DENVER, (40.2, -108.5), SALT_LAKE_CITY]


def encode_polyline6(points: Sequence[tuple[float, float]]) -> str:
    output, previous = [], (0, 0)
    for latitude, longitude in points:
        current = (round(latitude * 1e6), round(longitude * 1e6))
        for value in (current[0] - previous[0], current[1] - previous[1]):
            value = ~(value << 1) if value < 0 else value << 1
            while value >= 0x20:
                output.append(chr((0x20 | (value & 0x1F)) + 63))
                value >>= 5
            output.append(chr(value + 63))
        previous = current
    return "".join(output)


def feature(label: str, latitude: float, longitude: float) -> dict[str, Any]:
    return {
        "geometry": {"coordinates": [longitude, latitude]},
        "properties": {"label": label, "confidence": 1},
    }


GEOCODE_RESULTS: dict[str, list[dict[str, Any]]] = {
    "Denver, CO": [feature("Denver, CO, USA", *DENVER)],
    "Salt Lake City, UT": [feature("Salt Lake City, UT, USA", *SALT_LAKE_CITY)],
    "Springfield": [
        feature("Springfield, MO, USA", 37.197, -93.281),
        feature("Springfield, MA, USA", 42.118, -72.540),
    ],
    "Nowhere at all": [],
}


def valhalla_trip(length: float, seconds: float) -> dict[str, Any]:
    return {
        "units": "miles",
        "summary": {"length": length, "time": seconds},
        "legs": [
            {
                "shape": encode_polyline6(GEOMETRY),
                "maneuvers": [
                    {
                        "begin_shape_index": 0,
                        "end_shape_index": 1,
                        "length": 250.0,
                        "time": 13000.0,
                    },
                    {
                        "begin_shape_index": 1,
                        "end_shape_index": 2,
                        "length": length - 250.0,
                        "time": seconds - 13000.0,
                    },
                    {"begin_shape_index": 2, "end_shape_index": 2, "length": 0.0, "time": 0.0},
                ],
            }
        ],
    }


VALHALLA_TWO_ROUTES = {
    "trip": valhalla_trip(536.2, 28580.0),
    "alternates": [{"trip": valhalla_trip(527.2, 29544.0)}],
}


def open_meteo(request: httpx.Request, values: Callable[[int], tuple[Any, Any, Any]]) -> Any:
    """Every requested location gets hourly data from start_hour to end_hour.
    `values(hour_index)` gives (wind km/h, precipitation mm, snowfall cm)."""
    params = request.url.params
    count = len(params["latitude"].split(","))
    start = datetime.strptime(params["start_hour"], "%Y-%m-%dT%H:%M").replace(tzinfo=UTC)
    end = datetime.strptime(params["end_hour"], "%Y-%m-%dT%H:%M").replace(tzinfo=UTC)
    hours = int((end - start) / timedelta(hours=1)) + 1
    series = [values(i) for i in range(hours)]
    location = {
        "hourly_units": {
            "time": "unixtime",
            "wind_speed_10m": "km/h",
            "precipitation": "mm",
            "snowfall": "cm",
        },
        "hourly": {
            "time": [int((start + timedelta(hours=i)).timestamp()) for i in range(hours)],
            "wind_speed_10m": [s[0] for s in series],
            "precipitation": [s[1] for s in series],
            "snowfall": [s[2] for s in series],
        },
    }
    if count == 1:
        return location
    return [location] + [{**location, "location_id": i} for i in range(1, count)]


class FakeProviders:
    """An httpx transport handler. Override any provider's response per test."""

    def __init__(self) -> None:
        self.requests: list[httpx.Request] = []
        self.valhalla: Callable[[httpx.Request], httpx.Response] = lambda r: httpx.Response(
            200, json=VALHALLA_TWO_ROUTES
        )
        self.weather_values: Callable[[int], tuple[Any, Any, Any]] = lambda i: (16.09344, 0.0, 0.0)
        self.weather: Callable[[httpx.Request], httpx.Response] = lambda r: httpx.Response(
            200, json=open_meteo(r, self.weather_values)
        )
        self.geocode: Callable[[httpx.Request], httpx.Response] = lambda r: httpx.Response(
            200, json={"features": GEOCODE_RESULTS.get(r.url.params["text"], [])}
        )

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        host = request.url.host
        if host == "api.openrouteservice.org":
            return self.geocode(request)
        if host == "valhalla.test":
            return self.valhalla(request)
        if host == "api.open-meteo.com":
            return self.weather(request)
        raise AssertionError(f"unexpected request to {request.url}")

    def hosts(self) -> list[str]:
        return [request.url.host for request in self.requests]

    def valhalla_body(self) -> dict[str, Any]:
        (request,) = [r for r in self.requests if r.url.host == "valhalla.test"]
        return json.loads(request.content)
