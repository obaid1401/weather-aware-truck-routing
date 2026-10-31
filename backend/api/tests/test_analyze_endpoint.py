"""`POST /api/v1/routes/analyze/` end to end: real view, serializers, use case, services,
and domain logic. Only HTTP is faked (see fake_providers.py)."""

import os
import re
from datetime import UTC, datetime, timedelta, timezone
from typing import Any

import httpx
import pytest
from django.test import Client
from django.test.utils import override_settings

from api.tests.fake_providers import FakeProviders

URL = "/api/v1/routes/analyze/"
ISO_UTC = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?Z$")
RISKS = {"LOW", "MODERATE", "HIGH", "SEVERE", "NO_TRAVEL", "UNKNOWN"}


@pytest.fixture
def providers(monkeypatch: pytest.MonkeyPatch) -> FakeProviders:
    fake = FakeProviders()
    client = httpx.Client(transport=httpx.MockTransport(fake))
    for module in (
        "modules.geocoding.services.ors_geocoding",
        "modules.routing.services.valhalla_routing",
        "modules.weather.services.open_meteo",
    ):
        monkeypatch.setattr(f"{module}.get_http_client", lambda: client)
    return fake


def departure() -> str:
    mountain = timezone(timedelta(hours=-7))
    start = datetime.now(mountain).replace(minute=0, second=0, microsecond=0) + timedelta(days=1)
    return start.isoformat()


def request_body(**changes: Any) -> dict[str, Any]:
    return {
        "origin": "Denver, CO",
        "destination": "Salt Lake City, UT",
        "departure_time": departure(),
        "load_weight_lbs": 36000,
        "checkpoint_interval_miles": 25,
        **changes,
    }


def post(client: Client, body: dict[str, Any]) -> Any:
    return client.post(URL, body, content_type="application/json")


VALHALLA = override_settings(VALHALLA_BASE_URL="https://valhalla.test")


# Success


@VALHALLA
def test_complete_analysis_response(client: Client, providers: FakeProviders) -> None:
    body = request_body()

    response = post(client, body)

    assert response.status_code == 200, response.content
    data = response.json()
    assert set(data) == {
        "trip",
        "origin",
        "destination",
        "forecast_window",
        "routes",
        "recommendation",
        "provider_warnings",
    }
    assert data["trip"]["origin"] == "Denver, CO"
    assert data["trip"]["load_weight_lbs"] == 36000
    assert data["trip"]["checkpoint_interval_miles"] == 25
    assert data["origin"] == {"label": "Denver, CO, USA", "latitude": 39.741, "longitude": -104.986}
    assert data["destination"]["label"] == "Salt Lake City, UT, USA"
    # One geocode per address, one routing call, one weather call for both routes.
    assert providers.hosts() == [
        "api.openrouteservice.org",
        "api.openrouteservice.org",
        "valhalla.test",
        "api.open-meteo.com",
    ]
    assert providers.valhalla_body()["costing"] == "truck"


@VALHALLA
def test_routes_carry_geometry_metrics_and_checkpoints(
    client: Client, providers: FakeProviders
) -> None:
    data = post(client, request_body()).json()

    assert [r["id"] for r in data["routes"]] == ["route-1", "route-2"]
    route = data["routes"][0]
    assert route["label"] == "Route A"
    assert route["distance_miles"] == 536.2
    assert route["duration_seconds"] == 28580.0
    assert route["geometry"][0] == [39.741, -104.986]
    assert route["geometry"][-1] == [40.773, -111.934]
    assert route["checkpoint_count"] == len(route["checkpoints"]) == 23
    assert set(route["metrics"]) == {
        "distance_miles",
        "duration_seconds",
        "low_miles",
        "moderate_miles",
        "high_miles",
        "severe_miles",
        "no_travel_miles",
        "unknown_miles",
        "average_risk_score",
        "weather_coverage_percent",
        "complete_weather_coverage_percent",
    }
    assert route["metrics"]["low_miles"] == pytest.approx(536.2)
    assert route["metrics"]["weather_coverage_percent"] == 100.0


@VALHALLA
def test_checkpoints_carry_weather_risks_and_hourly_series(
    client: Client, providers: FakeProviders
) -> None:
    data = post(client, request_body()).json()

    checkpoint = data["routes"][0]["checkpoints"][1]
    assert checkpoint["id"] == "route-1-cp-1"
    assert checkpoint["distance_from_origin_miles"] == 25.0
    assert checkpoint["wind_speed_mph"] == pytest.approx(10.0)  # 16.09344 km/h
    assert checkpoint["precipitation_inches_per_hour"] == 0.0
    assert checkpoint["data_status"] == "AVAILABLE"
    assert {checkpoint[k] for k in ("wind_risk", "rain_risk", "snow_risk", "final_risk")} == {"LOW"}
    assert checkpoint["warnings"] == []
    series = checkpoint["hourly_forecasts"]
    assert [entry["hour_offset"] for entry in series] == list(range(49))
    assert all(entry["final_risk"] in RISKS for entry in series)


@VALHALLA
def test_timestamps_are_iso_8601_utc(client: Client, providers: FakeProviders) -> None:
    body = request_body()
    data = post(client, body).json()

    route = data["routes"][0]
    checkpoint = route["checkpoints"][3]
    for value in (
        data["forecast_window"]["start"],
        data["forecast_window"]["end"],
        route["estimated_arrival_time"],
        checkpoint["estimated_arrival_time"],
        checkpoint["forecast_timestamp"],
        checkpoint["hourly_forecasts"][0]["target_time"],
    ):
        assert ISO_UTC.match(value), value
    sent = datetime.fromisoformat(body["departure_time"])
    assert datetime.fromisoformat(data["trip"]["departure_time"]) == sent
    window_end = datetime.fromisoformat(data["forecast_window"]["end"])
    assert window_end - sent == timedelta(hours=48)
    arrival = datetime.fromisoformat(route["estimated_arrival_time"])
    assert arrival - sent == timedelta(seconds=28580)


@VALHALLA
def test_recommendation_and_provider_warnings(client: Client, providers: FakeProviders) -> None:
    data = post(client, request_body()).json()

    recommendation = data["recommendation"]
    assert recommendation["recommended_route_id"] == "route-1"  # equal risk; faster
    assert recommendation["ranked_route_ids"] == ["route-1", "route-2"]
    assert len(recommendation["ranking_reasons"]) == 2
    assert recommendation["ranking_reasons"][0].startswith("Route A is recommended")
    assert recommendation["warnings"] == []
    assert data["provider_warnings"] == [
        "The routing provider returned 2 of up to 3 requested routes. Only genuine provider "
        "routes are shown."
    ]


@VALHALLA
def test_missing_weather_values_are_null_not_zero(client: Client, providers: FakeProviders) -> None:
    providers.weather_values = lambda i: (16.09344, None, 0.0)  # precipitation missing

    data = post(client, request_body()).json()

    checkpoint = data["routes"][0]["checkpoints"][1]
    assert checkpoint["precipitation_inches_per_hour"] is None
    assert checkpoint["snowfall_inches_per_hour"] == 0.0
    assert checkpoint["rain_risk"] == "UNKNOWN"
    assert checkpoint["data_status"] == "PARTIAL"
    assert checkpoint["warnings"][0].startswith("Incomplete weather data: precipitation")
    metrics = data["routes"][0]["metrics"]
    assert metrics["weather_coverage_percent"] == 100.0
    assert metrics["complete_weather_coverage_percent"] == 0.0
    assert any("Incomplete weather data" in w for w in data["recommendation"]["warnings"])


@VALHALLA
def test_severe_weather_changes_the_recommendation(
    client: Client, providers: FakeProviders
) -> None:
    # Strong wind for every hour; with 45,000 lb the wind rules give NO_TRAVEL everywhere.
    providers.weather_values = lambda i: (80.0, 0.0, 0.0)  # ~49.7 mph

    data = post(client, request_body(load_weight_lbs=45000)).json()

    route = data["routes"][0]
    assert route["checkpoints"][1]["wind_risk"] == "NO_TRAVEL"
    assert route["metrics"]["no_travel_miles"] == pytest.approx(536.2)
    assert "No route is free of NO_TRAVEL conditions." in data["recommendation"]["warnings"]


# Errors


@VALHALLA
def test_invalid_request_is_rejected_before_any_provider_call(
    client: Client, providers: FakeProviders
) -> None:
    past = (datetime.now(UTC) - timedelta(hours=1)).isoformat()

    response = post(client, request_body(departure_time=past, checkpoint_interval_miles=30))

    assert response.status_code == 400
    error = response.json()["error"]
    assert error["code"] == "VALIDATION_ERROR"
    assert set(error["details"]) == {"departure_time", "checkpoint_interval_miles"}
    assert providers.requests == []


@VALHALLA
def test_ambiguous_address_returns_candidates(client: Client, providers: FakeProviders) -> None:
    response = post(client, request_body(origin="Springfield"))

    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "GEOCODING_AMBIGUOUS"
    assert error["details"]["field"] == "origin"
    assert [c["label"] for c in error["details"]["candidates"]] == [
        "Springfield, MO, USA",
        "Springfield, MA, USA",
    ]


@VALHALLA
def test_unknown_address(client: Client, providers: FakeProviders) -> None:
    response = post(client, request_body(destination="Nowhere at all"))

    assert response.status_code == 422
    assert response.json()["error"] == {
        "code": "GEOCODING_NOT_FOUND",
        "message": "No location was found for the destination address.",
        "details": {"field": "destination"},
    }


@VALHALLA
def test_route_beyond_the_routing_distance_limit(client: Client, providers: FakeProviders) -> None:
    providers.valhalla = lambda r: httpx.Response(
        400, json={"error_code": 154, "error": "Path distance exceeds the max distance limit"}
    )

    response = post(client, request_body())

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "ROUTE_DISTANCE_LIMIT"


@pytest.mark.parametrize(
    ("failing", "provider_response", "status", "code"),
    [
        ("geocode", httpx.Response(500), 502, "PROVIDER_ERROR"),
        ("valhalla", httpx.Response(503), 503, "PROVIDER_UNAVAILABLE"),
        ("weather", httpx.Response(429), 503, "PROVIDER_RATE_LIMITED"),
        ("weather", httpx.Response(200, json={"hourly": "nope"}), 502, "PROVIDER_ERROR"),
    ],
)
@VALHALLA
def test_provider_failures_map_to_documented_statuses(
    client: Client,
    providers: FakeProviders,
    failing: str,
    provider_response: httpx.Response,
    status: int,
    code: str,
) -> None:
    setattr(providers, failing, lambda r: provider_response)

    response = post(client, request_body())

    assert response.status_code == status
    assert response.json()["error"]["code"] == code
    assert "recommendation" not in response.json()


@VALHALLA
def test_provider_timeout_returns_504(client: Client, providers: FakeProviders) -> None:
    def timeout(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("timed out", request=request)

    providers.valhalla = timeout

    response = post(client, request_body())

    assert response.status_code == 504
    assert response.json()["error"]["code"] == "PROVIDER_TIMEOUT"


def test_only_post_is_allowed(client: Client) -> None:
    response = client.get(URL)

    assert response.status_code == 405
    assert response.json()["error"]["code"] == "METHOD_NOT_ALLOWED"


def test_endpoint_is_in_the_openapi_schema(client: Client) -> None:
    schema = client.get("/api/schema/", HTTP_ACCEPT="application/vnd.oai.openapi+json").json()

    operation = schema["paths"]["/api/v1/routes/analyze/"]["post"]
    assert set(operation["responses"]) == {"200", "400", "422", "429", "502", "503", "504"}
    assert set(schema["components"]["schemas"]["RiskLevelEnum"]["enum"]) == RISKS


# Departure time echo


@VALHALLA
def test_trip_departure_time_keeps_the_offset_the_client_sent(
    client: Client, providers: FakeProviders
) -> None:
    body = request_body()  # for example 2026-11-02T03:00:00-07:00

    data = post(client, body).json()

    assert data["trip"]["departure_time"] == body["departure_time"]
    assert data["trip"]["departure_time"].endswith("-07:00")
    # Every other timestamp stays in UTC.
    assert data["forecast_window"]["start"].endswith("Z")
    assert datetime.fromisoformat(data["forecast_window"]["start"]) == datetime.fromisoformat(
        body["departure_time"]
    )


@VALHALLA
def test_utc_departure_is_echoed_in_utc(client: Client, providers: FakeProviders) -> None:
    utc_departure = (datetime.now(UTC) + timedelta(days=1)).replace(
        minute=0, second=0, microsecond=0
    )

    data = post(client, request_body(departure_time=utc_departure.isoformat())).json()

    assert data["trip"]["departure_time"] == utc_departure.strftime("%Y-%m-%dT%H:%M:%SZ")


# Forecast horizon


@VALHALLA
def test_departure_beyond_the_forecast_range_is_unknown_with_a_clear_warning(
    client: Client, providers: FakeProviders
) -> None:
    far = (datetime.now(UTC) + timedelta(days=20)).replace(minute=0, second=0, microsecond=0)

    response = post(client, request_body(departure_time=far.isoformat()))

    assert response.status_code == 200
    data = response.json()
    assert "api.open-meteo.com" not in providers.hosts()  # nothing to fetch yet
    (horizon_warning,) = [w for w in data["provider_warnings"] if "only available until" in w]
    assert "checkpoints are reached after that" in horizon_warning
    checkpoint = data["routes"][0]["checkpoints"][1]
    assert checkpoint["final_risk"] == "UNKNOWN"
    assert checkpoint["wind_speed_mph"] is None
    assert data["routes"][0]["metrics"]["weather_coverage_percent"] == 0.0
    assert any("not a weather assessment" in w for w in data["recommendation"]["warnings"])


# Rate limiting (this API's own limit, separate from provider limits)


@pytest.fixture
def two_per_minute(monkeypatch: pytest.MonkeyPatch) -> None:
    from rest_framework.throttling import ScopedRateThrottle

    monkeypatch.setattr(ScopedRateThrottle, "THROTTLE_RATES", {"analyze": "2/minute"})


@VALHALLA
@pytest.mark.usefixtures("two_per_minute")
def test_too_many_analysis_requests_get_429_with_retry_after(
    client: Client, providers: FakeProviders
) -> None:
    statuses = [post(client, request_body()).status_code for _ in range(2)]

    throttled = post(client, request_body())

    assert statuses == [200, 200]
    assert throttled.status_code == 429
    error = throttled.json()["error"]
    assert error["code"] == "RATE_LIMITED"
    assert error["message"] == "Too many analysis requests. Try again later."
    assert 0 < error["details"]["retry_after_seconds"] <= 60
    assert throttled["Retry-After"] == str(error["details"]["retry_after_seconds"])
    assert providers.hosts().count("valhalla.test") == 2  # the third request never ran


@pytest.mark.usefixtures("two_per_minute")
def test_other_endpoints_are_not_rate_limited(client: Client) -> None:
    for _ in range(5):
        assert client.get("/api/health/").status_code == 200
        assert client.get("/api/docs/").status_code == 200


def test_analysis_rate_limit_comes_from_the_environment() -> None:
    from django.conf import settings
    from rest_framework.throttling import ScopedRateThrottle

    from api.views.analyze import AnalyzeTripView

    assert AnalyzeTripView.throttle_scope == "analyze"
    assert ScopedRateThrottle in AnalyzeTripView.throttle_classes
    assert ScopedRateThrottle.THROTTLE_RATES["analyze"] == settings.ANALYZE_RATE_LIMIT
    assert settings.ANALYZE_RATE_LIMIT == os.environ["ANALYZE_RATE_LIMIT"]
