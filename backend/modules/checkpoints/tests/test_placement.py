import pytest

from modules.checkpoints.domain.placement import checkpoint_distances, cumulative_distances, locate
from modules.checkpoints.tests.routes import MILES_PER_DEGREE, equator_route, make_route

# Checkpoint distances


@pytest.mark.parametrize(
    ("total", "interval", "expected"),
    [
        (60.0, 25, (0.0, 25.0, 50.0, 60.0)),  # final partial segment
        (25.0, 10, (0.0, 10.0, 20.0, 25.0)),
        (120.0, 50, (0.0, 50.0, 100.0, 120.0)),
        (3.0, 10, (0.0, 3.0)),  # shorter than one interval
        (10.0, 25, (0.0, 10.0)),
    ],
)
def test_origin_interval_multiples_and_destination(
    total: float, interval: int, expected: tuple[float, ...]
) -> None:
    assert checkpoint_distances(total, interval) == expected


@pytest.mark.parametrize("total", [50.0, 50.0 + 1e-7, 50.0 - 1e-7])
def test_destination_on_an_interval_multiple_is_not_duplicated(total: float) -> None:
    assert checkpoint_distances(total, 25) == (0.0, 25.0, total)


def test_destination_just_past_a_multiple_keeps_both() -> None:
    assert checkpoint_distances(50.01, 25) == (0.0, 25.0, 50.0, 50.01)


NAN, INF = float("nan"), float("inf")


@pytest.mark.parametrize(
    ("total", "interval"),
    [
        (0.0, 25),
        (-1.0, 25),
        (10.0, 0),
        (10.0, -5),
        (100.0, NAN),  # would otherwise silently return only the origin and destination
        (100.0, INF),
        (NAN, 25),
        (INF, 25),
    ],
)
def test_invalid_inputs_are_rejected(total: float, interval: int) -> None:
    with pytest.raises(ValueError):
        checkpoint_distances(total, interval)


# Cumulative distances


def test_cumulative_distances_follow_the_geometry() -> None:
    route = equator_route(0.0, 1.0, 3.0)

    distances = cumulative_distances(route)

    assert distances == pytest.approx((0.0, MILES_PER_DEGREE, 3 * MILES_PER_DEGREE))


def test_cumulative_distances_are_scaled_to_the_provider_distance() -> None:
    # The provider's road distance is 2% longer than the measured geometry.
    measured = 3 * MILES_PER_DEGREE
    route = equator_route(0.0, 1.0, 3.0, distance_miles=measured * 1.02)

    distances = cumulative_distances(route)

    assert distances[1] == pytest.approx(MILES_PER_DEGREE * 1.02)
    assert distances[-1] == route.distance_miles  # exact, not approximately


def test_duplicate_points_add_no_distance() -> None:
    distances = cumulative_distances(equator_route(0.0, 1.0, 1.0, 2.0))

    assert distances[1] == distances[2]


def test_cumulative_distances_measure_bends_not_the_straight_line() -> None:
    # Up one degree of latitude, then east one degree: the path is ~2 degrees long.
    route = make_route([(0.0, 0.0), (1.0, 0.0), (1.0, 1.0)])

    assert cumulative_distances(route)[-1] == pytest.approx(2 * MILES_PER_DEGREE, rel=1e-3)


@pytest.mark.parametrize(
    "route",
    [
        equator_route(0.0, distance_miles=10.0),  # a single point
        equator_route(5.0, 5.0, 5.0, distance_miles=10.0),  # zero-length geometry
        equator_route(0.0, 1.0, distance_miles=0.0),
        equator_route(0.0, 1.0, distance_miles=-5.0),
        equator_route(0.0, 1.0, distance_miles=float("nan")),
    ],
)
def test_invalid_geometry_is_rejected(route: object) -> None:
    with pytest.raises(ValueError):
        cumulative_distances(route)  # type: ignore[arg-type]


# Locating a distance on the geometry

DISTANCES = (0.0, 10.0, 10.0, 30.0)


@pytest.mark.parametrize(
    ("target", "expected"),
    [
        (0.0, (0, 0.0)),
        (-5.0, (0, 0.0)),
        (5.0, (0, 0.5)),
        (10.0, (2, 0.0)),  # exactly on a point; the zero-length segment is skipped
        (20.0, (2, 0.5)),
        (30.0, (2, 1.0)),
        (35.0, (2, 1.0)),
    ],
)
def test_locate(target: float, expected: tuple[int, float]) -> None:
    assert locate(DISTANCES, target) == expected
