"""Matching forecast hours to target times (checkpoint ETAs or slider hours)."""

from collections.abc import Mapping
from datetime import UTC, datetime, timedelta

from modules.weather.services.open_meteo import ForecastHour
from shared.types import DataStatus

HOUR = timedelta(hours=1)


def nearest_forecast_hour(target: datetime) -> datetime:
    """The whole UTC hour closest to `target`; the earlier hour when both are equally close."""
    if target.tzinfo is None or target.utcoffset() is None:
        raise ValueError("target must be timezone-aware")
    floored = target.astimezone(UTC).replace(minute=0, second=0, microsecond=0)
    if target - floored <= floored + HOUR - target:
        return floored
    return floored + HOUR


def match_forecast(hours: Mapping[datetime, ForecastHour], target: datetime) -> ForecastHour | None:
    """The forecast for the hour nearest `target`, or None if that hour was not provided.

    Other hours are never substituted: a gap or the end of the forecast horizon means the
    conditions at `target` are unknown.
    """
    return hours.get(nearest_forecast_hour(target))


def data_status(hour: ForecastHour | None) -> DataStatus:
    if hour is None:
        return DataStatus.UNAVAILABLE
    values = (
        hour.wind_speed_mph,
        hour.precipitation_inches_per_hour,
        hour.snowfall_inches_per_hour,
    )
    known = sum(value is not None for value in values)
    if known == len(values):
        return DataStatus.AVAILABLE
    return DataStatus.PARTIAL if known else DataStatus.UNAVAILABLE
