"""Types and contracts shared across backend modules.

This module must not depend on Django, DRF, or HTTP concepts. The API layer maps
these types and errors to HTTP responses.
"""

from dataclasses import dataclass
from datetime import datetime
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


@dataclass(frozen=True)
class Checkpoint:
    id: str
    route_id: str
    distance_from_origin_miles: float
    latitude: float
    longitude: float
    estimated_arrival_time: datetime

    @property
    def coordinate(self) -> Coordinate:
        return Coordinate(self.latitude, self.longitude)


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
