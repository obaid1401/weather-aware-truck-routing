from datetime import UTC, datetime, timedelta, timezone

import pytest

from modules.checkpoints.domain.eta import (
    arrival_time,
    elapsed_times,
    proportional_elapsed_seconds,
    steps_cover_route,
)
from modules.checkpoints.domain.placement import cumulative_distances
from modules.checkpoints.tests.routes import equator_route


def elapsed(route: object) -> tuple[float, ...]:
    """Arrival seconds at each geometry point."""
    times = elapsed_times(route, cumulative_distances(route))  # type: ignore[arg-type]
    return times.arrival


# Proportional fallback


def test_proportional_fallback_without_steps() -> None:
    route = equator_route(0.0, 1.0, 2.0, duration_seconds=4000.0)

    assert elapsed(route) == pytest.approx((0.0, 2000.0, 4000.0))


# Step-based ETA


def test_step_durations_set_the_pace_of_each_part_of_the_route() -> None:
    # Two equal-length halves; the second half is three times slower.
    route = equator_route(
        0.0, 1.0, 2.0, duration_seconds=4000.0, steps=[(0, 1, 1000.0), (1, 2, 3000.0)]
    )

    assert steps_cover_route(route)
    assert elapsed(route) == pytest.approx((0.0, 1000.0, 4000.0))


def test_time_within_a_step_is_spread_by_distance() -> None:
    # One step over unevenly spaced points: 1 degree, then 2 degrees.
    route = equator_route(0.0, 1.0, 3.0, duration_seconds=3000.0, steps=[(0, 2, 3000.0)])

    assert elapsed(route) == pytest.approx((0.0, 1000.0, 3000.0))


def test_zero_length_arrive_step_is_allowed() -> None:
    route = equator_route(
        0.0, 1.0, 2.0, duration_seconds=2000.0, steps=[(0, 2, 2000.0), (2, 2, 0.0)]
    )

    assert elapsed(route) == pytest.approx((0.0, 1000.0, 2000.0))


def test_time_in_a_zero_length_final_step_counts_toward_arrival() -> None:
    route = equator_route(
        0.0, 1.0, 2.0, duration_seconds=1000.0, steps=[(0, 2, 900.0), (2, 2, 100.0)]
    )

    assert elapsed(route) == pytest.approx((0.0, 450.0, 1000.0))


def test_step_over_duplicate_points_spreads_time_by_index() -> None:
    route = equator_route(
        0.0,
        1.0,
        1.0,
        1.0,
        2.0,
        duration_seconds=1200.0,
        steps=[(0, 1, 500.0), (1, 3, 200.0), (3, 4, 500.0)],
    )

    assert elapsed(route) == pytest.approx((0.0, 500.0, 600.0, 700.0, 1200.0))


def test_small_step_total_differences_are_rescaled_to_the_route_duration() -> None:
    # Steps add up to 3990 s; the route says 4000 s (within 1%).
    route = equator_route(
        0.0, 1.0, 2.0, duration_seconds=4000.0, steps=[(0, 1, 1995.0), (1, 2, 1995.0)]
    )

    result = elapsed(route)

    assert result[-1] == 4000.0
    assert result[1] == pytest.approx(2000.0)


@pytest.mark.parametrize(
    "steps",
    [
        [],
        [(1, 2, 4000.0)],  # does not start at the origin
        [(0, 1, 2000.0)],  # does not reach the destination
        [(0, 1, 1000.0), (2, 2, 3000.0)],  # gap between steps
        [(0, 1, 1000.0), (1, 2, 2000.0)],  # 3000 s vs 4000 s: beyond tolerance
        [(0, 1, 0.0), (1, 2, 0.0)],  # no durations
        [(0, 2, 60.0), (2, 1, 10.0), (1, 2, 3930.0)],  # reversed step
        [(0, 1, 4100.0), (1, 2, -100.0)],  # negative duration with a valid total
        [(0, 1, float("nan")), (1, 2, 4000.0)],
        [(0, 1, float("inf")), (1, 2, 4000.0)],
    ],
)
def test_unusable_steps_fall_back_to_proportional(steps: list[tuple[int, int, float]]) -> None:
    route = equator_route(0.0, 1.0, 2.0, duration_seconds=4000.0, steps=steps)
    distances = cumulative_distances(route)

    assert not steps_cover_route(route)
    times = elapsed_times(route, distances)
    assert times.arrival == times.departure == proportional_elapsed_seconds(route, distances)


@pytest.mark.parametrize(("step_total", "usable"), [(1059.0, True), (1061.0, False)])
def test_short_routes_allow_a_60_second_difference(step_total: float, usable: bool) -> None:
    route = equator_route(0.0, 1.0, duration_seconds=1000.0, steps=[(0, 1, step_total)])

    assert steps_cover_route(route) is usable


def test_distances_must_match_the_geometry() -> None:
    route = equator_route(0.0, 1.0, 2.0)

    with pytest.raises(ValueError):
        elapsed_times(route, (0.0, 1.0))


def test_proportional_fallback_requires_a_positive_distance() -> None:
    route = equator_route(0.0, 1.0, distance_miles=0.0)

    with pytest.raises(ValueError):
        proportional_elapsed_seconds(route, (0.0, 0.0))


# Stops (steps with time but no length)


def test_mid_route_stop_is_not_spread_over_the_next_segment() -> None:
    # 600 s to point 1, a 300 s stop there, then 600 s to point 2.
    route = equator_route(
        0.0,
        1.0,
        2.0,
        duration_seconds=1500.0,
        steps=[(0, 1, 600.0), (1, 1, 300.0), (1, 2, 600.0)],
    )

    times = elapsed_times(route, cumulative_distances(route))

    assert times.arrival == pytest.approx((0.0, 600.0, 1500.0))
    assert times.departure == pytest.approx((0.0, 900.0, 1500.0))
    assert times.at(1, 0.0) == pytest.approx(600.0)  # arriving at the stop
    assert times.at(1, 0.1) == pytest.approx(960.0)  # after the whole stop, plus 60 s of driving
    assert times.at(0, 0.5) == pytest.approx(300.0)  # before the stop: unaffected


def test_stop_at_the_origin_delays_everything_after_it() -> None:
    route = equator_route(0.0, 1.0, duration_seconds=1000.0, steps=[(0, 0, 200.0), (0, 1, 800.0)])

    times = elapsed_times(route, cumulative_distances(route))

    assert times.at(0, 0.0) == 0.0
    assert times.at(0, 0.5) == pytest.approx(600.0)
    assert times.at(0, 1.0) == pytest.approx(1000.0)


# Arrival time


def test_arrival_time_keeps_the_departure_timezone() -> None:
    mountain = timezone(timedelta(hours=-7))
    departure = datetime(2026, 11, 5, 8, 0, tzinfo=mountain)

    arrival = arrival_time(departure, 5400.5)

    assert arrival == datetime(2026, 11, 5, 9, 30, 0, 500000, tzinfo=mountain)
    assert arrival.utcoffset() == timedelta(hours=-7)


def test_arrival_time_crosses_midnight_and_compares_across_timezones() -> None:
    departure = datetime(2026, 11, 5, 23, 0, tzinfo=timezone(timedelta(hours=-7)))

    assert arrival_time(departure, 7200) == datetime(2026, 11, 6, 8, 0, tzinfo=UTC)


def test_naive_departure_is_rejected() -> None:
    with pytest.raises(ValueError):
        arrival_time(datetime(2026, 11, 5, 8, 0), 60)
