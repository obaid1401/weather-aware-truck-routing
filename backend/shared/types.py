"""Types and contracts shared across backend modules.

This module must not depend on Django, DRF, or HTTP concepts. The API layer maps
these types and errors to HTTP responses.
"""

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Any, NamedTuple

CHECKPOINT_INTERVAL_CHOICES_MILES: tuple[int, ...] = (10, 25, 50)
DEFAULT_CHECKPOINT_INTERVAL_MILES = 25


class Coordinate(NamedTuple):
    latitude: float
    longitude: float


@dataclass(frozen=True)
class TripInput:
    origin: str
    destination: str
    departure_time: datetime
    load_weight_lbs: float
    checkpoint_interval_miles: int = DEFAULT_CHECKPOINT_INTERVAL_MILES


@dataclass(frozen=True)
class Location:
    label: str
    latitude: float
    longitude: float

    @property
    def coordinate(self) -> Coordinate:
        return Coordinate(self.latitude, self.longitude)


@dataclass(frozen=True)
class RouteStep:
    """A provider step covering `geometry[start_index : end_index + 1]` of its route."""

    start_index: int
    end_index: int
    distance_miles: float
    duration_seconds: float


@dataclass(frozen=True)
class Route:
    id: str
    label: str
    geometry: tuple[Coordinate, ...]
    distance_miles: float
    duration_seconds: float
    steps: tuple[RouteStep, ...]


class DataStatus(StrEnum):
    """How many of the three weather values (wind, precipitation, snowfall) are known."""

    AVAILABLE = "AVAILABLE"  # all three
    PARTIAL = "PARTIAL"  # some, but not all
    UNAVAILABLE = "UNAVAILABLE"  # none; conditions are unknown


class RiskLevel(StrEnum):
    """Risk categories. Severity order and scores are defined in the risk module; never
    compare these values alphabetically."""

    LOW = "LOW"
    MODERATE = "MODERATE"
    HIGH = "HIGH"
    SEVERE = "SEVERE"
    NO_TRAVEL = "NO_TRAVEL"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class HourlyForecast:
    """Forecast conditions at a checkpoint location `hour_offset` hours after departure.

    Used only for the forecast slider. Missing values are `None`, never zero. Risks stay
    UNKNOWN until the risk module assesses the entry.
    """

    hour_offset: int
    target_time: datetime
    forecast_timestamp: datetime | None
    wind_speed_mph: float | None
    precipitation_inches_per_hour: float | None
    snowfall_inches_per_hour: float | None
    data_status: DataStatus
    wind_risk: RiskLevel = RiskLevel.UNKNOWN
    rain_risk: RiskLevel = RiskLevel.UNKNOWN
    snow_risk: RiskLevel = RiskLevel.UNKNOWN
    final_risk: RiskLevel = RiskLevel.UNKNOWN


@dataclass(frozen=True)
class Checkpoint:
    """A point along a route. Weather fields hold the forecast matched to the checkpoint's
    estimated arrival time; they stay `None` (and UNAVAILABLE) until weather is applied or
    when the forecast is missing. Risk fields stay UNKNOWN until risk is assessed."""

    id: str
    route_id: str
    distance_from_origin_miles: float
    latitude: float
    longitude: float
    estimated_arrival_time: datetime
    forecast_timestamp: datetime | None = None
    wind_speed_mph: float | None = None
    precipitation_inches_per_hour: float | None = None
    snowfall_inches_per_hour: float | None = None
    data_status: DataStatus = DataStatus.UNAVAILABLE
    hourly_forecasts: tuple[HourlyForecast, ...] = ()
    wind_risk: RiskLevel = RiskLevel.UNKNOWN
    rain_risk: RiskLevel = RiskLevel.UNKNOWN
    snow_risk: RiskLevel = RiskLevel.UNKNOWN
    final_risk: RiskLevel = RiskLevel.UNKNOWN
    warnings: tuple[str, ...] = ()

    @property
    def coordinate(self) -> Coordinate:
        return Coordinate(self.latitude, self.longitude)


@dataclass(frozen=True)
class RouteMetrics:
    """Risk mileage for a route. Each segment between consecutive checkpoints takes the
    risk of its downstream checkpoint; the risk miles add up to `distance_miles`."""

    distance_miles: float
    duration_seconds: float
    low_miles: float
    moderate_miles: float
    high_miles: float
    severe_miles: float
    no_travel_miles: float
    unknown_miles: float
    average_risk_score: float | None  # None when no mile has a known risk
    # Percentage of route miles whose segment has a known final risk (some factors may be
    # missing).
    weather_coverage_percent: float
    # Percentage of route miles whose segment has all three weather values available.
    complete_weather_coverage_percent: float


@dataclass(frozen=True)
class Recommendation:
    """Route ranking (FR-10). `ranking_reasons[i]` explains the route at
    `ranked_route_ids[i]`; the first entry explains why the recommended route was chosen."""

    recommended_route_id: str
    ranked_route_ids: tuple[str, ...]
    ranking_reasons: tuple[str, ...]
    warnings: tuple[str, ...]


# Errors


class AnalysisError(Exception):
    """Base class for expected failures that are reported to the client."""

    code = "ANALYSIS_ERROR"
    default_message = "The trip analysis failed."

    def __init__(
        self,
        message: str | None = None,
        details: dict[str, Any] | None = None,
        code: str | None = None,
    ) -> None:
        self.message = message or self.default_message
        self.details = details or {}
        if code is not None:
            self.code = code
        super().__init__(self.message)


class GeocodingAmbiguousError(AnalysisError):
    code = "GEOCODING_AMBIGUOUS"

    def __init__(self, field: str, candidates: list[Location]) -> None:
        super().__init__(
            message=f"The {field} address matches multiple locations.",
            details={
                "field": field,
                "candidates": [
                    {
                        "label": candidate.label,
                        "latitude": candidate.latitude,
                        "longitude": candidate.longitude,
                    }
                    for candidate in candidates
                ],
            },
        )


class GeocodingNotFoundError(AnalysisError):
    code = "GEOCODING_NOT_FOUND"

    def __init__(self, field: str) -> None:
        super().__init__(
            message=f"No location was found for the {field} address.",
            details={"field": field},
        )


class NoRouteFoundError(AnalysisError):
    code = "ROUTE_NOT_FOUND"
    default_message = "No truck route was found between the origin and destination."


class ProviderError(AnalysisError):
    code = "PROVIDER_ERROR"
    default_message = "An external provider returned an error or an invalid response."


class ProviderRateLimitError(AnalysisError):
    code = "PROVIDER_RATE_LIMITED"
    default_message = "An external provider's request limit was reached. Try again later."


class ProviderUnavailableError(AnalysisError):
    code = "PROVIDER_UNAVAILABLE"
    default_message = "An external provider is temporarily unavailable. Try again later."


class ProviderTimeoutError(AnalysisError):
    code = "PROVIDER_TIMEOUT"
    default_message = "An external provider did not respond in time."
