import random
from collections.abc import Sequence
from datetime import UTC, datetime

import pytest

from modules.recommendation.domain.metrics import route_metrics
from modules.recommendation.domain.ranking import recommend
from shared.types import Checkpoint, Coordinate, DataStatus, RiskLevel, Route

LOW, MODERATE, HIGH, SEVERE, NO_TRAVEL, UNKNOWN = (
    RiskLevel.LOW,
    RiskLevel.MODERATE,
    RiskLevel.HIGH,
    RiskLevel.SEVERE,
    RiskLevel.NO_TRAVEL,
    RiskLevel.UNKNOWN,
)
NOW = datetime(2026, 11, 5, 15, 0, tzinfo=UTC)


def route(distance: float, route_id: str = "route-1") -> Route:
    return Route(
        id=route_id,
        label="Route A",
        geometry=(Coordinate(0, 0), Coordinate(0, 1)),
        distance_miles=distance,
        duration_seconds=3600.0,
        steps=(),
    )


def checkpoints(
    stops: Sequence[tuple[float, RiskLevel] | tuple[float, RiskLevel, DataStatus]],
    route_id: str = "route-1",
) -> list[Checkpoint]:
    """Checkpoints from `(distance, final_risk)` or `(distance, final_risk, data_status)`.
    Without a data status, it follows the risk: UNAVAILABLE for UNKNOWN, else AVAILABLE."""
    result = []
    for n, (distance, risk, *status) in enumerate(stops):
        default = DataStatus.UNAVAILABLE if risk is UNKNOWN else DataStatus.AVAILABLE
        result.append(
            Checkpoint(
                id=f"{route_id}-cp-{n}",
                route_id=route_id,
                distance_from_origin_miles=distance,
                latitude=0.0,
                longitude=0.0,
                estimated_arrival_time=NOW,
                data_status=status[0] if status else default,
                final_risk=risk,
            )
        )
    return result


def test_each_segment_takes_its_downstream_checkpoints_risk() -> None:
    # Origin (its risk covers no miles), then 25-mile segments and a 10-mile final segment.
    cps = checkpoints([(0, NO_TRAVEL), (25, HIGH), (50, SEVERE), (60, MODERATE)])

    metrics = route_metrics(route(60), cps)

    assert metrics.no_travel_miles == 0  # the origin's risk is not assigned to any miles
    assert metrics.high_miles == 25
    assert metrics.severe_miles == 25
    assert metrics.moderate_miles == 10  # final partial segment
    assert metrics.low_miles == 0
    assert metrics.unknown_miles == 0


def test_every_mile_is_counted_exactly_once() -> None:
    cps = checkpoints([(0, LOW), (10, LOW), (20, HIGH), (30, UNKNOWN), (37.5, NO_TRAVEL)])

    m = route_metrics(route(37.5), cps)

    total = (
        m.low_miles
        + m.moderate_miles
        + m.high_miles
        + m.severe_miles
        + m.no_travel_miles
        + m.unknown_miles
    )
    assert total == pytest.approx(37.5)
    # Segments: 0-10 LOW, 10-20 HIGH, 20-30 UNKNOWN, 30-37.5 NO_TRAVEL.
    assert (m.low_miles, m.high_miles, m.unknown_miles, m.no_travel_miles) == (10, 10, 10, 7.5)


def test_distance_weighted_average_excludes_unknown_miles() -> None:
    # Known: 25 mi HIGH (3), 25 mi SEVERE (4), 10 mi MODERATE (2). Unknown: 20 mi.
    cps = checkpoints([(0, LOW), (25, HIGH), (50, SEVERE), (70, UNKNOWN), (80, MODERATE)])

    metrics = route_metrics(route(80), cps)

    assert metrics.average_risk_score == pytest.approx((3 * 25 + 4 * 25 + 2 * 10) / 60)
    assert metrics.unknown_miles == 20
    assert metrics.weather_coverage_percent == pytest.approx(75.0)


def test_average_is_weighted_by_distance_not_by_checkpoint_count() -> None:
    # One long LOW segment and one short NO_TRAVEL segment.
    cps = checkpoints([(0, LOW), (90, LOW), (100, NO_TRAVEL)])

    metrics = route_metrics(route(100), cps)

    assert metrics.average_risk_score == pytest.approx((1 * 90 + 5 * 10) / 100)  # 1.4
    assert metrics.average_risk_score != pytest.approx((1 + 5) / 2)  # not a simple mean


def test_no_known_risk_gives_no_average_and_zero_coverage() -> None:
    cps = checkpoints([(0, LOW), (25, UNKNOWN), (40, UNKNOWN)])

    metrics = route_metrics(route(40), cps)

    assert metrics.average_risk_score is None
    assert metrics.weather_coverage_percent == 0
    assert metrics.unknown_miles == 40


def test_full_coverage() -> None:
    metrics = route_metrics(route(30), checkpoints([(0, UNKNOWN), (25, LOW), (30, LOW)]))

    assert metrics.weather_coverage_percent == 100
    assert metrics.average_risk_score == 1


def test_route_shorter_than_one_interval() -> None:
    metrics = route_metrics(route(3.5), checkpoints([(0, LOW), (3.5, SEVERE)]))

    assert metrics.severe_miles == 3.5
    assert metrics.average_risk_score == 4


def test_metrics_copy_route_distance_and_duration() -> None:
    metrics = route_metrics(route(60), checkpoints([(0, LOW), (60, LOW)]))

    assert (metrics.distance_miles, metrics.duration_seconds) == (60, 3600.0)


@pytest.mark.parametrize(
    "stops",
    [
        [(0, LOW)],  # no destination
        [(5, LOW), (60, LOW)],  # does not start at the origin
        [(0, LOW), (40, LOW), (30, LOW), (60, LOW)],  # out of order
        [(0, LOW), (50, LOW)],  # does not reach the destination
    ],
)
def test_invalid_checkpoint_sequences_are_rejected(stops: list[tuple[float, RiskLevel]]) -> None:
    with pytest.raises(ValueError):
        route_metrics(route(60), checkpoints(stops))


def test_checkpoints_from_another_route_are_rejected() -> None:
    with pytest.raises(ValueError):
        route_metrics(route(60), checkpoints([(0, LOW), (60, LOW)], route_id="route-2"))


# Complete weather coverage (all three weather values available)

AVAILABLE, PARTIAL, UNAVAILABLE = DataStatus.AVAILABLE, DataStatus.PARTIAL, DataStatus.UNAVAILABLE


def test_fully_available_weather_is_complete_everywhere() -> None:
    cps = checkpoints([(0, LOW, AVAILABLE), (25, HIGH, AVAILABLE), (60, LOW, AVAILABLE)])

    metrics = route_metrics(route(60), cps)

    assert metrics.complete_weather_coverage_percent == 100
    assert metrics.weather_coverage_percent == 100


def test_partial_weather_counts_for_risk_coverage_but_not_complete_coverage() -> None:
    # Segment 0-25 ends at a checkpoint with partial data but a known (LOW) risk.
    cps = checkpoints([(0, LOW, AVAILABLE), (25, LOW, PARTIAL), (60, LOW, AVAILABLE)])

    metrics = route_metrics(route(60), cps)

    assert metrics.weather_coverage_percent == 100
    assert metrics.complete_weather_coverage_percent == pytest.approx(100 * 35 / 60)


def test_unavailable_weather_counts_for_neither_coverage() -> None:
    cps = checkpoints([(0, LOW, AVAILABLE), (25, UNKNOWN, UNAVAILABLE), (40, HIGH, AVAILABLE)])

    metrics = route_metrics(route(40), cps)

    assert metrics.weather_coverage_percent == pytest.approx(100 * 15 / 40)
    assert metrics.complete_weather_coverage_percent == pytest.approx(100 * 15 / 40)
    assert metrics.unknown_miles == 25


def test_partial_data_everywhere_looks_covered_but_is_not_complete() -> None:
    # Wind missing at every checkpoint, rain and snow LOW: risk is known (LOW) everywhere,
    # but no mile has complete weather data.
    cps = checkpoints([(0, LOW, PARTIAL), (25, LOW, PARTIAL), (50, LOW, PARTIAL)])

    metrics = route_metrics(route(50), cps)

    assert metrics.weather_coverage_percent == 100
    assert metrics.complete_weather_coverage_percent == 0


def test_complete_coverage_uses_the_downstream_checkpoint_and_the_final_segment() -> None:
    # The origin's status covers no miles; the 10-mile final segment ends at the destination.
    cps = checkpoints(
        [(0, UNKNOWN, UNAVAILABLE), (25, LOW, AVAILABLE), (50, LOW, PARTIAL), (60, LOW, AVAILABLE)]
    )

    metrics = route_metrics(route(60), cps)

    assert metrics.complete_weather_coverage_percent == pytest.approx(100 * (25 + 10) / 60)


def test_complete_coverage_does_not_change_risk_figures() -> None:
    stops = [(0, LOW), (25, HIGH), (50, SEVERE), (70, UNKNOWN), (80, MODERATE)]
    with_partial = [
        (0, LOW, AVAILABLE),
        (25, HIGH, PARTIAL),
        (50, SEVERE, PARTIAL),
        (70, UNKNOWN, UNAVAILABLE),
        (80, MODERATE, AVAILABLE),
    ]

    baseline = route_metrics(route(80), checkpoints(stops))
    partial = route_metrics(route(80), checkpoints(with_partial))

    for field in (
        "low_miles",
        "moderate_miles",
        "high_miles",
        "severe_miles",
        "no_travel_miles",
        "unknown_miles",
        "average_risk_score",
        "weather_coverage_percent",
    ):
        assert getattr(partial, field) == getattr(baseline, field)
    assert baseline.complete_weather_coverage_percent == pytest.approx(75.0)
    assert partial.complete_weather_coverage_percent == pytest.approx(100 * 10 / 80)


# Coverage is exact at 100% and 0% (floating-point summation order)


def uneven_routes(count: int, seed: int = 1) -> list[tuple[Route, list[tuple[float, RiskLevel]]]]:
    """Routes with uneven segment lengths and mixed known risks. Many of these produced a
    coverage of 99.99999999999999% before the fix."""
    rng = random.Random(seed)
    routes = []
    for _ in range(count):
        distances = [0.0]
        for _ in range(rng.randint(3, 25)):
            distances.append(distances[-1] + rng.choice([10, 25, 50]) + rng.random())
        stops = [(d, rng.choice([LOW, MODERATE, HIGH, SEVERE, NO_TRAVEL])) for d in distances]
        routes.append((route(distances[-1]), stops))
    return routes


def test_full_weather_on_uneven_segments_is_exactly_100_percent() -> None:
    for full_route, stops in uneven_routes(500):
        metrics = route_metrics(full_route, checkpoints(stops))

        assert metrics.weather_coverage_percent == 100.0
        assert metrics.complete_weather_coverage_percent == 100.0
        assert metrics.unknown_miles == 0


def test_full_weather_on_uneven_segments_gives_no_incomplete_data_warning() -> None:
    for full_route, stops in uneven_routes(200, seed=7):
        metrics = route_metrics(full_route, checkpoints(stops))

        recommendation = recommend([full_route], {full_route.id: metrics})

        assert not any("Incomplete weather data" in w for w in recommendation.warnings)  # type: ignore[union-attr]


def test_no_weather_on_uneven_segments_is_exactly_0_percent() -> None:
    _, stops = uneven_routes(1, seed=3)[0]
    distances = [d for d, _ in stops]
    no_data = [(d, UNKNOWN, UNAVAILABLE) for d in distances]
    partial = [(d, LOW, PARTIAL) for d in distances]

    unknown = route_metrics(route(distances[-1]), checkpoints(no_data))
    known_but_partial = route_metrics(route(distances[-1]), checkpoints(partial))

    assert (unknown.weather_coverage_percent, unknown.complete_weather_coverage_percent) == (0, 0)
    assert unknown.average_risk_score is None
    assert known_but_partial.weather_coverage_percent == 100.0
    assert known_but_partial.complete_weather_coverage_percent == 0.0


def test_partial_and_unavailable_data_on_uneven_segments() -> None:
    # Segments: 12.3 (complete), 7.9 (partial, known risk), 20.45 (no data), 5.35 (complete).
    cps = checkpoints(
        [
            (0, LOW, AVAILABLE),
            (12.3, LOW, AVAILABLE),
            (20.2, MODERATE, PARTIAL),
            (40.65, UNKNOWN, UNAVAILABLE),
            (46.0, HIGH, AVAILABLE),
        ]
    )

    metrics = route_metrics(route(46.0), cps)

    assert metrics.unknown_miles == pytest.approx(20.45)
    assert metrics.weather_coverage_percent == pytest.approx(100 * (46.0 - 20.45) / 46.0)
    assert metrics.complete_weather_coverage_percent == pytest.approx(100 * (12.3 + 5.35) / 46.0)
    assert 0 < metrics.complete_weather_coverage_percent < metrics.weather_coverage_percent < 100
    # Risk mileage and the average are unaffected by the coverage calculation.
    assert (metrics.low_miles, metrics.moderate_miles, metrics.high_miles) == pytest.approx(
        (12.3, 7.9, 5.35)
    )
    assert metrics.average_risk_score == pytest.approx((1 * 12.3 + 2 * 7.9 + 3 * 5.35) / 25.55)
