"""OpenRouteService geocoding (Pelias `/geocode/search`)."""

from dataclasses import dataclass
from typing import Any

import httpx
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

from shared.geo import coordinate_from_lon_lat, distance_miles
from shared.http import (
    get_http_client,
    invalid_response_error,
    parse_json,
    raise_for_status,
    send_request,
)
from shared.types import GeocodingAmbiguousError, GeocodingNotFoundError, Location
from shared.validation import finite_number

PROVIDER = "OpenRouteService"
SEARCH_URL = "https://api.openrouteservice.org/geocode/search"
RESULT_SIZE = 10
MAX_AMBIGUOUS_CANDIDATES = 5

# Approved ambiguity rule (docs/requirements.md FR-03). A result is plausible when its
# confidence is within CONFIDENCE_MARGIN of the best confidence. Plausible results are
# materially different when they are more than DISTINCT_LOCATION_MILES apart. More than
# one materially different plausible location means the address is ambiguous. Only
# plausible results can be selected.
CONFIDENCE_MARGIN = 0.1
DISTINCT_LOCATION_MILES = 25.0


@dataclass(frozen=True)
class _Candidate:
    location: Location
    confidence: float


class OrsGeocodingService:
    def __init__(self, client: httpx.Client | None = None, api_key: str | None = None) -> None:
        self._client = client or get_http_client()
        self._api_key = api_key if api_key is not None else settings.ORS_API_KEY
        if not self._api_key:
            raise ImproperlyConfigured("ORS_API_KEY is not set.")

    def geocode(self, query: str, field: str) -> Location:
        """Resolves `query` to one location. `field` names the input in error details."""
        response = send_request(
            self._client,
            PROVIDER,
            "GET",
            SEARCH_URL,
            params={"text": query, "size": RESULT_SIZE},
            headers={"Authorization": self._api_key},
        )
        raise_for_status(response, PROVIDER)
        candidates = _parse_candidates(parse_json(response, PROVIDER))
        if not candidates:
            raise GeocodingNotFoundError(field)
        return _resolve(candidates, field)


def _parse_candidates(data: Any) -> list[_Candidate]:
    try:
        features = data["features"]
        if not isinstance(features, list):
            raise TypeError("features is not a list")
        candidates = []
        for feature in features:
            label = feature["properties"]["label"]
            if not isinstance(label, str) or not label.strip():
                raise ValueError(f"invalid label {label!r}")
            coordinate = coordinate_from_lon_lat(feature["geometry"]["coordinates"])
            candidates.append(
                _Candidate(
                    location=Location(label, coordinate.latitude, coordinate.longitude),
                    confidence=finite_number(feature["properties"]["confidence"]),
                )
            )
        return candidates
    except (KeyError, TypeError, ValueError) as exc:
        raise invalid_response_error(PROVIDER, f"malformed geocoding result: {exc}") from exc


def _resolve(candidates: list[_Candidate], field: str) -> Location:
    # The tolerance keeps a difference of exactly CONFIDENCE_MARGIN (e.g. 0.8 vs 0.7)
    # plausible despite floating-point rounding.
    threshold = max(c.confidence for c in candidates) - CONFIDENCE_MARGIN - 1e-9
    plausible = [c for c in candidates if c.confidence >= threshold]

    distinct: list[_Candidate] = []
    for candidate in plausible:
        if all(not _same_place(candidate, kept) for kept in distinct):
            distinct.append(candidate)

    if len(distinct) > 1:
        raise GeocodingAmbiguousError(
            field, [c.location for c in distinct[:MAX_AMBIGUOUS_CANDIDATES]]
        )

    # The first plausible result in provider order. Lower-confidence results are never
    # selected, even when they are nearby.
    return distinct[0].location


def _same_place(a: _Candidate, b: _Candidate) -> bool:
    return distance_miles(a.location.coordinate, b.location.coordinate) <= DISTINCT_LOCATION_MILES
