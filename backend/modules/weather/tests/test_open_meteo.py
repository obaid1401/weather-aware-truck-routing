from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx
import pytest
from django.core.exceptions import ImproperlyConfigured
from django.test import override_settings

from modules.weather.services.open_meteo import (
    PROXY_TOKEN_HEADER,
    ForecastHour,
    OpenMeteoForecastService,
)
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


def test_up_to_100_locations_are_fetched_in_one_request_in_order() -> None:
    recorder = Recorder(echo_locations)
    coordinates = [Coordinate(30 + i * 0.01, -100.0) for i in range(100)]

    forecasts = service(recorder).get_hourly_forecasts(coordinates, START, START)

    assert [len(r.url.params["latitude"].split(",")) for r in recorder.requests] == [100]
    assert [f.coordinate for f in forecasts] == coordinates


def test_more_than_100_locations_is_a_programming_error() -> None:
    # Batching larger sets is the caller's job (CheckpointWeatherService).
    recorder = Recorder(echo_locations)
    coordinates = [Coordinate(30 + i * 0.01, -100.0) for i in range(101)]

    with pytest.raises(ValueError):
        service(recorder).get_hourly_forecasts(coordinates, START, START)
    assert recorder.requests == []


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


# Configuration: base URL and proxy token

PROXY = "https://weather-proxy.example.workers.dev"
TOKEN = "proxy-secret-for-tests"


def configured_request(**settings: str) -> httpx.Request:
    """The request sent for one location with the given Open-Meteo settings."""
    recorder = Recorder(echo_locations)
    with override_settings(**settings):
        # Same default headers as the shared client, so header merging is exercised.
        client = httpx.Client(
            transport=httpx.MockTransport(recorder), headers=get_http_client().headers
        )
        forecasts = OpenMeteoForecastService(client, clock=lambda: NOW)
    forecasts.get_hourly_forecasts([DENVER], START, START)
    (request,) = recorder.requests
    return request


def endpoint(request: httpx.Request) -> str:
    return str(request.url.copy_with(query=None))


def test_default_forecast_url_is_the_public_api_without_a_token() -> None:
    request = configured_request(
        OPEN_METEO_BASE_URL="https://api.open-meteo.com", OPEN_METEO_PROXY_TOKEN=""
    )

    assert endpoint(request) == "https://api.open-meteo.com/v1/forecast"
    assert PROXY_TOKEN_HEADER not in request.headers


@pytest.mark.parametrize("base_url", [PROXY, f"{PROXY}/", f"  {PROXY}/  "])
def test_custom_base_url_builds_the_forecast_url(base_url: str) -> None:
    request = configured_request(OPEN_METEO_BASE_URL=base_url, OPEN_METEO_PROXY_TOKEN="")

    assert endpoint(request) == f"{PROXY}/v1/forecast"
    assert PROXY_TOKEN_HEADER not in request.headers


def test_request_parameters_and_client_headers_are_unchanged_through_a_proxy() -> None:
    public = configured_request(
        OPEN_METEO_BASE_URL="https://api.open-meteo.com", OPEN_METEO_PROXY_TOKEN=""
    )
    proxied = configured_request(OPEN_METEO_BASE_URL=PROXY, OPEN_METEO_PROXY_TOKEN=TOKEN)

    assert dict(proxied.url.params) == dict(public.url.params)
    assert proxied.method == public.method == "GET"


@pytest.mark.parametrize(
    "base_url",
    [
        "",
        "   ",
        "api.open-meteo.com",
        "ftp://proxy.example",
        "https://",
        f"{PROXY}/?key=1",
        "https://[proxy",
        "https://proxy.example:abc",
        "https://proxy.example:99999",
    ],
)
def test_empty_or_invalid_base_url_is_a_configuration_error(base_url: str) -> None:
    with (
        override_settings(OPEN_METEO_BASE_URL=base_url, OPEN_METEO_PROXY_TOKEN=""),
        pytest.raises(ImproperlyConfigured, match="OPEN_METEO_BASE_URL"),
    ):
        OpenMeteoForecastService(httpx.Client())


def test_proxy_token_is_sent_to_a_configured_proxy() -> None:
    request = configured_request(OPEN_METEO_BASE_URL=PROXY, OPEN_METEO_PROXY_TOKEN=TOKEN)

    assert endpoint(request) == f"{PROXY}/v1/forecast"
    assert request.headers[PROXY_TOKEN_HEADER] == TOKEN
    # The shared client's own headers are kept.
    assert request.headers["User-Agent"] == get_http_client().headers["User-Agent"]


def test_proxy_token_is_allowed_over_http_only_for_a_local_proxy() -> None:
    request = configured_request(
        OPEN_METEO_BASE_URL="http://localhost:8787", OPEN_METEO_PROXY_TOKEN=TOKEN
    )
    assert request.headers[PROXY_TOKEN_HEADER] == TOKEN

    with (
        override_settings(
            OPEN_METEO_BASE_URL="http://weather-proxy.example", OPEN_METEO_PROXY_TOKEN=TOKEN
        ),
        pytest.raises(ImproperlyConfigured, match="must use https") as error,
    ):
        OpenMeteoForecastService(httpx.Client())
    assert TOKEN not in str(error.value)


@pytest.mark.parametrize(
    "base_url",
    [
        "https://api.open-meteo.com",
        "https://API.Open-Meteo.com/",
        "https://customer-api.open-meteo.com",
        "https://open-meteo.com",
        "https://api.open-meteo.com.",
        "https://API.OPEN-METEO.COM.:443/",
    ],
)
def test_proxy_token_is_never_sent_to_open_meteo_itself(base_url: str) -> None:
    sent: list[httpx.Request] = []
    with (
        override_settings(OPEN_METEO_BASE_URL=base_url, OPEN_METEO_PROXY_TOKEN=TOKEN),
        pytest.raises(ImproperlyConfigured, match="points to Open-Meteo itself") as error,
    ):
        OpenMeteoForecastService(httpx.Client(transport=httpx.MockTransport(sent.append)))

    assert sent == []
    assert TOKEN not in str(error.value)


# Provider response validation


def with_times(times: list[Any], **overrides: Any) -> dict[str, Any]:
    payload = location_payload(hours=len(times))
    payload["hourly"]["time"] = times
    payload.update(overrides)
    return payload


HOUR_0 = int(START.timestamp())


def fetch(payload: Any, coordinates: list[Coordinate] | None = None) -> Any:
    return service(lambda request: httpx.Response(200, json=payload)).get_hourly_forecasts(
        coordinates or [DENVER], START, START
    )


@pytest.mark.parametrize(
    "times",
    [
        [HOUR_0, HOUR_0],  # duplicate
        [HOUR_0, HOUR_0 + 3600, HOUR_0 + 3600],  # duplicate later on
        [HOUR_0 + 3600, HOUR_0],  # out of order
        [HOUR_0, HOUR_0 + 900],  # not on a whole hour
        [HOUR_0 + 0.5, HOUR_0 + 3600],  # fractional second
        ["2026-11-01T08:00", "2026-11-01T09:00"],  # ISO strings, not unixtime
        [None, HOUR_0],
        [True, HOUR_0],
    ],
)
def test_duplicate_or_invalid_timestamps_are_rejected(times: list[Any]) -> None:
    with pytest.raises(ProviderError):
        fetch(with_times(times))


def test_valid_hourly_timestamps_are_accepted() -> None:
    (forecast,) = fetch(with_times([HOUR_0, HOUR_0 + 3600, HOUR_0 + 7200]))

    assert [h.timestamp for h in forecast.hours] == [START + timedelta(hours=h) for h in range(3)]
    assert all(h.timestamp.tzinfo is UTC for h in forecast.hours)


@pytest.mark.parametrize(
    "location_ids",
    [
        [None, 1, 2],  # Open-Meteo omits the id on the first result
        [0, 1, 2],
    ],
)
def test_results_in_request_order_are_accepted(location_ids: list[int | None]) -> None:
    payload = [location_payload(wind=[float(i)] * 2) for i in range(3)]
    for location, location_id in zip(payload, location_ids, strict=True):
        if location_id is not None:
            location["location_id"] = location_id
    coordinates = [DENVER, SALT_LAKE_CITY, Coordinate(40.0, -105.0)]

    forecasts = fetch(payload, coordinates)

    assert [f.coordinate for f in forecasts] == coordinates
    assert [f.hours[0].wind_speed_mph for f in forecasts] == pytest.approx(
        [0.0, 1 / 1.609344, 2 / 1.609344]
    )


@pytest.mark.parametrize(
    "location_ids",
    [
        [None, 2, 1],  # results swapped
        [1, 0, 2],
        [None, 1, 1],
        [None, True, 2],  # a boolean is not an id
        [None, "1", 2],
    ],
)
def test_results_out_of_request_order_are_rejected(location_ids: list[Any]) -> None:
    payload = [location_payload() for _ in range(3)]
    for location, location_id in zip(payload, location_ids, strict=True):
        if location_id is not None:
            location["location_id"] = location_id

    with pytest.raises(ProviderError):
        fetch(payload, [DENVER, SALT_LAKE_CITY, Coordinate(40.0, -105.0)])


@pytest.mark.parametrize(
    "units",
    [
        None,  # hourly_units missing entirely
        {"time": "unixtime", "precipitation": "mm", "snowfall": "cm"},  # wind unit missing
        {"time": "unixtime", "wind_speed_10m": "km/h", "snowfall": "cm"},
        {"time": "unixtime", "wind_speed_10m": "km/h", "precipitation": "mm"},
        {"wind_speed_10m": "km/h", "precipitation": "mm", "snowfall": "cm"},  # time missing
        {**UNITS, "time": "iso8601"},
        {**UNITS, "precipitation": "inch"},
        {**UNITS, "snowfall": "inch"},
        "km/h",
    ],
)
def test_missing_or_unexpected_units_are_rejected(units: Any) -> None:
    payload = location_payload()
    if units is None:
        del payload["hourly_units"]
    else:
        payload["hourly_units"] = units

    with pytest.raises(ProviderError):
        fetch(payload)


# Provider forecast range shorter than our computed horizon

END = START + timedelta(hours=48)  # 2026-11-03 08:00 UTC, within our computed horizon


def range_error(last_day: str = "2026-11-02", parameter: str = "end_hour") -> httpx.Response:
    return httpx.Response(
        400,
        json={
            "error": True,
            "reason": f"Parameter '{parameter}' is out of allowed range from 2026-07-30 "
            f"to {last_day}",
        },
    )


def hours_until(end_hour: str) -> dict[str, Any]:
    """A payload with every hour from START through `end_hour` (inclusive)."""
    last = datetime.strptime(end_hour, "%Y-%m-%dT%H:%M").replace(tzinfo=UTC)
    count = int((last - START) / timedelta(hours=1)) + 1
    return location_payload(hours=count)


class Responses:
    """Returns the given responses in order and records each request."""

    def __init__(self, *responses: Callable[[httpx.Request], httpx.Response]) -> None:
        self.responses = list(responses)
        self.requests: list[httpx.Request] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        return self.responses.pop(0)(request)


def test_out_of_range_end_is_retried_once_within_the_providers_range() -> None:
    handler = Responses(
        lambda request: range_error("2026-11-02"),
        lambda request: httpx.Response(200, json=hours_until(request.url.params["end_hour"])),
    )

    (forecast,) = service(handler).get_hourly_forecasts([DENVER], START, END)

    first, retry = handler.requests
    assert first.url.params["end_hour"] == "2026-11-03T08:00"
    assert retry.url.params["end_hour"] == "2026-11-02T23:00"
    assert retry.url.params["start_hour"] == first.url.params["start_hour"] == "2026-11-01T08:00"
    # Every available hour is kept: 08:00 on Nov 1 through 23:00 on Nov 2.
    assert len(forecast.hours) == 40
    assert forecast.hours[-1].timestamp == datetime(2026, 11, 2, 23, 0, tzinfo=UTC)
    assert all(h.wind_speed_mph == pytest.approx(10.0) for h in forecast.hours)


def test_hours_beyond_the_providers_range_are_absent_not_zero() -> None:
    handler = Responses(
        lambda request: range_error("2026-11-02"),
        lambda request: httpx.Response(200, json=hours_until(request.url.params["end_hour"])),
    )

    (forecast,) = service(handler).get_hourly_forecasts([DENVER], START, END)

    timestamps = {h.timestamp for h in forecast.hours}
    assert datetime(2026, 11, 3, 0, 0, tzinfo=UTC) not in timestamps
    assert datetime(2026, 11, 3, 8, 0, tzinfo=UTC) not in timestamps


def test_window_entirely_beyond_the_providers_range_returns_no_hours() -> None:
    handler = Responses(lambda request: range_error("2026-10-31", parameter="start_hour"))

    (forecast,) = service(handler).get_hourly_forecasts([DENVER], START, END)

    assert forecast.hours == ()
    assert len(handler.requests) == 1


def test_a_second_failure_is_not_retried_again() -> None:
    handler = Responses(
        lambda request: range_error("2026-11-02"),
        lambda request: range_error("2026-11-01"),
    )

    with pytest.raises(ProviderError):
        service(handler).get_hourly_forecasts([DENVER], START, END)
    assert len(handler.requests) == 2


@pytest.mark.parametrize(
    "response",
    [
        httpx.Response(400, json={"error": True, "reason": "Cannot initialize WeatherVariable"}),
        httpx.Response(
            400, json={"error": True, "reason": "Latitude must be in range of -90 to 90°"}
        ),
        httpx.Response(400, text="Bad Request"),
    ],
)
def test_unrelated_bad_requests_are_not_retried(response: httpx.Response) -> None:
    handler = Responses(lambda request: response)

    with pytest.raises(ProviderError) as error:
        service(handler).get_hourly_forecasts([DENVER], START, END)

    assert len(handler.requests) == 1
    assert error.value.message == "Open-Meteo returned an error (HTTP 400)."


@pytest.mark.parametrize(
    "reason",
    [
        "Parameter 'end_hour' is out of allowed range",  # no dates
        "Parameter 'end_hour' is out of allowed range from 2026-07-30 to 2026-13-45",  # bad date
        "Parameter 'end_hour' is out of allowed range from 2026-07-30 to 15/11/2026",
        "Parameter 'end_hour' is out of allowed range from 2026-07-30 to 2026-11-16",  # not earlier
        None,
        ["out of allowed range"],
    ],
)
def test_unparseable_or_unhelpful_range_errors_keep_the_existing_behavior(reason: Any) -> None:
    handler = Responses(lambda request: httpx.Response(400, json={"error": True, "reason": reason}))

    with pytest.raises(ProviderError) as error:
        service(handler).get_hourly_forecasts([DENVER], START, END)

    assert len(handler.requests) == 1
    assert error.value.message == "Open-Meteo returned an error (HTTP 400)."
