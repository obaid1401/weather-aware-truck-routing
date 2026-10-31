"""Builders for synthetic routes used by the checkpoint tests."""

from collections.abc import Sequence

from shared.geo import distance_miles
from shared.types import Coordinate, Route, RouteStep

# Length of one degree of longitude along the equator.
MILES_PER_DEGREE = distance_miles(Coordinate(0, 0), Coordinate(0, 1))


def make_route(
    points: Sequence[tuple[float, float]],
    *,
    distance_miles: float | None = None,
    duration_seconds: float = 3600.0,
    steps: Sequence[tuple[int, int, float]] = (),
    route_id: str = "route-1",
) -> Route:
    """A route through `(latitude, longitude)` points.

    `distance_miles` defaults to the measured geometry length. Steps are given as
    `(start_index, end_index, duration_seconds)`.
    """
    geometry = tuple(Coordinate(lat, lon) for lat, lon in points)
    if distance_miles is None:
        distance_miles = sum(distance_miles_between(geometry))
    return Route(
        id=route_id,
        label="Route A",
        geometry=geometry,
        distance_miles=distance_miles,
        duration_seconds=duration_seconds,
        steps=tuple(RouteStep(start, end, 0.0, duration) for start, end, duration in steps),
    )


def equator_route(*longitudes: float, **kwargs: object) -> Route:
    return make_route([(0.0, lon) for lon in longitudes], **kwargs)  # type: ignore[arg-type]


def distance_miles_between(geometry: Sequence[Coordinate]) -> list[float]:
    return [distance_miles(a, b) for a, b in zip(geometry, geometry[1:], strict=False)]
