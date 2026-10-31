"""Route risk mileage, distance-weighted average risk, and weather coverage (FR-09).

Segment-risk approximation: each segment between two consecutive checkpoints takes the risk
of its downstream checkpoint (the one the truck reaches at the end of the segment). The
final partial segment ends at the destination checkpoint. Every route mile belongs to
exactly one segment, so no mile is counted twice. The origin checkpoint's risk does not
cover any miles.

Two coverage figures use the same segments. Weather coverage counts miles whose risk is
known, even when some weather values are missing. Complete weather coverage counts only
miles whose downstream checkpoint has all three weather values (`DataStatus.AVAILABLE`).
"""

import math
from collections.abc import Sequence
from itertools import pairwise

from modules.risk.domain.thresholds import RISK_SCORES, SEVERITY_ORDER
from shared.types import Checkpoint, DataStatus, RiskLevel, Route, RouteMetrics

DISTANCE_TOLERANCE_MILES = 1e-6


def route_metrics(route: Route, checkpoints: Sequence[Checkpoint]) -> RouteMetrics:
    """Metrics for `route` from its risk-assessed checkpoints, ordered from origin to
    destination."""
    _validate(route, checkpoints)

    miles = dict.fromkeys(RiskLevel, 0.0)
    complete_miles = incomplete_miles = 0.0
    for upstream, downstream in pairwise(checkpoints):
        segment = downstream.distance_from_origin_miles - upstream.distance_from_origin_miles
        miles[downstream.final_risk] += segment
        if downstream.data_status is DataStatus.AVAILABLE:
            complete_miles += segment
        else:
            incomplete_miles += segment

    known_miles = sum(miles[level] for level in SEVERITY_ORDER)
    total_miles = known_miles + miles[RiskLevel.UNKNOWN]
    average = (
        sum(RISK_SCORES[level] * miles[level] for level in SEVERITY_ORDER) / known_miles
        if known_miles > 0
        else None
    )
    return RouteMetrics(
        distance_miles=route.distance_miles,
        duration_seconds=route.duration_seconds,
        low_miles=miles[RiskLevel.LOW],
        moderate_miles=miles[RiskLevel.MODERATE],
        high_miles=miles[RiskLevel.HIGH],
        severe_miles=miles[RiskLevel.SEVERE],
        no_travel_miles=miles[RiskLevel.NO_TRAVEL],
        unknown_miles=miles[RiskLevel.UNKNOWN],
        average_risk_score=average,
        weather_coverage_percent=_coverage_percent(
            total_miles, covered_miles=known_miles, missing_miles=miles[RiskLevel.UNKNOWN]
        ),
        complete_weather_coverage_percent=_coverage_percent(
            total_miles, covered_miles=complete_miles, missing_miles=incomplete_miles
        ),
    )


def _coverage_percent(total_miles: float, covered_miles: float, missing_miles: float) -> float:
    """Percentage of `total_miles` covered, exact at both ends.

    The covered and total miles are summed in different orders, so dividing them directly
    can give 99.99999999999999% for a fully covered route. Full and zero coverage are
    therefore decided by whether any miles are missing or covered; partial coverage is
    computed from the missing miles.
    """
    if missing_miles == 0:
        return 100.0
    if covered_miles == 0:
        return 0.0
    return min(100.0, max(0.0, 100 * (total_miles - missing_miles) / total_miles))


def _validate(route: Route, checkpoints: Sequence[Checkpoint]) -> None:
    if len(checkpoints) < 2:
        raise ValueError("a route needs at least an origin and a destination checkpoint")
    if any(checkpoint.route_id != route.id for checkpoint in checkpoints):
        raise ValueError(f"all checkpoints must belong to route {route.id!r}")
    distances = [checkpoint.distance_from_origin_miles for checkpoint in checkpoints]
    if distances[0] != 0:
        raise ValueError("the first checkpoint must be the origin (mile 0)")
    if any(later < earlier for earlier, later in pairwise(distances)):
        raise ValueError("checkpoints must be ordered by distance from the origin")
    if not math.isclose(distances[-1], route.distance_miles, abs_tol=DISTANCE_TOLERANCE_MILES):
        raise ValueError("the last checkpoint must be the destination")
