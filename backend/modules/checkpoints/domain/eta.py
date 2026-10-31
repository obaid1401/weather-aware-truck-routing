"""Elapsed travel time along a route, used to estimate checkpoint arrival times.

Preferred: provider step durations, spread across each step's geometry in proportion to
distance. Fallback: route duration in proportion to distance from the origin. Both are
estimates, not live traffic predictions.
"""

import math
from dataclasses import dataclass
from datetime import datetime, timedelta

from shared.datetimes import add_elapsed
from shared.datetimes import require_timezone_aware as shared_require_timezone_aware
from shared.types import Route

# Step durations are used only when they add up to the route duration within this
# tolerance (the larger of the two values).
STEP_DURATION_TOLERANCE_SECONDS = 60.0
STEP_DURATION_TOLERANCE_RATIO = 0.01


@dataclass(frozen=True)
class ElapsedTimes:
    """Elapsed seconds from departure at every geometry point.

    `arrival` is when the truck reaches each point and `departure` is when it leaves. They
    differ only where a step has time but no length (a stop at that point), so the stop's
    time is not spread over the following segment.
    """

    arrival: tuple[float, ...]
    departure: tuple[float, ...]

    def at(self, index: int, fraction: float) -> float:
        """Elapsed seconds at `fraction` of the segment from point `index` to `index + 1`."""
        if fraction == 0:
            return self.arrival[index]
        if fraction == 1:
            return self.arrival[index + 1]
        start = self.departure[index]
        return start + (self.arrival[index + 1] - start) * fraction


def elapsed_times(route: Route, distances: tuple[float, ...]) -> ElapsedTimes:
    """Elapsed times at every geometry point; the destination always equals the route duration.

    `distances` holds the cumulative distance at each geometry point.
    """
    if len(distances) != len(route.geometry):
        raise ValueError("distances must have one value per geometry point")
    if steps_cover_route(route):
        return _from_steps(route, distances)
    elapsed = proportional_elapsed_seconds(route, distances)
    return ElapsedTimes(elapsed, elapsed)


def steps_cover_route(route: Route) -> bool:
    """True when the steps describe the whole route in order, with valid durations that add
    up to the route duration."""
    steps = route.steps
    if not steps or steps[0].start_index != 0 or steps[-1].end_index != len(route.geometry) - 1:
        return False
    if any(
        current.start_index != previous.end_index
        for previous, current in zip(steps, steps[1:], strict=False)
    ):
        return False
    if any(
        step.end_index < step.start_index
        or not math.isfinite(step.duration_seconds)
        or step.duration_seconds < 0
        for step in steps
    ):
        return False
    total = sum(step.duration_seconds for step in steps)
    tolerance = max(
        STEP_DURATION_TOLERANCE_SECONDS, route.duration_seconds * STEP_DURATION_TOLERANCE_RATIO
    )
    return total > 0 and abs(total - route.duration_seconds) <= tolerance


def proportional_elapsed_seconds(route: Route, distances: tuple[float, ...]) -> tuple[float, ...]:
    """Fallback: `route_duration × distance / route_distance` at every point."""
    if not route.distance_miles > 0:
        raise ValueError("route distance must be positive")
    return tuple(route.duration_seconds * d / route.distance_miles for d in distances)


def _from_steps(route: Route, distances: tuple[float, ...]) -> ElapsedTimes:
    arrival = [0.0] * len(distances)
    departure = [0.0] * len(distances)
    clock = 0.0
    for step in route.steps:
        start, end = step.start_index, step.end_index
        if start == end:
            # A step with no length is time spent at a point, such as a stop.
            clock += step.duration_seconds
            departure[start] = clock
            continue
        span = distances[end] - distances[start]
        for index in range(start + 1, end + 1):
            if span > 0:
                fraction = (distances[index] - distances[start]) / span
            else:
                fraction = (index - start) / (end - start)
            arrival[index] = departure[index] = clock + step.duration_seconds * fraction
        clock += step.duration_seconds
    # Time spent at the destination itself (for example an "arrive" maneuver) counts toward
    # arrival, so the destination matches the route duration.
    arrival[-1] = departure[-1] = clock

    # Step durations can differ slightly from the route total; rescale so the destination
    # matches the route duration exactly.
    scale = route.duration_seconds / clock
    return ElapsedTimes(
        tuple(value * scale for value in arrival), tuple(value * scale for value in departure)
    )


def require_timezone_aware(departure_time: datetime) -> None:
    shared_require_timezone_aware(departure_time, "departure_time")


def arrival_time(departure_time: datetime, elapsed_seconds: float) -> datetime:
    """The instant `elapsed_seconds` of real time after departure, in the departure's
    timezone (correct across daylight-saving changes)."""
    require_timezone_aware(departure_time)
    return add_elapsed(departure_time, timedelta(seconds=elapsed_seconds))
