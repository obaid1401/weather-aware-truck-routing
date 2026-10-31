"""Checkpoint placement along a route's geometry, by cumulative route distance."""

import bisect
import math

from shared.geo import distance_miles
from shared.types import Route

# Interval multiples this close to the route's end are treated as the destination itself.
DESTINATION_TOLERANCE_MILES = 1e-6


def cumulative_distances(route: Route) -> tuple[float, ...]:
    """Distance from the origin, in miles, at every geometry point.

    Point-to-point distances are measured along the geometry and scaled so the final point
    sits exactly at the provider's route distance. Geometry measurements differ slightly
    from the provider's road distance; scaling keeps checkpoint mileage consistent with
    the route totals while preserving where each point lies along the route.
    """
    _require_positive("route distance", route.distance_miles)
    geometry = route.geometry
    if len(geometry) < 2:
        raise ValueError("route geometry must have at least two points")

    measured = [0.0]
    for previous, current in zip(geometry, geometry[1:], strict=False):
        measured.append(measured[-1] + distance_miles(previous, current))
    if measured[-1] <= 0:
        raise ValueError("route geometry has zero length")

    scale = route.distance_miles / measured[-1]
    distances = [value * scale for value in measured]
    distances[-1] = route.distance_miles
    return tuple(distances)


def checkpoint_distances(total_miles: float, interval_miles: float) -> tuple[float, ...]:
    """Origin (0), each interval multiple before the end, then the destination (total)."""
    _require_positive("total distance", total_miles)
    _require_positive("interval", interval_miles)

    distances = [0.0]
    multiple = 1
    while multiple * interval_miles < total_miles - DESTINATION_TOLERANCE_MILES:
        distances.append(float(multiple * interval_miles))
        multiple += 1
    distances.append(total_miles)
    return tuple(distances)


def locate(distances: tuple[float, ...], target_miles: float) -> tuple[int, float]:
    """Returns `(index, fraction)`: `target_miles` lies `fraction` of the way along the
    geometry segment from point `index` to point `index + 1`."""
    if target_miles <= distances[0]:
        return 0, 0.0
    if target_miles >= distances[-1]:
        return len(distances) - 2, 1.0
    # distances[index] <= target < distances[index + 1], so the segment has positive length.
    index = bisect.bisect_right(distances, target_miles) - 1
    span = distances[index + 1] - distances[index]
    return index, (target_miles - distances[index]) / span


def _require_positive(name: str, value: float) -> None:
    if not (math.isfinite(value) and value > 0):
        raise ValueError(f"{name} must be a positive, finite number, got {value!r}")
