"""Applies Open-Meteo forecasts to checkpoints: ETA-matched conditions and the 0-48 h series."""

import dataclasses
import logging
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta

from modules.weather.services.forecast_matching import (
    data_status,
    match_forecast,
    nearest_forecast_hour,
)
from modules.weather.services.open_meteo import (
    FORECAST_HORIZON_DAYS,
    MAX_LOCATIONS_PER_REQUEST,
    ForecastHour,
    OpenMeteoForecastService,
)
from shared.datetimes import add_elapsed, require_timezone_aware
from shared.geo import distance_miles
from shared.types import (
    AnalysisError,
    Checkpoint,
    Coordinate,
    HourlyForecast,
    ProviderRateLimitError,
)

logger = logging.getLogger(__name__)

SERIES_HOURS = 48

# A checkpoint within this distance of a location that is already being fetched shares
# that location's forecast. This removes duplicates such as the origin every route starts
# from, or checkpoints on a stretch several routes have in common. Open-Meteo's model grid
# is kilometres wide, so the forecast is the same at that distance.
SHARED_LOCATION_MILES = 0.1


@dataclass(frozen=True)
class CheckpointWeatherResult:
    checkpoints: tuple[Checkpoint, ...]
    warnings: tuple[str, ...]


class CheckpointWeatherService:
    def __init__(self, forecasts: OpenMeteoForecastService | None = None) -> None:
        self._forecasts = forecasts or OpenMeteoForecastService()

    def apply(
        self, checkpoints: Sequence[Checkpoint], departure_time: datetime
    ) -> CheckpointWeatherResult:
        """Returns the checkpoints (same order) with weather matched to each ETA and an hourly
        series for 0-48 hours after departure.

        Locations are fetched in sequential batches. If some batches fail, their checkpoints
        are left UNAVAILABLE and a warning is returned; if every batch fails, the first
        error is raised.
        """
        require_timezone_aware(departure_time, "departure_time")
        if not checkpoints:
            return CheckpointWeatherResult((), ())

        locations, location_of = _shared_locations(checkpoints)
        end = max(
            add_elapsed(departure_time, timedelta(hours=SERIES_HOURS)),
            *(checkpoint.estimated_arrival_time for checkpoint in checkpoints),
        )
        hours_by_location, failures, failed_count = self._fetch(locations, departure_time, end)

        updated = tuple(
            _with_weather(checkpoint, hours_by_location.get(location, {}), departure_time)
            for checkpoint, location in zip(checkpoints, location_of, strict=True)
        )
        warnings = []
        if failures:
            warnings.append(
                f"Weather forecasts could not be retrieved for {failed_count} of "
                f"{len(locations)} checkpoint locations ({failures[0].message.rstrip('.')}). "
                "Conditions there are UNKNOWN."
            )
        horizon_warning = _beyond_horizon_warning(updated, self._forecasts.forecast_horizon_end())
        if horizon_warning:
            warnings.append(horizon_warning)
        return CheckpointWeatherResult(updated, tuple(warnings))

    def _fetch(
        self, locations: list[Coordinate], start: datetime, end: datetime
    ) -> tuple[dict[int, dict[datetime, ForecastHour]], list[AnalysisError], int]:
        """Hours by location index, the batch errors, and how many locations failed."""
        hours_by_location: dict[int, dict[datetime, ForecastHour]] = {}
        failures: list[AnalysisError] = []
        failed_count = 0

        # Batches run sequentially on purpose. Open-Meteo counts every location as one API
        # call (600 per minute on the free tier); concurrent batches were measured to be no
        # faster and only reach that limit sooner. After a rate-limit error the remaining
        # batches are skipped rather than sent into the same limit.
        for offset in range(0, len(locations), MAX_LOCATIONS_PER_REQUEST):
            batch = locations[offset : offset + MAX_LOCATIONS_PER_REQUEST]
            if any(isinstance(failure, ProviderRateLimitError) for failure in failures):
                failed_count += len(batch)
                continue
            try:
                forecasts = self._forecasts.get_hourly_forecasts(batch, start, end)
            except AnalysisError as error:
                logger.warning("Weather batch of %d locations failed: %s", len(batch), error)
                failures.append(error)
                failed_count += len(batch)
                continue
            for index, forecast in enumerate(forecasts, start=offset):
                hours_by_location[index] = {hour.timestamp: hour for hour in forecast.hours}

        if failures and not hours_by_location:
            raise failures[0]
        return hours_by_location, failures, failed_count


def _beyond_horizon_warning(checkpoints: Sequence[Checkpoint], horizon_end: datetime) -> str | None:
    """A warning when checkpoint ETAs, or forecast-slider hours, fall after the last hour the
    provider forecasts. Those values are UNKNOWN because no forecast exists yet, not because
    a request failed."""
    limit = f"{horizon_end:%Y-%m-%d %H:%M} UTC"
    late = sum(nearest_forecast_hour(cp.estimated_arrival_time) > horizon_end for cp in checkpoints)
    if late:
        return (
            f"Weather forecasts are only available until {limit} (about "
            f"{FORECAST_HORIZON_DAYS} days ahead). {late} of {len(checkpoints)} checkpoints "
            "are reached after that, so their weather and risk are UNKNOWN."
        )
    if any(
        nearest_forecast_hour(entry.target_time) > horizon_end
        for cp in checkpoints
        for entry in cp.hourly_forecasts
    ):
        return (
            f"Weather forecasts are only available until {limit}. Forecast slider hours "
            "after that are UNKNOWN."
        )
    return None


def _shared_locations(checkpoints: Sequence[Checkpoint]) -> tuple[list[Coordinate], list[int]]:
    """The distinct locations to fetch, and the index of each checkpoint's location.

    A checkpoint uses the nearest already-chosen location within SHARED_LOCATION_MILES;
    otherwise its exact coordinate becomes a new location.
    """
    locations: list[Coordinate] = []
    location_of: list[int] = []
    for checkpoint in checkpoints:
        coordinate = checkpoint.coordinate
        nearest_index, nearest_distance = None, 0.0
        for index, location in enumerate(locations):
            distance = distance_miles(coordinate, location)
            # Strictly closer only, so the earlier location wins a tie.
            if distance <= SHARED_LOCATION_MILES and (
                nearest_index is None or distance < nearest_distance
            ):
                nearest_index, nearest_distance = index, distance
        if nearest_index is None:
            locations.append(coordinate)
            nearest_index = len(locations) - 1
        location_of.append(nearest_index)
    return locations, location_of


def _with_weather(
    checkpoint: Checkpoint, hours: dict[datetime, ForecastHour], departure_time: datetime
) -> Checkpoint:
    matched = match_forecast(hours, checkpoint.estimated_arrival_time)
    series = []
    for offset in range(SERIES_HOURS + 1):
        target = add_elapsed(departure_time, timedelta(hours=offset))
        hour = match_forecast(hours, target)
        series.append(
            HourlyForecast(
                hour_offset=offset,
                target_time=target,
                forecast_timestamp=hour.timestamp if hour else None,
                wind_speed_mph=hour.wind_speed_mph if hour else None,
                precipitation_inches_per_hour=hour.precipitation_inches_per_hour if hour else None,
                snowfall_inches_per_hour=hour.snowfall_inches_per_hour if hour else None,
                data_status=data_status(hour),
            )
        )
    return dataclasses.replace(
        checkpoint,
        forecast_timestamp=matched.timestamp if matched else None,
        wind_speed_mph=matched.wind_speed_mph if matched else None,
        precipitation_inches_per_hour=matched.precipitation_inches_per_hour if matched else None,
        snowfall_inches_per_hour=matched.snowfall_inches_per_hour if matched else None,
        data_status=data_status(matched),
        hourly_forecasts=tuple(series),
    )
