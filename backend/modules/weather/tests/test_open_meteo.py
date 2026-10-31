from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx
import pytest

from modules.weather.services.open_meteo import ForecastHour, OpenMeteoForecastService
from shared.http import get_http_client
from shared.types import (
    Coordinate,
    ProviderError,
    ProviderRateLimitError,
    ProviderTimeoutError,
)

NOW = datetime(2026, 10, 31, 10, 20, tzinfo=UTC)
START = datetime(2026, 11, 1, 8, 0, tzinfo=UTC)
DENVER = Coordinate(39.7392, -104.9903)
SALT_LAKE_CITY = Coordinate(40.7608, -111.8910)
UNITS = {"time": "unixtime", "wind_speed_10m": "km/h", "precipitation": "mm", "snowfall": "cm"}


def location_payload(
    hours: int = 2,
    wind: list[Any] | None = None,
    precipitation: list[Any] | None = None,
    snowfall: list[Any] | None = None,
    units: dict[str, str] | None = None,
) -> dict[str, Any]:
    times = [int((START + timedelta(hours=h)).timestamp()) for h in range(hours)]
    return {
        "latitude": 39.75,
        "longitude": -104.99,
        "hourly_units": units or UNITS,
        "hourly": {
            "time": times,
            "wind_speed_10m": wind if wind is not None else [16.09344] * hours,
            "precipitation": precipitation if precipitation is not None else [2.54] * hours,
            "snowfall": snowfall if snowfall is not None else [2.54] * hours,
        },
    }


class Recorder:
    def __init__(self, respond: Callable[[httpx.Request], httpx.Response]) -> None:
        self.respond = respond
        self.requests: list[httpx.Request] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        return self.respond(request)


def service(handler: Callable[[httpx.Request], httpx.Response]) -> OpenMeteoForecastService:
    return OpenMeteoForecastService(
        httpx.Client(transport=httpx.MockTransport(handler)), clock=lambda: NOW
    )


def echo_locations(request: httpx.Request) -> httpx.Response:
    count = len(request.url.params["latitude"].split(","))
    payload = [location_payload() for _ in range(count)]
    return httpx.Response(200, json=payload if count > 1 else payload[0])


def test_requests_hourly_variables_for_all_locations_in_one_call() -> None:
    recorder = Recorder(echo_locations)

    service(recorder).get_hourly_forecasts(
        [DENVER, SALT_LAKE_CITY], START, START + timedelta(hours=1, minutes=30)
    )

    (request,) = recorder.requests
    params = request.url.params
    assert request.url.host == "api.open-meteo.com"
    assert params["latitude"] == "39.73920,40.76080"
    assert params["longitude"] == "-104.99030,-111.89100"
    assert params["hourly"] == "wind_speed_10m,precipitation,snowfall"
    assert params["timezone"] == "GMT"
    assert params["timeformat"] == "unixtime"
    assert params["start_hour"] == "2026-11-01T08:00"
    assert params["end_hour"] == "2026-11-01T10:00"


def test_values_are_converted_to_mph_and_inches() -> None:
    (forecast,) = service(echo_locations).get_hourly_forecasts([DENVER], START, START)

    assert forecast.coordinate == DENVER
    assert forecast.hours[0] == ForecastHour(
        timestamp=START,
        wind_speed_mph=pytest.approx(10.0),
        precipitation_inches_per_hour=pytest.approx(0.1),
        snowfall_inches_per_hour=pytest.approx(1.0),
    )
    assert forecast.hours[1].timestamp == START + timedelta(hours=1)


def test_missing_values_stay_none() -> None:
    payload = location_payload(wind=[None, 10.0], precipitation=[0.0, None], snowfall=[None, None])

    (forecast,) = service(lambda request: httpx.Response(200, json=payload)).get_hourly_forecasts(
        [DENVER], START, START
    )

    assert forecast.hours[0].wind_speed_mph is None
    assert forecast.hours[0].precipitation_inches_per_hour == 0.0
    assert forecast.hours[1].precipitation_inches_per_hour is None
    assert forecast.hours[1].snowfall_inches_per_hour is None


def test_large_location_lists_are_batched_in_order() -> None:
    recorder = Recorder(echo_locations)
    coordinates = [Coordinate(30 + i * 0.01, -100.0) for i in range(150)]

    forecasts = service(recorder).get_hourly_forecasts(coordinates, START, START)

    assert [len(r.url.params["latitude"].split(",")) for r in recorder.requests] == [100, 50]
    assert [f.coordinate for f in forecasts] == coordinates


def test_window_is_cut_off_at_forecast_horizon() -> None:
    recorder = Recorder(echo_locations)

    service(recorder).get_hourly_forecasts([DENVER], START, NOW + timedelta(days=30))

    assert recorder.requests[0].url.params["end_hour"] == "2026-11-15T23:00"


def test_window_beyond_horizon_returns_empty_forecasts_without_a_request() -> None:
    recorder = Recorder(echo_locations)
    start = NOW + timedelta(days=20)

    forecasts = service(recorder).get_hourly_forecasts([DENVER], start, start + timedelta(hours=48))

    assert recorder.requests == []
    assert forecasts[0].hours == ()


def test_no_coordinates_makes_no_request() -> None:
    recorder = Recorder(echo_locations)

    assert service(recorder).get_hourly_forecasts([], START, START) == []
    assert recorder.requests == []


@pytest.mark.parametrize(
    "payload",
    [
        [location_payload(), location_payload()],  # two results for one location
        location_payload(units={**UNITS, "wind_speed_10m": "mp/h"}),
        location_payload(wind=[1.0]),  # length mismatch
        location_payload(wind=["calm", 1.0]),
        location_payload(precipitation=[-1.0, 0.0]),
        {"hourly": {}},
        "not an object",
    ],
)
def test_malformed_responses_raise_provider_error(payload: Any) -> None:
    with pytest.raises(ProviderError):
        service(lambda request: httpx.Response(200, json=payload)).get_hourly_forecasts(
            [DENVER], START, START
        )


def test_provider_error_reason_is_not_retried_or_hidden_as_success() -> None:
    body = {"error": True, "reason": "Parameter 'end_hour' is out of allowed range"}

    with pytest.raises(ProviderError) as error:
        service(lambda request: httpx.Response(400, json=body)).get_hourly_forecasts(
            [DENVER], START, START
        )

    assert error.value.details == {"provider": "Open-Meteo"}


def test_rate_limit_is_reported() -> None:
    with pytest.raises(ProviderRateLimitError):
        service(lambda request: httpx.Response(429)).get_hourly_forecasts([DENVER], START, START)


def test_timeout_is_reported() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectTimeout("timed out", request=request)

    with pytest.raises(ProviderTimeoutError):
        service(handler).get_hourly_forecasts([DENVER], START, START)


def test_naive_or_reversed_windows_are_programming_errors() -> None:
    forecasts = service(echo_locations)

    with pytest.raises(ValueError):
        forecasts.get_hourly_forecasts([DENVER], START.replace(tzinfo=None), START)
    with pytest.raises(ValueError):
        forecasts.get_hourly_forecasts([DENVER], START, START - timedelta(hours=1))


def test_uses_the_shared_configured_client_by_default() -> None:
    assert OpenMeteoForecastService()._client is get_http_client()
