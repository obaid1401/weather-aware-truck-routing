"""Open-Meteo hourly forecasts.

Values are normalized at this boundary: wind to mph, and hourly precipitation and
snowfall accumulations to inches. Missing values stay `None`; they are never zero-filled.
"""

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx

from shared.http import (
    get_http_client,
    invalid_response_error,
    parse_json,
    raise_for_status,
    send_request,
)
from shared.types import Coordinate
from shared.validation import finite_number

PROVIDER = "Open-Meteo"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"

WIND, PRECIPITATION, SNOWFALL = "wind_speed_10m", "precipitation", "snowfall"
EXPECTED_UNITS = {WIND: "km/h", PRECIPITATION: "mm", SNOWFALL: "cm"}

KMH_PER_MPH = 1.609344
MM_PER_INCH = 25.4
CM_PER_INCH = 2.54

# Open-Meteo serves forecasts up to the end of the 16th day (today included) and rejects
# requests for hours beyond that.
FORECAST_HORIZON_DAYS = 16

# Batches are fetched sequentially on purpose. Open-Meteo counts every location as one API
# call (600 per minute on the free tier), and in measurements concurrent batches were no
# faster than sequential ones (three batches of 100 took about 0.7 s in sequence), while
# making the per-minute limit easier to hit.
MAX_LOCATIONS_PER_REQUEST = 100
HOUR = timedelta(hours=1)


@dataclass(frozen=True)
class ForecastHour:
    timestamp: datetime
    wind_speed_mph: float | None
    precipitation_inches_per_hour: float | None
    snowfall_inches_per_hour: float | None


@dataclass(frozen=True)
class LocationForecast:
    coordinate: Coordinate
    hours: tuple[ForecastHour, ...]


class OpenMeteoForecastService:
    def __init__(
        self,
        client: httpx.Client | None = None,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self._client = client or get_http_client()
        self._clock = clock

    def get_hourly_forecasts(
        self, coordinates: Sequence[Coordinate], start: datetime, end: datetime
    ) -> list[LocationForecast]:
        """Returns hourly forecasts covering `start`..`end`, one result per coordinate in order.

        The window is widened to whole hours and cut off at the provider's forecast
        horizon. Hours beyond the horizon are simply absent from the result.
        """
        if start.tzinfo is None or end.tzinfo is None:
            raise ValueError("start and end must be timezone-aware")
        if end < start:
            raise ValueError("end must not be before start")

        first_hour = _floor_hour(start)
        last_hour = min(_ceil_hour(end), self._horizon_end())
        if first_hour > last_hour:
            return [LocationForecast(coordinate, ()) for coordinate in coordinates]

        forecasts: list[LocationForecast] = []
        for offset in range(0, len(coordinates), MAX_LOCATIONS_PER_REQUEST):
            batch = coordinates[offset : offset + MAX_LOCATIONS_PER_REQUEST]
            forecasts.extend(self._fetch_batch(batch, first_hour, last_hour))
        return forecasts

    def _horizon_end(self) -> datetime:
        today = self._clock().astimezone(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
        return today + timedelta(days=FORECAST_HORIZON_DAYS) - HOUR

    def _fetch_batch(
        self, batch: Sequence[Coordinate], first_hour: datetime, last_hour: datetime
    ) -> list[LocationForecast]:
        response = send_request(
            self._client,
            PROVIDER,
            "GET",
            FORECAST_URL,
            params={
                "latitude": ",".join(f"{c.latitude:.5f}" for c in batch),
                "longitude": ",".join(f"{c.longitude:.5f}" for c in batch),
                "hourly": ",".join(EXPECTED_UNITS),
                "timezone": "GMT",
                "timeformat": "unixtime",
                "start_hour": first_hour.strftime("%Y-%m-%dT%H:%M"),
                "end_hour": last_hour.strftime("%Y-%m-%dT%H:%M"),
            },
        )
        raise_for_status(response, PROVIDER)
        data = parse_json(response, PROVIDER)

        # A single-location request returns an object instead of a list.
        locations = data if isinstance(data, list) else [data]
        if len(locations) != len(batch):
            raise invalid_response_error(
                PROVIDER, f"expected {len(batch)} locations, got {len(locations)}"
            )
        try:
            return [
                LocationForecast(coordinate, _parse_hours(location))
                for coordinate, location in zip(batch, locations, strict=True)
            ]
        except (AttributeError, KeyError, TypeError, ValueError) as exc:
            raise invalid_response_error(PROVIDER, f"malformed forecast: {exc}") from exc


def _parse_hours(location: Any) -> tuple[ForecastHour, ...]:
    units = location.get("hourly_units", {})
    for variable, expected in EXPECTED_UNITS.items():
        if units.get(variable, expected) != expected:
            raise ValueError(f"unexpected unit for {variable}: {units[variable]!r}")

    hourly = location["hourly"]
    times = hourly["time"]
    series = {variable: hourly[variable] for variable in EXPECTED_UNITS}
    if not isinstance(times, list) or any(
        not isinstance(values, list) or len(values) != len(times) for values in series.values()
    ):
        raise ValueError("hourly arrays are missing or have different lengths")

    return tuple(
        ForecastHour(
            timestamp=datetime.fromtimestamp(finite_number(timestamp), UTC),
            wind_speed_mph=_convert(series[WIND][i], KMH_PER_MPH),
            precipitation_inches_per_hour=_convert(series[PRECIPITATION][i], MM_PER_INCH),
            snowfall_inches_per_hour=_convert(series[SNOWFALL][i], CM_PER_INCH),
        )
        for i, timestamp in enumerate(times)
    )


def _convert(value: object, divisor: float) -> float | None:
    if value is None:
        return None
    number = finite_number(value)
    if number < 0:
        raise ValueError(f"negative weather value {number!r}")
    return number / divisor


def _floor_hour(value: datetime) -> datetime:
    return value.astimezone(UTC).replace(minute=0, second=0, microsecond=0)


def _ceil_hour(value: datetime) -> datetime:
    floored = _floor_hour(value)
    return floored if floored == value else floored + HOUR
