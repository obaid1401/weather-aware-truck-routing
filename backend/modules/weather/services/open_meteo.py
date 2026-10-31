"""Open-Meteo hourly forecasts.

Values are normalized at this boundary: wind to mph, and hourly precipitation and
snowfall accumulations to inches. Missing values stay `None`; they are never zero-filled.
"""

import logging
import re
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

logger = logging.getLogger(__name__)

PROVIDER = "Open-Meteo"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"

WIND, PRECIPITATION, SNOWFALL = "wind_speed_10m", "precipitation", "snowfall"
EXPECTED_UNITS = {WIND: "km/h", PRECIPITATION: "mm", SNOWFALL: "cm"}
TIME_UNIT = "unixtime"

KMH_PER_MPH = 1.609344
MM_PER_INCH = 25.4
CM_PER_INCH = 2.54

# Open-Meteo serves forecasts up to the end of the 16th day (today included) and rejects
# requests for hours beyond that with HTTP 400, for example:
# "Parameter 'end_hour' is out of allowed range from 2026-07-30 to 2026-11-15".
FORECAST_HORIZON_DAYS = 16
OUT_OF_RANGE = re.compile(
    r"'(?:start_hour|end_hour)' is out of allowed range from \d{4}-\d{2}-\d{2} "
    r"to (\d{4}-\d{2}-\d{2})"
)

# Keeps the request URL short. Larger sets are split into batches by the caller
# (see checkpoint_weather.py).
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

        Makes one provider request (two if the provider's forecast range ends earlier than
        expected), for up to MAX_LOCATIONS_PER_REQUEST coordinates. The window is widened to
        whole hours and cut off at the provider's forecast horizon. Hours beyond the horizon
        are simply absent from the result.
        """
        if start.tzinfo is None or end.tzinfo is None:
            raise ValueError("start and end must be timezone-aware")
        if end < start:
            raise ValueError("end must not be before start")
        if len(coordinates) > MAX_LOCATIONS_PER_REQUEST:
            raise ValueError(f"at most {MAX_LOCATIONS_PER_REQUEST} coordinates per request")

        first_hour = _floor_hour(start)
        last_hour = min(_ceil_hour(end), self._horizon_end())
        if not coordinates or first_hour > last_hour:
            return _no_hours(coordinates)

        response = self._request(coordinates, first_hour, last_hour)

        # Our horizon comes from our own clock. If the provider's range ends earlier (for
        # example just after UTC midnight), it rejects the request; retry once within its
        # range so the available hours are kept and later hours stay unavailable.
        allowed_end = _allowed_end_hour(response)
        if allowed_end is not None and allowed_end < last_hour:
            if first_hour > allowed_end:
                return _no_hours(coordinates)
            logger.warning(
                "%s forecast range ends at %s; retrying with a shorter window.",
                PROVIDER,
                allowed_end.isoformat(),
            )
            response = self._request(coordinates, first_hour, allowed_end)
        return self._parse(response, coordinates)

    def _horizon_end(self) -> datetime:
        today = self._clock().astimezone(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
        return today + timedelta(days=FORECAST_HORIZON_DAYS) - HOUR

    def _request(
        self, batch: Sequence[Coordinate], first_hour: datetime, last_hour: datetime
    ) -> httpx.Response:
        return send_request(
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

    def _parse(
        self, response: httpx.Response, batch: Sequence[Coordinate]
    ) -> list[LocationForecast]:
        raise_for_status(response, PROVIDER)
        data = parse_json(response, PROVIDER)

        # A single-location request returns an object instead of a list.
        locations = data if isinstance(data, list) else [data]
        if len(locations) != len(batch):
            raise invalid_response_error(
                PROVIDER, f"expected {len(batch)} locations, got {len(locations)}"
            )
        try:
            forecasts = []
            for index, (coordinate, location) in enumerate(zip(batch, locations, strict=True)):
                _check_location_id(location, index)
                forecasts.append(LocationForecast(coordinate, _parse_hours(location)))
            return forecasts
        except (AttributeError, KeyError, TypeError, ValueError) as exc:
            raise invalid_response_error(PROVIDER, f"malformed forecast: {exc}") from exc


def _no_hours(coordinates: Sequence[Coordinate]) -> list[LocationForecast]:
    return [LocationForecast(coordinate, ()) for coordinate in coordinates]


def _allowed_end_hour(response: httpx.Response) -> datetime | None:
    """The last hour Open-Meteo allows (23:00 UTC on its maximum date) when `response` is
    an out-of-range error; None for any other response or an unparseable message."""
    if response.status_code != 400:
        return None
    try:
        reason = response.json()["reason"]
    except (ValueError, KeyError, TypeError):
        return None
    match = OUT_OF_RANGE.search(reason) if isinstance(reason, str) else None
    if match is None:
        return None
    try:
        last_day = datetime.strptime(match.group(1), "%Y-%m-%d").replace(tzinfo=UTC)
    except ValueError:
        return None
    return last_day + timedelta(hours=23)


def _check_location_id(location: Any, index: int) -> None:
    """Results must be in request order. Open-Meteo labels multi-location results with
    `location_id` (the request position); the first result may omit it."""
    location_id = location.get("location_id", index)
    if isinstance(location_id, bool) or location_id != index:
        raise ValueError(f"result {index} has location_id {location_id!r}")


def _parse_hours(location: Any) -> tuple[ForecastHour, ...]:
    units = location["hourly_units"]
    if units.get("time") != TIME_UNIT:
        raise ValueError(f"unexpected time format: {units.get('time')!r}")
    for variable, expected in EXPECTED_UNITS.items():
        if units.get(variable) != expected:
            raise ValueError(f"missing or unexpected unit for {variable}: {units.get(variable)!r}")

    hourly = location["hourly"]
    times = hourly["time"]
    series = {variable: hourly[variable] for variable in EXPECTED_UNITS}
    if not isinstance(times, list) or any(
        not isinstance(values, list) or len(values) != len(times) for values in series.values()
    ):
        raise ValueError("hourly arrays are missing or have different lengths")

    timestamps = [_parse_timestamp(value) for value in times]
    if any(later <= earlier for earlier, later in zip(timestamps, timestamps[1:], strict=False)):
        raise ValueError("hourly timestamps are duplicated or out of order")

    return tuple(
        ForecastHour(
            timestamp=timestamp,
            wind_speed_mph=_convert(series[WIND][i], KMH_PER_MPH),
            precipitation_inches_per_hour=_convert(series[PRECIPITATION][i], MM_PER_INCH),
            snowfall_inches_per_hour=_convert(series[SNOWFALL][i], CM_PER_INCH),
        )
        for i, timestamp in enumerate(timestamps)
    )


def _parse_timestamp(value: object) -> datetime:
    """A Unix timestamp on a whole UTC hour."""
    seconds = finite_number(value)
    if seconds % 3600:
        raise ValueError(f"timestamp {value!r} is not on a whole hour")
    return datetime.fromtimestamp(seconds, UTC)


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
