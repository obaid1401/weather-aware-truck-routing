"""Route ranking and recommendation (FR-10).

Routes are ranked by a lexicographic comparison, never a weighted score:

1. Fewest severe-risk miles.
2. Fewest high-risk miles.
3. Lowest distance-weighted average risk score. A route with no known average (no mile
   with a known risk) ranks below every route with a known average at this step.
4. Shortest estimated travel time.

When all four are tied: the shorter route, then provider order.

NO_TRAVEL miles are not a ranking criterion. They are reported as prominent warnings
instead, together with incomplete weather coverage.
"""

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from shared.types import Recommendation, Route, RouteMetrics


@dataclass(frozen=True)
class _Candidate:
    route: Route
    metrics: RouteMetrics
    provider_position: int


def ranking_key(metrics: RouteMetrics, provider_position: int) -> tuple:
    """Sort key: smaller is better at every position, compared left to right."""
    average = metrics.average_risk_score
    return (
        metrics.severe_miles,
        metrics.high_miles,
        (0, average) if average is not None else (1, 0.0),  # unknown average ranks last
        metrics.duration_seconds,
        metrics.distance_miles,
        provider_position,
    )


def recommend(
    routes: Sequence[Route], metrics_by_route: Mapping[str, RouteMetrics]
) -> Recommendation | None:
    """Ranks `routes` (in provider order) using their metrics. Returns None when there are
    no routes, since no recommendation can be made."""
    if not routes:
        return None
    missing = [route.id for route in routes if route.id not in metrics_by_route]
    if missing:
        raise ValueError(f"no metrics for routes: {', '.join(missing)}")

    candidates = sorted(
        (
            _Candidate(route, metrics_by_route[route.id], position)
            for position, route in enumerate(routes)
        ),
        key=lambda c: ranking_key(c.metrics, c.provider_position),
    )
    return Recommendation(
        recommended_route_id=candidates[0].route.id,
        ranked_route_ids=tuple(c.route.id for c in candidates),
        ranking_reasons=_ranking_reasons(candidates),
        warnings=_warnings(candidates),
    )


# Explanations


def _ranking_reasons(candidates: list[_Candidate]) -> tuple[str, ...]:
    count = len(candidates)
    best = candidates[0]
    if count == 1:
        first = (
            f"{best.route.label} is recommended because it is the only route available "
            f"({_summary(best.metrics)})."
        )
    else:
        first = (
            f"{best.route.label} is recommended: it ranks first of {count} routes "
            f"({_summary(best.metrics)}). It ranks ahead of {candidates[1].route.label} on "
            f"{_deciding_criterion(best, candidates[1])}."
        )
    reasons = [first]
    for rank, (above, current) in enumerate(zip(candidates, candidates[1:], strict=False), start=2):
        reasons.append(
            f"{current.route.label} ranks {rank} of {count} ({_summary(current.metrics)}). "
            f"It ranks below {above.route.label} on {_deciding_criterion(above, current)}."
        )
    return tuple(reasons)


def _deciding_criterion(better: _Candidate, worse: _Candidate) -> str:
    """The first ranking criterion on which `better` beats `worse`, in words."""
    a, b = better.metrics, worse.metrics
    if a.severe_miles != b.severe_miles:
        return "fewer severe-risk miles ({} vs {})".format(
            *_compared_miles(a.severe_miles, b.severe_miles)
        )
    if a.high_miles != b.high_miles:
        return "fewer high-risk miles ({} vs {})".format(
            *_compared_miles(a.high_miles, b.high_miles)
        )
    if a.average_risk_score != b.average_risk_score:
        if b.average_risk_score is None:
            return (
                f"average risk score ({_average(a.average_risk_score)} vs unknown; a route "
                "without any known weather risk ranks below routes with a known average)"
            )
        return "lower average risk score ({} vs {})".format(
            *_compared_averages(a.average_risk_score, b.average_risk_score)  # type: ignore[arg-type]
        )
    if a.duration_seconds != b.duration_seconds:
        faster, slower = _duration(a.duration_seconds), _duration(b.duration_seconds)
        if faster == slower:
            faster, slower = f"{a.duration_seconds:,.1f} s", f"{b.duration_seconds:,.1f} s"
        return f"shorter estimated travel time ({faster} vs {slower})"
    if a.distance_miles != b.distance_miles:
        return (
            "shorter distance ({} vs {}), after tying on severe-risk miles, high-risk miles, "
            "average risk, and travel time".format(
                *_compared_miles(a.distance_miles, b.distance_miles)
            )
        )
    return "routing provider order, after tying on every ranking criterion and distance"


def _summary(metrics: RouteMetrics) -> str:
    return (
        f"{_miles(metrics.severe_miles)} severe-risk, {_miles(metrics.high_miles)} high-risk, "
        f"{_miles(metrics.no_travel_miles)} no-travel; average risk "
        f"{_average(metrics.average_risk_score)}; {_duration(metrics.duration_seconds)}; "
        f"{_miles(metrics.distance_miles)}; weather coverage "
        f"{_percent(metrics.weather_coverage_percent)}"
    )


# Warnings


def _warnings(candidates: list[_Candidate]) -> tuple[str, ...]:
    warnings = []
    recommended = candidates[0]

    no_travel = [c for c in candidates if c.metrics.no_travel_miles > 0]
    for c in no_travel:
        role = "the recommended route" if c is recommended else "an alternative route"
        warnings.append(
            f"NO_TRAVEL conditions: {c.route.label} ({role}) has "
            f"{_miles(c.metrics.no_travel_miles)} of no-travel conditions."
        )
    if no_travel and len(no_travel) == len(candidates):
        warnings.append(
            "No route is free of NO_TRAVEL conditions."
            if len(candidates) > 1
            else "The only available route contains NO_TRAVEL conditions."
        )

    for c in candidates:
        m = c.metrics
        if m.unknown_miles > 0:
            warnings.append(
                f"Incomplete weather data: risk is unknown for {_miles(m.unknown_miles)} of "
                f"{c.route.label} (weather coverage {_percent(m.weather_coverage_percent)}). "
                "Unknown miles are not counted as safe."
            )
        elif m.complete_weather_coverage_percent < 100:
            warnings.append(
                f"Incomplete weather data: some weather values are missing on {c.route.label} "
                f"(complete weather coverage {_percent(m.complete_weather_coverage_percent)}). "
                "Risk there is based on the available values only."
            )

    if all(c.metrics.average_risk_score is None for c in candidates):
        warnings.append(
            "No weather risk could be determined for any route, so the recommendation is "
            "based on travel time and distance only and is not a weather assessment."
        )
    return tuple(warnings)


# Formatting


def _miles(value: float) -> str:
    # Never show a non-zero distance (for example of NO_TRAVEL conditions) as 0.0.
    if 0 < value < 0.05:
        return "<0.1 mi"
    return f"{value:,.1f} mi"


def _compared_miles(a: float, b: float) -> tuple[str, str]:
    """Both distances, with enough precision that they visibly differ."""
    if _miles(a) != _miles(b):
        return _miles(a), _miles(b)
    return f"{a:,.3f} mi", f"{b:,.3f} mi"


def _average(value: float | None) -> str:
    return "unknown" if value is None else f"{value:.2f}"


def _compared_averages(a: float, b: float) -> tuple[str, str]:
    if _average(a) != _average(b):
        return _average(a), _average(b)
    return f"{a:.4f}", f"{b:.4f}"


def _percent(value: float) -> str:
    # Rounded down, so incomplete coverage is never shown as 100%.
    tenths = math.floor(value * 10 + 1e-9) / 10
    return f"{tenths:.0f}%" if tenths.is_integer() else f"{tenths:.1f}%"


def _duration(seconds: float) -> str:
    minutes = round(seconds / 60)
    hours, minutes = divmod(minutes, 60)
    return f"{hours} h {minutes:02d} min" if hours else f"{minutes} min"
