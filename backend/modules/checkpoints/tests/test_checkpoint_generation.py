from datetime import datetime, timedelta, timezone

import pytest

from modules.checkpoints.services.checkpoint_generation import generate_checkpoints
from modules.checkpoints.tests.routes import MILES_PER_DEGREE, equator_route, make_route
from shared.types import Checkpoint, Coordinate

MOUNTAIN = timezone(timedelta(hours=-7))
DEPARTURE = datetime(2026, 11, 5, 8, 0, tzinfo=MOUNTAIN)


def test_checkpoints_along_a_straight_route() -> None:
    # One degree along the equator (~69.09 miles), 25-mile interval, one hour.
    route = equator_route(0.0, 1.0, duration_seconds=3600.0)

    checkpoints = generate_checkpoints(route, 25, DEPARTURE)

    assert [c.id for c in checkpoints] == [f"route-1-cp-{n}" for n in range(4)]
    assert {c.route_id for c in checkpoints} == {"route-1"}
    assert [c.distance_from_origin_miles for c in checkpoints] == [
        0.0,
        25.0,
        50.0,
        route.distance_miles,
    ]
    for checkpoint in checkpoints:
        assert checkpoint.latitude == pytest.approx(0.0, abs=1e-9)
        assert checkpoint.longitude == pytest.approx(
            checkpoint.distance_from_origin_miles / MILES_PER_DEGREE
        )
    # No step data, so ETAs follow the average speed.
    elapsed = (checkpoints[1].estimated_arrival_time - DEPARTURE).total_seconds()
    assert elapsed == pytest.approx(3600 * 25 / route.distance_miles)


def test_origin_and_destination_match_the_route_ends_exactly() -> None:
    route = equator_route(0.0, 0.4, 1.0, duration_seconds=3600.0)

    origin, *_, destination = generate_checkpoints(route, 10, DEPARTURE)

    assert origin == Checkpoint("route-1-cp-0", "route-1", 0.0, 0.0, 0.0, DEPARTURE)
    assert (destination.latitude, destination.longitude) == (0.0, 1.0)
    assert destination.distance_from_origin_miles == route.distance_miles
    assert destination.estimated_arrival_time == DEPARTURE + timedelta(hours=1)


@pytest.mark.parametrize(
    ("interval", "count", "last_multiple"),
    [
        (10, 13, 110.0),  # 120 is itself a multiple, so it is only the destination
        (25, 6, 100.0),
        (50, 4, 100.0),
    ],
)
def test_supported_intervals(interval: int, count: int, last_multiple: float) -> None:
    route = equator_route(0.0, 1.0, 2.0, distance_miles=120.0)

    checkpoints = generate_checkpoints(route, interval, DEPARTURE)

    assert len(checkpoints) == count
    assert checkpoints[-1].distance_from_origin_miles == 120.0
    assert checkpoints[-2].distance_from_origin_miles == last_multiple


def test_destination_on_an_interval_multiple_is_not_duplicated() -> None:
    route = equator_route(0.0, 1.0, distance_miles=50.0)

    checkpoints = generate_checkpoints(route, 25, DEPARTURE)

    assert [c.distance_from_origin_miles for c in checkpoints] == [0.0, 25.0, 50.0]


def test_route_shorter_than_the_interval_has_origin_and_destination_only() -> None:
    route = equator_route(0.0, 0.05)  # ~3.5 miles

    checkpoints = generate_checkpoints(route, 10, DEPARTURE)

    assert [c.distance_from_origin_miles for c in checkpoints] == [0.0, route.distance_miles]


def test_positions_follow_the_route_geometry_not_a_straight_line() -> None:
    # North one degree, then east one degree. A checkpoint 1.5 degrees along the route
    # is on the eastbound leg at about (1.0, 0.5), not on the straight origin-destination line.
    route = make_route([(0.0, 0.0), (1.0, 0.0), (1.0, 1.0)])
    leg = route.distance_miles / 2

    (checkpoint,) = [
        c
        for c in generate_checkpoints(route, leg * 1.5, DEPARTURE)
        if c.distance_from_origin_miles == leg * 1.5
    ]

    assert checkpoint.latitude == pytest.approx(1.0, abs=1e-3)
    assert checkpoint.longitude == pytest.approx(0.5, abs=1e-3)


def test_step_durations_shape_the_arrival_times() -> None:
    # Two equal halves: the first takes 1000 s, the second 3000 s.
    route = equator_route(
        0.0, 1.0, 2.0, duration_seconds=4000.0, steps=[(0, 1, 1000.0), (1, 2, 3000.0)]
    )
    quarter = route.distance_miles / 4

    checkpoints = generate_checkpoints(route, quarter, DEPARTURE)
    elapsed = [(c.estimated_arrival_time - DEPARTURE).total_seconds() for c in checkpoints]

    # Proportional timing would give 0, 1000, 2000, 3000, 4000.
    assert elapsed == pytest.approx([0.0, 500.0, 1000.0, 2500.0, 4000.0])


def test_checkpoints_are_ordered_and_timezone_aware() -> None:
    route = equator_route(0.0, 0.3, 0.31, 0.9, 1.7, 2.0, duration_seconds=9000.0)

    checkpoints = generate_checkpoints(route, 10, DEPARTURE)

    distances = [c.distance_from_origin_miles for c in checkpoints]
    arrivals = [c.estimated_arrival_time for c in checkpoints]
    assert distances == sorted(distances)
    assert len(set(distances)) == len(distances)
    assert arrivals == sorted(arrivals)
    assert all(a.utcoffset() == timedelta(hours=-7) for a in arrivals)


def test_naive_departure_is_rejected_before_any_route_processing() -> None:
    # The route is invalid too; the timezone check must come first.
    invalid_route = equator_route(0.0)

    with pytest.raises(ValueError, match="timezone-aware"):
        generate_checkpoints(invalid_route, 25, datetime(2026, 11, 5, 8, 0))


def test_zero_distance_route_is_a_value_error() -> None:
    route = equator_route(0.0, 1.0, distance_miles=0.0)

    with pytest.raises(ValueError, match="positive"):
        generate_checkpoints(route, 25, DEPARTURE)


def test_mid_route_stop_delays_only_later_checkpoints() -> None:
    # 600 s to the midpoint, a 300 s stop there, then 600 s more.
    route = equator_route(
        0.0,
        1.0,
        2.0,
        duration_seconds=1500.0,
        steps=[(0, 1, 600.0), (1, 1, 300.0), (1, 2, 600.0)],
    )
    tenth = route.distance_miles / 10

    elapsed = [
        (c.estimated_arrival_time - DEPARTURE).total_seconds()
        for c in generate_checkpoints(route, tenth, DEPARTURE)
    ]

    # Before the stop: 120 s per tenth. At the stop: arrival (600 s). After: 900 s + driving.
    assert elapsed == pytest.approx([0, 120, 240, 360, 480, 600, 1020, 1140, 1260, 1380, 1500])


def test_checkpoint_coordinate() -> None:
    checkpoint = generate_checkpoints(equator_route(0.0, 1.0), 25, DEPARTURE)[1]

    assert checkpoint.coordinate == Coordinate(checkpoint.latitude, checkpoint.longitude)
