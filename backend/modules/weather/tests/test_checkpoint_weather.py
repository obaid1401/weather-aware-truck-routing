from collections.abc import Callable, Sequence
from datetime import UTC, datetime, timedelta, timezone
from typing import Any
from zoneinfo import ZoneInfo

import httpx
import pytest

from modules.weather.services.checkpoint_weather import CheckpointWeatherService
from modules.weather.services.open_meteo import (
    ForecastHour,
    LocationForecast,
    OpenMeteoForecastService,
)
from shared.types import (
    Checkpoint,
    Coordinate,
    DataStatus,
    ProviderError,
    ProviderRateLimitError,
    ProviderTimeoutError,
)

MOUNTAIN = timezone(timedelta(hours=-7))
DEPARTURE = datetime(2026, 11, 5, 8, 0, tzinfo=MOUNTAIN)  # 15:00 UTC
DENVER = Coordinate(39.7392, -104.9903)
BOULDER = Coordinate(40.0150, -105.2705)


def utc_hour(offset: int) -> datetime:
    """The UTC hour `offset` hours after departure."""
    return DEPARTURE.astimezone(UTC) + timedelta(hours=offset)


def full_hours(first: int = 0, last: int = 50, wind: float = 10.0) -> tuple[ForecastHour, ...]:
    """Forecast hours relative to departure; wind is `wind + offset` to identify each hour."""
    return tuple(
        ForecastHour(utc_hour(offset), wind + offset, 0.01, 0.0)
        for offset in range(first, last + 1)
    )


def checkpoint(
    coordinate: Coordinate = DENVER,
    eta: datetime = DEPARTURE,
    route_id: str = "route-1",
    number: int = 0,
) -> Checkpoint:
    return Checkpoint(
        id=f"{route_id}-cp-{number}",
        route_id=route_id,
        distance_from_origin_miles=float(number * 25),
        latitude=coordinate.latitude,
        longitude=coordinate.longitude,
        estimated_arrival_time=eta,
    )


class StubForecasts:
    """Stands in for OpenMeteoForecastService and records every request."""

    def __init__(
        self,
        hours: Callable[[Coordinate], tuple[ForecastHour, ...]] = lambda c: full_hours(),
        errors: dict[int, Exception] | None = None,
        horizon_end: datetime = datetime(2100, 1, 1, tzinfo=UTC),
    ) -> None:
        self.hours = hours
        self.errors = errors or {}
        self.horizon_end = horizon_end
        self.calls: list[tuple[list[Coordinate], datetime, datetime]] = []

    def forecast_horizon_end(self) -> datetime:
        return self.horizon_end

    def get_hourly_forecasts(
        self, coordinates: Sequence[Coordinate], start: datetime, end: datetime
    ) -> list[LocationForecast]:
        self.calls.append((list(coordinates), start, end))
        if len(self.calls) in self.errors:
            raise self.errors[len(self.calls)]
        return [LocationForecast(c, self.hours(c)) for c in coordinates]


def apply(
    checkpoints: Sequence[Checkpoint], stub: StubForecasts | None = None
) -> tuple[Any, StubForecasts]:
    stub = stub or StubForecasts()
    result = CheckpointWeatherService(stub).apply(checkpoints, DEPARTURE)  # type: ignore[arg-type]
    return result, stub


# ETA matching


@pytest.mark.parametrize(
    ("eta_minutes", "expected_offset"),
    [(0, 0), (80, 1), (100, 2), (90, 1)],  # 90 minutes is a tie: the earlier hour
)
def test_weather_is_matched_to_the_nearest_hour_of_the_eta(
    eta_minutes: int, expected_offset: int
) -> None:
    (cp,) = apply([checkpoint(eta=DEPARTURE + timedelta(minutes=eta_minutes))])[0].checkpoints

    assert cp.forecast_timestamp == utc_hour(expected_offset)
    assert cp.wind_speed_mph == 10.0 + expected_offset
    assert cp.precipitation_inches_per_hour == 0.01
    assert cp.snowfall_inches_per_hour == 0.0
    assert cp.data_status == DataStatus.AVAILABLE


def test_checkpoint_fields_from_earlier_phases_are_kept() -> None:
    original = checkpoint(eta=DEPARTURE + timedelta(hours=2), number=3)

    (cp,) = apply([original])[0].checkpoints

    assert (cp.id, cp.route_id, cp.distance_from_origin_miles) == ("route-1-cp-3", "route-1", 75.0)
    assert (cp.latitude, cp.longitude) == (original.latitude, original.longitude)
    assert cp.estimated_arrival_time == original.estimated_arrival_time


def test_checkpoints_keep_their_order() -> None:
    cps = [checkpoint(BOULDER, number=1), checkpoint(DENVER, number=0)]

    result = apply(cps)[0]

    assert [cp.id for cp in result.checkpoints] == ["route-1-cp-1", "route-1-cp-0"]


# Hourly series


def test_hourly_series_covers_0_to_48_hours_after_departure() -> None:
    (cp,) = apply([checkpoint()])[0].checkpoints

    series = cp.hourly_forecasts
    assert [entry.hour_offset for entry in series] == list(range(49))
    assert [entry.target_time for entry in series] == [
        DEPARTURE + timedelta(hours=h) for h in range(49)
    ]
    assert all(entry.target_time.utcoffset() == timedelta(hours=-7) for entry in series)
    assert [entry.forecast_timestamp for entry in series] == [utc_hour(h) for h in range(49)]
    assert [entry.wind_speed_mph for entry in series] == [10.0 + h for h in range(49)]
    assert {entry.data_status for entry in series} == {DataStatus.AVAILABLE}


def test_series_is_independent_of_the_checkpoint_eta() -> None:
    late = checkpoint(eta=DEPARTURE + timedelta(hours=30))

    (cp,) = apply([late])[0].checkpoints

    assert cp.forecast_timestamp == utc_hour(30)
    assert cp.hourly_forecasts[0].forecast_timestamp == utc_hour(0)


def test_departure_between_hours_uses_the_earlier_hour_on_ties() -> None:
    departure = datetime(2026, 11, 5, 8, 30, tzinfo=MOUNTAIN)  # 15:30 UTC: every target ties
    stub = StubForecasts()

    result = CheckpointWeatherService(stub).apply(  # type: ignore[arg-type]
        [checkpoint(eta=departure)], departure
    )

    series = result.checkpoints[0].hourly_forecasts
    assert series[0].forecast_timestamp == utc_hour(0)  # 15:00, not 16:00
    assert series[48].forecast_timestamp == utc_hour(48)


def test_one_request_serves_both_eta_matching_and_the_series() -> None:
    cps = [checkpoint(eta=DEPARTURE + timedelta(hours=60))]  # beyond the 48-hour series

    stub = apply(cps)[1]

    ((coordinates, start, end),) = stub.calls
    assert coordinates == [DENVER]
    assert start == DEPARTURE
    assert end == DEPARTURE + timedelta(hours=60)


def test_window_is_at_least_48_hours() -> None:
    stub = apply([checkpoint(eta=DEPARTURE + timedelta(hours=3))])[1]

    assert stub.calls[0][2] == DEPARTURE + timedelta(hours=48)


# Missing and partial data


def test_missing_forecast_hours_are_unavailable_not_zero() -> None:
    # Forecast stops 10 hours after departure (for example at the provider's horizon).
    stub = StubForecasts(hours=lambda c: full_hours(last=10))
    late = checkpoint(eta=DEPARTURE + timedelta(hours=20))

    (cp,) = apply([late], stub)[0].checkpoints

    assert cp.forecast_timestamp is None
    assert cp.wind_speed_mph is None
    assert cp.precipitation_inches_per_hour is None
    assert cp.snowfall_inches_per_hour is None
    assert cp.data_status == DataStatus.UNAVAILABLE
    assert [e.data_status for e in cp.hourly_forecasts[:11]] == [DataStatus.AVAILABLE] * 11
    assert all(
        e.data_status == DataStatus.UNAVAILABLE
        and e.forecast_timestamp is None
        and e.wind_speed_mph is None
        for e in cp.hourly_forecasts[11:]
    )


def test_a_gap_is_not_filled_from_a_neighbouring_hour() -> None:
    hours = tuple(h for h in full_hours() if h.timestamp != utc_hour(2))
    stub = StubForecasts(hours=lambda c: hours)

    (cp,) = apply([checkpoint(eta=DEPARTURE + timedelta(hours=2, minutes=10))], stub)[0].checkpoints

    assert cp.data_status == DataStatus.UNAVAILABLE
    assert cp.hourly_forecasts[2].data_status == DataStatus.UNAVAILABLE
    assert cp.hourly_forecasts[3].data_status == DataStatus.AVAILABLE


def test_a_missing_variable_keeps_the_others() -> None:
    hours = (ForecastHour(utc_hour(0), None, 0.25, 0.0), *full_hours(first=1))
    stub = StubForecasts(hours=lambda c: hours)

    (cp,) = apply([checkpoint()], stub)[0].checkpoints

    assert cp.wind_speed_mph is None
    assert cp.precipitation_inches_per_hour == 0.25
    assert cp.snowfall_inches_per_hour == 0.0
    assert cp.data_status == DataStatus.PARTIAL
    assert cp.hourly_forecasts[0].data_status == DataStatus.PARTIAL
    assert cp.hourly_forecasts[0].precipitation_inches_per_hour == 0.25


def test_departure_beyond_the_forecast_horizon_is_unavailable_everywhere() -> None:
    stub = StubForecasts(hours=lambda c: ())

    result = apply([checkpoint(), checkpoint(BOULDER, number=1)], stub)[0]

    assert result.warnings == ()  # no provider failure; the data simply does not exist yet
    for cp in result.checkpoints:
        assert cp.data_status == DataStatus.UNAVAILABLE
        assert {e.data_status for e in cp.hourly_forecasts} == {DataStatus.UNAVAILABLE}


# Shared locations


def test_shared_checkpoint_locations_are_fetched_once() -> None:
    nearby = Coordinate(DENVER.latitude + 0.0002, DENVER.longitude - 0.0002)  # ~25 m away
    cps = [
        checkpoint(DENVER, route_id="route-1"),
        checkpoint(DENVER, route_id="route-2"),  # identical origin on another route
        checkpoint(nearby, route_id="route-3"),
        checkpoint(BOULDER, route_id="route-1", number=1),
    ]

    def hours(coordinate: Coordinate) -> tuple[ForecastHour, ...]:
        return full_hours(wind=50.0 if coordinate == BOULDER else 5.0)

    result, stub = apply(cps, StubForecasts(hours))

    ((coordinates, _, _),) = stub.calls
    assert coordinates == [DENVER, BOULDER]  # exact coordinates, no rounding
    assert [cp.wind_speed_mph for cp in result.checkpoints] == [5.0, 5.0, 5.0, 50.0]
    assert all(cp.data_status == DataStatus.AVAILABLE for cp in result.checkpoints)


def test_locations_a_metre_apart_are_shared_even_across_a_rounding_boundary() -> None:
    # -104.99050 and -104.99049 round to different 3-decimal values but are ~1 m apart.
    a = Coordinate(39.739, -104.99050)
    b = Coordinate(39.739, -104.99049)

    stub = apply([checkpoint(a), checkpoint(b, route_id="route-2")])[1]

    assert stub.calls[0][0] == [a]


@pytest.mark.parametrize(("offset_degrees", "shared"), [(0.0014, True), (0.0016, False)])
def test_locations_are_shared_within_a_tenth_of_a_mile(offset_degrees: float, shared: bool) -> None:
    # 0.0014 degrees of latitude is ~0.097 miles; 0.0016 is ~0.11 miles.
    other = Coordinate(DENVER.latitude + offset_degrees, DENVER.longitude)

    stub = apply([checkpoint(DENVER), checkpoint(other, route_id="route-2")])[1]

    assert len(stub.calls[0][0]) == (1 if shared else 2)


def test_each_checkpoint_gets_its_own_locations_forecast() -> None:
    def hours(coordinate: Coordinate) -> tuple[ForecastHour, ...]:
        return full_hours(wind=50.0 if coordinate.latitude > 40 else 5.0)

    result = apply([checkpoint(DENVER), checkpoint(BOULDER, number=1)], StubForecasts(hours))[0]

    assert [cp.wind_speed_mph for cp in result.checkpoints] == [5.0, 50.0]


def test_large_location_sets_are_fetched_in_sequential_batches() -> None:
    cps = [checkpoint(Coordinate(30 + i * 0.01, -100.0), number=i) for i in range(150)]

    stub = apply(cps)[1]

    assert [len(call[0]) for call in stub.calls] == [100, 50]


def test_no_checkpoints_makes_no_request() -> None:
    result, stub = apply([])

    assert result.checkpoints == () and result.warnings == ()
    assert stub.calls == []


# Provider failures


def many_locations(count: int) -> list[Checkpoint]:
    return [checkpoint(Coordinate(30 + i * 0.01, -100.0), number=i) for i in range(count)]


def test_failed_batch_leaves_only_its_checkpoints_unavailable() -> None:
    stub = StubForecasts(errors={2: ProviderError("Open-Meteo returned an invalid response.")})

    result = apply(many_locations(150), stub)[0]

    assert all(cp.data_status == DataStatus.AVAILABLE for cp in result.checkpoints[:100])
    assert all(cp.data_status == DataStatus.UNAVAILABLE for cp in result.checkpoints[100:])
    assert all(cp.wind_speed_mph is None for cp in result.checkpoints[100:])
    assert result.warnings == (
        "Weather forecasts could not be retrieved for 50 of 150 checkpoint locations "
        "(Open-Meteo returned an invalid response). Conditions there are UNKNOWN.",
    )


def test_rate_limit_stops_the_remaining_batches() -> None:
    stub = StubForecasts(
        errors={2: ProviderRateLimitError("Open-Meteo request limit was reached.")}
    )

    result = apply(many_locations(250), stub)[0]

    assert len(stub.calls) == 2  # the third batch is not sent
    assert sum(cp.data_status == DataStatus.AVAILABLE for cp in result.checkpoints) == 100
    assert "150 of 250" in result.warnings[0]


@pytest.mark.parametrize(
    "error", [ProviderTimeoutError(), ProviderRateLimitError(), ProviderError()]
)
def test_when_every_batch_fails_the_error_is_raised(error: Exception) -> None:
    stub = StubForecasts(errors={1: error, 2: error})

    with pytest.raises(type(error)):
        apply(many_locations(150), stub)


def test_naive_departure_is_rejected() -> None:
    with pytest.raises(ValueError):
        CheckpointWeatherService(StubForecasts()).apply(  # type: ignore[arg-type]
            [checkpoint()], datetime(2026, 11, 5, 8, 0)
        )


# End to end with the real Open-Meteo client (mocked HTTP)

NOW = datetime(2026, 11, 4, 12, 0, tzinfo=UTC)


def open_meteo_service(handler: Callable[[httpx.Request], httpx.Response]) -> Any:
    client = httpx.Client(transport=httpx.MockTransport(handler))
    return CheckpointWeatherService(OpenMeteoForecastService(client, clock=lambda: NOW))


def open_meteo_payload(request: httpx.Request) -> dict[str, Any]:
    count = len(request.url.params["latitude"].split(","))
    start = datetime.strptime(request.url.params["start_hour"], "%Y-%m-%dT%H:%M")
    times = [int((start.replace(tzinfo=UTC) + timedelta(hours=h)).timestamp()) for h in range(60)]
    location = {
        "hourly_units": {
            "time": "unixtime",
            "wind_speed_10m": "km/h",
            "precipitation": "mm",
            "snowfall": "cm",
        },
        "hourly": {
            "time": times,
            "wind_speed_10m": [16.09344] * 60,  # 10 mph
            "precipitation": [2.54] * 59 + [None],  # 0.1 in; last hour missing
            "snowfall": [5.08] * 60,  # 2 in
        },
    }
    return [location] * count if count > 1 else location  # type: ignore[return-value]


def test_end_to_end_values_are_converted_to_mph_and_inches() -> None:
    service = open_meteo_service(
        lambda request: httpx.Response(200, json=open_meteo_payload(request))
    )

    (cp,) = service.apply([checkpoint(eta=DEPARTURE + timedelta(hours=1))], DEPARTURE).checkpoints

    assert cp.wind_speed_mph == pytest.approx(10.0)
    assert cp.precipitation_inches_per_hour == pytest.approx(0.1)
    assert cp.snowfall_inches_per_hour == pytest.approx(2.0)
    assert cp.forecast_timestamp == utc_hour(1)
    assert cp.data_status == DataStatus.AVAILABLE


def test_end_to_end_malformed_response_raises_provider_error() -> None:
    service = open_meteo_service(lambda request: httpx.Response(200, json={"hourly": "nope"}))

    with pytest.raises(ProviderError):
        service.apply([checkpoint()], DEPARTURE)


def test_end_to_end_provider_error_status_is_raised() -> None:
    service = open_meteo_service(lambda request: httpx.Response(429))

    with pytest.raises(ProviderRateLimitError):
        service.apply([checkpoint()], DEPARTURE)


# Nearest shared location


def test_checkpoint_uses_the_nearest_shared_location_not_the_first() -> None:
    a = Coordinate(39.7, -105.0)
    b = Coordinate(39.7, -105.0 + 0.0024)  # ~0.128 mi from a: a separate location
    c = Coordinate(39.7, -105.0 + 0.0018)  # ~0.096 mi from a, ~0.032 mi from b

    def hours(coordinate: Coordinate) -> tuple[ForecastHour, ...]:
        return full_hours(wind=50.0 if coordinate == b else 5.0)

    result, stub = apply(
        [checkpoint(a), checkpoint(b, number=1), checkpoint(c, number=2)], StubForecasts(hours)
    )

    assert stub.calls[0][0] == [a, b]
    assert [cp.wind_speed_mph for cp in result.checkpoints] == [5.0, 50.0, 50.0]


def test_equidistant_checkpoint_uses_the_earlier_location() -> None:
    a, b = Coordinate(0.0, -0.0012), Coordinate(0.0, 0.0012)  # ~0.166 mi apart
    middle = Coordinate(0.0, 0.0)  # ~0.083 mi from each

    def hours(coordinate: Coordinate) -> tuple[ForecastHour, ...]:
        return full_hours(wind=50.0 if coordinate == b else 5.0)

    result = apply(
        [checkpoint(a), checkpoint(b, number=1), checkpoint(middle, number=2)],
        StubForecasts(hours),
    )[0]

    assert result.checkpoints[2].wind_speed_mph == 5.0


# Daylight-saving transitions (named time zones)

DENVER_TZ = ZoneInfo("America/Denver")


@pytest.mark.parametrize(
    "departure",
    [
        datetime(2026, 10, 31, 20, 0, tzinfo=DENVER_TZ),  # DST ends 2026-11-01 02:00
        datetime(2027, 3, 13, 20, 0, tzinfo=DENVER_TZ),  # DST starts 2027-03-14 02:00
    ],
)
def test_hourly_series_uses_real_elapsed_hours_across_dst(departure: datetime) -> None:
    departure_utc = departure.astimezone(UTC)
    stub = StubForecasts(
        hours=lambda c: tuple(
            ForecastHour(departure_utc + timedelta(hours=h), float(h), 0.0, 0.0) for h in range(60)
        )
    )

    result = CheckpointWeatherService(stub).apply(  # type: ignore[arg-type]
        [checkpoint(eta=departure)], departure
    )

    series = result.checkpoints[0].hourly_forecasts
    for h, entry in enumerate(series):
        assert entry.target_time.astimezone(UTC) - departure_utc == timedelta(hours=h)
        assert entry.target_time.tzinfo is DENVER_TZ
        assert entry.forecast_timestamp == departure_utc + timedelta(hours=h)  # none skipped
        assert entry.wind_speed_mph == float(h)
    assert series[0].target_time.utcoffset() != series[48].target_time.utcoffset()
    # The fetch window is 48 real hours long.
    assert stub.calls[0][2].astimezone(UTC) == departure_utc + timedelta(hours=48)


def test_provider_range_shorter_than_expected_keeps_earlier_hours_and_marks_later_unknown() -> None:
    # The provider's range ends at 23:00Z on the departure day, 8 hours after the 15:00Z
    # departure and earlier than our computed horizon. The client retries within that range.
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.params["end_hour"] != "2026-11-05T23:00":
            return httpx.Response(
                400,
                json={
                    "error": True,
                    "reason": "Parameter 'end_hour' is out of allowed range from 2026-08-05 "
                    "to 2026-11-05",
                },
            )
        start = datetime.strptime(request.url.params["start_hour"], "%Y-%m-%dT%H:%M")
        times = [
            int((start.replace(tzinfo=UTC) + timedelta(hours=h)).timestamp()) for h in range(9)
        ]
        return httpx.Response(
            200,
            json={
                "hourly_units": {
                    "time": "unixtime",
                    "wind_speed_10m": "km/h",
                    "precipitation": "mm",
                    "snowfall": "cm",
                },
                "hourly": {
                    "time": times,
                    "wind_speed_10m": [16.09344] * 9,
                    "precipitation": [0.0] * 9,
                    "snowfall": [0.0] * 9,
                },
            },
        )

    service = open_meteo_service(handler)
    late = checkpoint(eta=DEPARTURE + timedelta(hours=12))

    (cp,) = service.apply([late], DEPARTURE).checkpoints

    series = cp.hourly_forecasts
    assert [e.data_status for e in series[:9]] == [DataStatus.AVAILABLE] * 9  # through 23:00Z
    assert all(e.wind_speed_mph == pytest.approx(10.0) for e in series[:9])
    assert all(
        e.data_status == DataStatus.UNAVAILABLE and e.wind_speed_mph is None for e in series[9:]
    )
    assert cp.data_status == DataStatus.UNAVAILABLE  # its ETA is beyond the provider's range
    assert cp.wind_speed_mph is None


# Forecast horizon warnings (a range limit, not a provider failure)


def test_checkpoints_after_the_forecast_horizon_get_a_range_warning() -> None:
    # Forecast exists for 10 hours after departure (UTC 15:00 + 10 h = 01:00 next day).
    horizon = utc_hour(10)
    stub = StubForecasts(hours=lambda c: full_hours(last=10), horizon_end=horizon)
    cps = [
        checkpoint(eta=DEPARTURE + timedelta(hours=2)),
        checkpoint(BOULDER, eta=DEPARTURE + timedelta(hours=12), number=1),
        checkpoint(Coordinate(41.0, -106.0), eta=DEPARTURE + timedelta(hours=20), number=2),
    ]

    result = apply(cps, stub)[0]

    assert result.warnings == (
        "Weather forecasts are only available until 2026-11-06 01:00 UTC (about 16 days "
        "ahead). 2 of 3 checkpoints are reached after that, so their weather and risk are "
        "UNKNOWN.",
    )
    assert [cp.data_status for cp in result.checkpoints] == [
        DataStatus.AVAILABLE,
        DataStatus.UNAVAILABLE,
        DataStatus.UNAVAILABLE,
    ]
    assert result.checkpoints[1].wind_speed_mph is None  # unknown, never zero


def test_only_slider_hours_after_the_horizon_get_a_slider_warning() -> None:
    horizon = utc_hour(30)  # every ETA is covered; slider hours 31-48 are not
    stub = StubForecasts(hours=lambda c: full_hours(last=30), horizon_end=horizon)

    result = apply([checkpoint(eta=DEPARTURE + timedelta(hours=3))], stub)[0]

    assert result.warnings == (
        "Weather forecasts are only available until 2026-11-06 21:00 UTC. Forecast slider "
        "hours after that are UNKNOWN.",
    )
    series = result.checkpoints[0].hourly_forecasts
    assert series[30].data_status == DataStatus.AVAILABLE
    assert {e.data_status for e in series[31:]} == {DataStatus.UNAVAILABLE}


def test_departure_entirely_beyond_the_horizon_warns_without_a_provider_failure() -> None:
    stub = StubForecasts(hours=lambda c: (), horizon_end=DEPARTURE - timedelta(days=4))

    result = apply([checkpoint(), checkpoint(BOULDER, number=1)], stub)[0]

    (warning,) = result.warnings
    assert "2 of 2 checkpoints are reached after that" in warning
    assert "could not be retrieved" not in warning  # not reported as a provider failure


def test_no_horizon_warning_when_everything_is_within_range() -> None:
    result = apply([checkpoint(eta=DEPARTURE + timedelta(hours=5))])[0]

    assert result.warnings == ()


def test_a_gap_inside_the_horizon_is_not_reported_as_a_range_limit() -> None:
    hours = tuple(h for h in full_hours() if h.timestamp != utc_hour(2))
    stub = StubForecasts(hours=lambda c: hours)

    result = apply([checkpoint(eta=DEPARTURE + timedelta(hours=2))], stub)[0]

    assert result.checkpoints[0].data_status == DataStatus.UNAVAILABLE
    assert result.warnings == ()


def test_provider_failure_and_horizon_warnings_are_both_reported() -> None:
    stub = StubForecasts(
        errors={2: ProviderError("Open-Meteo returned an invalid response.")},
        horizon_end=utc_hour(1),
    )
    cps = [
        checkpoint(Coordinate(30 + i * 0.01, -100.0), eta=DEPARTURE + timedelta(hours=3), number=i)
        for i in range(150)
    ]

    warnings = apply(cps, stub)[0].warnings

    assert warnings[0].startswith("Weather forecasts could not be retrieved for 50 of 150")
    assert warnings[1].startswith("Weather forecasts are only available until")
