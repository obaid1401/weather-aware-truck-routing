"""OpenRouteService geocoding (Pelias `/geocode/search`) and place suggestions
(`/geocode/autocomplete`)."""

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
PROVIDER = "OpenRouteService"

SEARCH_URL = "https://api.heigit.org/pelias/v1/search"
AUTOCOMPLETE_URL = "https://api.heigit.org/pelias/v1/autocomplete"
RESULT_SIZE = 10
# Suggestions shown while the user types an address.
SUGGESTION_SIZE = 5
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

    def suggest(self, query: str) -> list[Location]:
        """Up to SUGGESTION_SIZE places matching partly typed `query`, in provider order, with
        repeated labels removed. An empty list when nothing matches."""
        response = send_request(
            self._client,
            PROVIDER,
            "GET",
            AUTOCOMPLETE_URL,
            params={"text": query, "size": SUGGESTION_SIZE},
            headers={"Authorization": self._api_key},
        )
        raise_for_status(response, PROVIDER)
        try:
            features = _features(parse_json(response, PROVIDER))
            locations = [_location(feature) for feature in features]
        except (KeyError, TypeError, ValueError) as exc:
            raise invalid_response_error(PROVIDER, f"malformed suggestion: {exc}") from exc

        unique: dict[str, Location] = {}
        for location in locations:
            unique.setdefault(location.label, location)
        return list(unique.values())[:SUGGESTION_SIZE]


def _parse_candidates(data: Any) -> list[_Candidate]:
    try:
        return [
            _Candidate(
                location=_location(feature),
                confidence=finite_number(feature["properties"]["confidence"]),
            )
            for feature in _features(data)
        ]
    except (KeyError, TypeError, ValueError) as exc:
        raise invalid_response_error(PROVIDER, f"malformed geocoding result: {exc}") from exc


def _features(data: Any) -> list[Any]:
    features = data["features"]
    if not isinstance(features, list):
        raise TypeError("features is not a list")
    return features


def _location(feature: Any) -> Location:
    """The labelled location of one GeoJSON feature (search and autocomplete results)."""
    label = feature["properties"]["label"]
    if not isinstance(label, str) or not label.strip():
        raise ValueError(f"invalid label {label!r}")
    coordinate = coordinate_from_lon_lat(feature["geometry"]["coordinates"])
    return Location(label, coordinate.latitude, coordinate.longitude)


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
