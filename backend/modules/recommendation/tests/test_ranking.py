import dataclasses
from typing import Any

import pytest

from modules.recommendation.domain.ranking import ranking_key, recommend
from shared.types import Coordinate, Route, RouteMetrics

BASE = RouteMetrics(
    distance_miles=500.0,
    duration_seconds=8 * 3600.0,
    low_miles=500.0,
    moderate_miles=0.0,
    high_miles=0.0,
    severe_miles=0.0,
    no_travel_miles=0.0,
    unknown_miles=0.0,
    average_risk_score=1.0,
    weather_coverage_percent=100.0,
    complete_weather_coverage_percent=100.0,
)


def metrics(**changes: Any) -> RouteMetrics:
    return dataclasses.replace(BASE, **changes)


def route(number: int) -> Route:
    return Route(
        id=f"route-{number}",
        label=f"Route {'ABCDE'[number - 1]}",
        geometry=(Coordinate(0, 0), Coordinate(0, 1)),
        distance_miles=500.0,
        duration_seconds=8 * 3600.0,
        steps=(),
    )


def rank(*route_metrics: RouteMetrics) -> Any:
    """Recommendation for routes 1..n (in provider order) with the given metrics."""
    routes = [route(n) for n in range(1, len(route_metrics) + 1)]
    return recommend(routes, {r.id: m for r, m in zip(routes, route_metrics, strict=True)})


def order(*route_metrics: RouteMetrics) -> list[str]:
    return list(rank(*route_metrics).ranked_route_ids)


# Each criterion, in priority order


def test_fewest_severe_miles_ranks_first() -> None:
    assert order(metrics(severe_miles=30), metrics(severe_miles=10)) == ["route-2", "route-1"]


def test_severe_miles_outrank_every_later_criterion() -> None:
    worse_later = metrics(
        severe_miles=10, high_miles=200, average_risk_score=3.5, duration_seconds=20 * 3600
    )
    better_later = metrics(
        severe_miles=11, high_miles=0, average_risk_score=1.0, duration_seconds=3600
    )

    assert order(better_later, worse_later) == ["route-2", "route-1"]


def test_high_miles_decide_when_severe_miles_tie() -> None:
    assert order(
        metrics(severe_miles=5, high_miles=40), metrics(severe_miles=5, high_miles=20)
    ) == ["route-2", "route-1"]


def test_high_miles_outrank_average_and_travel_time() -> None:
    worse_later = metrics(high_miles=20, average_risk_score=3.0, duration_seconds=12 * 3600)
    better_later = metrics(high_miles=21, average_risk_score=1.0, duration_seconds=3600)

    assert order(better_later, worse_later) == ["route-2", "route-1"]


def test_average_risk_decides_when_severe_and_high_miles_tie() -> None:
    assert order(metrics(average_risk_score=1.6), metrics(average_risk_score=1.2)) == [
        "route-2",
        "route-1",
    ]


def test_average_risk_outranks_travel_time() -> None:
    slower_safer = metrics(average_risk_score=1.1, duration_seconds=10 * 3600)
    faster_riskier = metrics(average_risk_score=1.5, duration_seconds=5 * 3600)

    assert order(faster_riskier, slower_safer) == ["route-2", "route-1"]


def test_travel_time_decides_when_risk_criteria_tie() -> None:
    assert order(metrics(duration_seconds=9 * 3600), metrics(duration_seconds=8 * 3600)) == [
        "route-2",
        "route-1",
    ]


def test_travel_time_outranks_distance() -> None:
    shorter_slower = metrics(distance_miles=400, duration_seconds=9 * 3600)
    longer_faster = metrics(distance_miles=600, duration_seconds=8 * 3600)

    assert order(shorter_slower, longer_faster) == ["route-2", "route-1"]


def test_no_travel_miles_are_not_a_ranking_criterion() -> None:
    # FR-10: ranking must not silently add no-travel miles; they are reported as warnings.
    with_no_travel = metrics(no_travel_miles=50, duration_seconds=7 * 3600)
    without = metrics(duration_seconds=8 * 3600)

    assert order(without, with_no_travel) == ["route-2", "route-1"]


def test_weighted_scores_are_not_used() -> None:
    # A weighted formula could favour route 1 (far fewer high miles, lower average); the
    # lexicographic order picks route 2 for its single fewer severe mile.
    route_1 = metrics(severe_miles=1, high_miles=0, average_risk_score=1.01)
    route_2 = metrics(severe_miles=0, high_miles=300, average_risk_score=2.9)

    assert order(route_1, route_2) == ["route-2", "route-1"]


# Tie-breakers


def test_shorter_distance_breaks_a_tie_on_all_four_criteria() -> None:
    assert order(metrics(distance_miles=510), metrics(distance_miles=490)) == [
        "route-2",
        "route-1",
    ]


def test_provider_order_breaks_a_complete_tie() -> None:
    assert order(metrics(), metrics(), metrics()) == ["route-1", "route-2", "route-3"]


def test_provider_order_is_preserved_whatever_order_metrics_are_given_in() -> None:
    routes = [route(1), route(2)]
    tied = {"route-2": metrics(), "route-1": metrics()}  # mapping order reversed

    assert recommend(routes, tied).ranked_route_ids == ("route-1", "route-2")  # type: ignore[union-attr]


def test_full_ordering_of_several_routes() -> None:
    assert order(
        metrics(severe_miles=0, high_miles=10),  # 3rd: more high miles
        metrics(severe_miles=0, high_miles=0, average_risk_score=1.4),  # 2nd: higher average
        metrics(severe_miles=5),  # 5th: most severe miles
        metrics(severe_miles=0, high_miles=0, average_risk_score=1.1),  # 1st
        metrics(severe_miles=0, high_miles=10, distance_miles=400),  # tie with route 1 but shorter
    ) == ["route-4", "route-2", "route-5", "route-1", "route-3"]


# Unknown average risk


def test_unknown_average_ranks_below_any_known_average() -> None:
    unknown = metrics(average_risk_score=None, weather_coverage_percent=0, unknown_miles=500)
    worst_known = metrics(average_risk_score=5.0)

    assert order(unknown, worst_known) == ["route-2", "route-1"]


def test_unknown_average_does_not_override_earlier_criteria() -> None:
    unknown_but_fewer_high = metrics(average_risk_score=None, high_miles=0)
    known_but_more_high = metrics(average_risk_score=1.0, high_miles=10)

    assert order(known_but_more_high, unknown_but_fewer_high) == ["route-2", "route-1"]


def test_two_unknown_averages_tie_and_fall_through_to_travel_time() -> None:
    assert order(
        metrics(average_risk_score=None, duration_seconds=9 * 3600),
        metrics(average_risk_score=None, duration_seconds=8 * 3600),
    ) == ["route-2", "route-1"]


def test_ranking_key_matches_the_documented_comparator() -> None:
    m = metrics(severe_miles=1, high_miles=2, average_risk_score=1.5, duration_seconds=10)

    assert ranking_key(m, 3) == (1, 2, (0, 1.5), 10, 500.0, 3)
    assert ranking_key(dataclasses.replace(m, average_risk_score=None), 3)[2] == (1, 0.0)


# No routes, and input validation


def test_no_routes_means_no_recommendation() -> None:
    assert recommend([], {}) is None


def test_missing_metrics_are_rejected() -> None:
    with pytest.raises(ValueError, match="route-2"):
        recommend([route(1), route(2)], {"route-1": metrics()})


# Explanations


def test_recommendation_explains_the_deciding_criterion() -> None:
    result = rank(metrics(severe_miles=25), metrics(severe_miles=0, high_miles=10))

    assert result.recommended_route_id == "route-2"
    assert result.ranking_reasons[0] == (
        "Route B is recommended: it ranks first of 2 routes (0.0 mi severe-risk, 10.0 mi "
        "high-risk, 0.0 mi no-travel; average risk 1.00; 8 h 00 min; 500.0 mi; weather "
        "coverage 100%). It ranks ahead of Route A on fewer severe-risk miles "
        "(0.0 mi vs 25.0 mi)."
    )
    assert result.ranking_reasons[1].startswith("Route A ranks 2 of 2 (25.0 mi severe-risk")
    assert result.ranking_reasons[1].endswith(
        "It ranks below Route B on fewer severe-risk miles (0.0 mi vs 25.0 mi)."
    )


@pytest.mark.parametrize(
    ("better", "worse", "phrase"),
    [
        ({"high_miles": 5}, {"high_miles": 15}, "fewer high-risk miles (5.0 mi vs 15.0 mi)"),
        (
            {"average_risk_score": 1.25},
            {"average_risk_score": 1.5},
            "lower average risk score (1.25 vs 1.50)",
        ),
        (
            {"average_risk_score": 2.0},
            {"average_risk_score": None},
            "average risk score (2.00 vs unknown; a route without any known weather risk "
            "ranks below routes with a known average)",
        ),
        (
            {"duration_seconds": 7.5 * 3600},
            {"duration_seconds": 8 * 3600},
            "shorter estimated travel time (7 h 30 min vs 8 h 00 min)",
        ),
        (
            {"distance_miles": 480},
            {"distance_miles": 520},
            "shorter distance (480.0 mi vs 520.0 mi), after tying on severe-risk miles, "
            "high-risk miles, average risk, and travel time",
        ),
        ({}, {}, "routing provider order, after tying on every ranking criterion and distance"),
    ],
)
def test_each_criterion_is_explained(
    better: dict[str, Any], worse: dict[str, Any], phrase: str
) -> None:
    result = rank(metrics(**better), metrics(**worse))

    assert result.ranked_route_ids == ("route-1", "route-2")
    assert result.ranking_reasons[0].endswith(f"It ranks ahead of Route B on {phrase}.")
    assert result.ranking_reasons[1].endswith(f"It ranks below Route A on {phrase}.")


def test_each_route_is_explained_against_the_route_directly_above_it() -> None:
    result = rank(
        metrics(severe_miles=0, high_miles=0),
        metrics(severe_miles=0, high_miles=20),
        metrics(severe_miles=40),
    )

    assert len(result.ranking_reasons) == 3
    assert "It ranks below Route A on fewer high-risk miles" in result.ranking_reasons[1]
    assert "It ranks below Route B on fewer severe-risk miles" in result.ranking_reasons[2]


@pytest.mark.parametrize(
    ("better", "worse", "shown"),
    [
        ({"severe_miles": 25.004}, {"severe_miles": 25.006}, "(25.004 mi vs 25.006 mi)"),
        ({"average_risk_score": 1.2341}, {"average_risk_score": 1.2349}, "(1.2341 vs 1.2349)"),
        (
            {"duration_seconds": 28580.2},
            {"duration_seconds": 28580.7},
            "(28,580.2 s vs 28,580.7 s)",
        ),
    ],
)
def test_near_identical_values_are_shown_with_enough_precision(
    better: dict[str, Any], worse: dict[str, Any], shown: str
) -> None:
    result = rank(metrics(**better), metrics(**worse))

    assert shown in result.ranking_reasons[0]


def test_single_route_explanation() -> None:
    result = rank(metrics())

    assert result.ranked_route_ids == ("route-1",)
    assert result.ranking_reasons[0].startswith(
        "Route A is recommended because it is the only route available"
    )


# Warnings


def test_no_travel_warnings_name_each_affected_route() -> None:
    result = rank(metrics(no_travel_miles=12.5), metrics(), metrics(no_travel_miles=3))

    assert result.warnings == (
        "NO_TRAVEL conditions: Route A (the recommended route) has 12.5 mi of no-travel "
        "conditions.",
        "NO_TRAVEL conditions: Route C (an alternative route) has 3.0 mi of no-travel conditions.",
    )


def test_all_routes_with_no_travel_are_called_out() -> None:
    result = rank(metrics(no_travel_miles=10), metrics(no_travel_miles=20))

    assert "No route is free of NO_TRAVEL conditions." in result.warnings


def test_single_route_with_no_travel() -> None:
    result = rank(metrics(no_travel_miles=10))

    assert "The only available route contains NO_TRAVEL conditions." in result.warnings


def test_tiny_no_travel_distance_is_never_shown_as_zero() -> None:
    result = rank(metrics(no_travel_miles=0.02))

    assert result.warnings[0] == (
        "NO_TRAVEL conditions: Route A (the recommended route) has <0.1 mi of no-travel conditions."
    )


def test_routes_without_no_travel_or_gaps_have_no_warnings() -> None:
    assert rank(metrics(high_miles=50), metrics()).warnings == ()


def test_unknown_miles_warning_shows_weather_coverage() -> None:
    result = rank(metrics(unknown_miles=25, weather_coverage_percent=95, average_risk_score=1.1))

    assert result.warnings == (
        "Incomplete weather data: risk is unknown for 25.0 mi of Route A (weather coverage "
        "95%). Unknown miles are not counted as safe.",
    )


def test_partial_weather_values_warning_shows_complete_coverage() -> None:
    result = rank(metrics(complete_weather_coverage_percent=62.5))

    assert result.warnings == (
        "Incomplete weather data: some weather values are missing on Route A (complete "
        "weather coverage 62.5%). Risk there is based on the available values only.",
    )


def test_coverage_is_never_rounded_up_to_100_percent() -> None:
    result = rank(metrics(unknown_miles=0.2, weather_coverage_percent=99.96))

    assert "(weather coverage 99.9%)" in result.warnings[0]


def test_no_weather_for_any_route_means_no_weather_based_recommendation() -> None:
    no_weather = metrics(
        average_risk_score=None,
        unknown_miles=500,
        low_miles=0,
        weather_coverage_percent=0,
        complete_weather_coverage_percent=0,
    )

    result = rank(no_weather, no_weather)

    assert result.warnings[-1] == (
        "No weather risk could be determined for any route, so the recommendation is based "
        "on travel time and distance only and is not a weather assessment."
    )
    assert sum("Incomplete weather data" in w for w in result.warnings) == 2


def test_no_travel_warnings_come_before_coverage_warnings() -> None:
    # The coverage gap is on route A; route B has NO_TRAVEL miles. NO_TRAVEL is listed first.
    result = rank(
        metrics(unknown_miles=10, weather_coverage_percent=98),
        metrics(no_travel_miles=5, duration_seconds=9 * 3600),
    )

    assert [w.split(":")[0] for w in result.warnings] == [
        "NO_TRAVEL conditions",
        "Incomplete weather data",
    ]
