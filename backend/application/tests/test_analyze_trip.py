import dataclasses
from collections.abc import Callable, Sequence
from datetime import datetime, timedelta, timezone

import pytest

from application.use_cases.analyze_trip import AnalyzeTripUseCase
from modules.geocoding.services.ors_geocoding import OrsGeocodingService
from modules.routing.services.valhalla_routing import RoutingResult, ValhallaRoutingService
from modules.weather.services.checkpoint_weather import (
    CheckpointWeatherResult,
    CheckpointWeatherService,
)
from shared.http import get_http_client
from shared.types import (
    Checkpoint,
    Coordinate,
    DataStatus,
    GeocodingAmbiguousError,
    Location,
    NoRouteFoundError,
    ProviderTimeoutError,
    RiskLevel,
    Route,
    RouteStep,
    TripInput,
)

MOUNTAIN = timezone(timedelta(hours=-7))
DEPARTURE = datetime(2026, 11, 5, 8, 0, tzinfo=MOUNTAIN)
DENVER = Location("Denver, CO, USA", 39.741, -104.986)
SALT_LAKE_CITY = Location("Salt Lake City, UT, USA", 40.773, -111.934)


def trip(**changes: object) -> TripInput:
    base = TripInput("Denver, CO", "Salt Lake City, UT", DEPARTURE, 36_000.0, 25)
    return dataclasses.replace(base, **changes)


def route(number: int, distance: float, hours: float) -> Route:
    geometry = (
        Coordinate(39.741, -104.986),
        Coordinate(40.2, -108.5),
        Coordinate(40.773, -111.934),
    )
    return Route(
        id=f"route-{number}",
        label=f"Route {'ABC'[number - 1]}",
        geometry=geometry,
        distance_miles=distance,
        duration_seconds=hours * 3600,
        steps=(RouteStep(0, 2, distance, hours * 3600),),
    )


class FakeGeocoder:
    def __init__(self, error: Exception | None = None) -> None:
        self.error = error
        self.calls: list[tuple[str, str]] = []

    def geocode(self, query: str, field: str) -> Location:
        self.calls.append((query, field))
        if self.error:
            raise self.error
        return DENVER if field == "origin" else SALT_LAKE_CITY


class FakeRouter:
    def __init__(
        self,
        routes: Sequence[Route] = (route(1, 536.2, 7.9), route(2, 527.2, 8.2)),
        warnings: tuple[str, ...] = (
            "The routing provider returned 2 of up to 3 requested routes.",
        ),
        error: Exception | None = None,
    ) -> None:
        self.result = RoutingResult(tuple(routes), warnings)
        self.error = error
        self.calls: list[tuple[Location, Location]] = []

    def get_routes(self, origin: Location, destination: Location) -> RoutingResult:
        self.calls.append((origin, destination))
        if self.error:
            raise self.error
        return self.result


Conditions = tuple[float | None, float | None, float | None]


class FakeWeather:
    """Applies `conditions(checkpoint)` as each checkpoint's ETA-matched weather."""

    def __init__(
        self,
        conditions: Callable[[Checkpoint], Conditions] = lambda cp: (10.0, 0.0, 0.0),
        warnings: tuple[str, ...] = (),
        error: Exception | None = None,
    ) -> None:
        self.conditions = conditions
        self.warnings = warnings
        self.error = error
        self.calls: list[tuple[list[Checkpoint], datetime]] = []

    def apply(
        self, checkpoints: Sequence[Checkpoint], departure: datetime
    ) -> CheckpointWeatherResult:
        self.calls.append((list(checkpoints), departure))
        if self.error:
            raise self.error
        updated = []
        for cp in checkpoints:
            wind, rain, snow = self.conditions(cp)
            known = sum(v is not None for v in (wind, rain, snow))
            status = (
                DataStatus.AVAILABLE
                if known == 3
                else DataStatus.PARTIAL
                if known
                else DataStatus.UNAVAILABLE
            )
            updated.append(
                dataclasses.replace(
                    cp,
                    forecast_timestamp=cp.estimated_arrival_time if known else None,
                    wind_speed_mph=wind,
                    precipitation_inches_per_hour=rain,
                    snowfall_inches_per_hour=snow,
                    data_status=status,
                )
            )
        return CheckpointWeatherResult(tuple(updated), self.warnings)


def use_case(
    geocoder: FakeGeocoder | None = None,
    router: FakeRouter | None = None,
    weather: FakeWeather | None = None,
) -> AnalyzeTripUseCase:
    return AnalyzeTripUseCase(
        geocoder=geocoder or FakeGeocoder(),  # type: ignore[arg-type]
        router=router or FakeRouter(),  # type: ignore[arg-type]
        weather=weather or FakeWeather(),  # type: ignore[arg-type]
    )


# Wiring


def test_services_are_called_in_order_with_each_others_results() -> None:
    geocoder, router, weather = FakeGeocoder(), FakeRouter(), FakeWeather()

    use_case(geocoder, router, weather).execute(trip())

    assert geocoder.calls == [("Denver, CO", "origin"), ("Salt Lake City, UT", "destination")]
    assert router.calls == [(DENVER, SALT_LAKE_CITY)]
    ((checkpoints, departure),) = weather.calls  # one weather fetch for all routes
    assert departure == DEPARTURE
    assert {cp.route_id for cp in checkpoints} == {"route-1", "route-2"}


def test_analysis_contains_every_route_in_provider_order() -> None:
    analysis = use_case().execute(trip())

    assert [r.route.id for r in analysis.routes] == ["route-1", "route-2"]
    assert (analysis.origin, analysis.destination) == (DENVER, SALT_LAKE_CITY)
    assert analysis.trip == trip()
    for analyzed in analysis.routes:
        assert all(cp.route_id == analyzed.route.id for cp in analyzed.checkpoints)
        assert analyzed.checkpoints[0].distance_from_origin_miles == 0
        assert analyzed.checkpoints[-1].distance_from_origin_miles == analyzed.route.distance_miles
        assert analyzed.metrics.distance_miles == analyzed.route.distance_miles


def test_route_arrival_time_is_departure_plus_duration() -> None:
    analysis = use_case().execute(trip())

    for analyzed in analysis.routes:
        assert analyzed.estimated_arrival_time == DEPARTURE + timedelta(
            seconds=analyzed.route.duration_seconds
        )
        assert analyzed.estimated_arrival_time == analyzed.checkpoints[-1].estimated_arrival_time


@pytest.mark.parametrize(("interval", "count"), [(10, 55), (25, 23), (50, 12)])
def test_checkpoint_interval_is_used(interval: int, count: int) -> None:
    analysis = use_case().execute(trip(checkpoint_interval_miles=interval))

    assert len(analysis.routes[0].checkpoints) == count  # 536.2 miles


def test_forecast_window_covers_48_hours_after_departure() -> None:
    analysis = use_case().execute(trip())

    assert analysis.forecast_window_start == DEPARTURE
    assert analysis.forecast_window_end == DEPARTURE + timedelta(hours=48)


# Risk, metrics, and recommendation


def test_cargo_weight_reaches_the_risk_assessment() -> None:
    weather = FakeWeather(conditions=lambda cp: (40.0, 0.0, 0.0))  # HIGH; SEVERE above 40,000 lb

    light = use_case(weather=weather).execute(trip(load_weight_lbs=40_000.0))
    heavy = use_case(weather=weather).execute(trip(load_weight_lbs=40_001.0))

    assert light.routes[0].checkpoints[1].final_risk == RiskLevel.HIGH
    assert heavy.routes[0].checkpoints[1].final_risk == RiskLevel.SEVERE
    assert heavy.routes[0].metrics.severe_miles == pytest.approx(536.2)


def test_safer_route_is_recommended_over_a_faster_one() -> None:
    # Route A is faster but has severe snow; Route B is calm.
    def conditions(cp: Checkpoint) -> Conditions:
        return (10.0, 0.0, 2.5) if cp.route_id == "route-1" else (10.0, 0.0, 0.0)

    analysis = use_case(weather=FakeWeather(conditions)).execute(trip())

    assert analysis.recommendation is not None
    assert analysis.recommendation.ranked_route_ids == ("route-2", "route-1")
    assert analysis.routes[0].metrics.severe_miles == pytest.approx(536.2)
    assert analysis.recommendation.ranking_reasons[0].startswith("Route B is recommended")


def test_hourly_forecasts_are_risk_assessed() -> None:
    def with_series(cp: Checkpoint) -> Conditions:
        return (60.0, 0.0, 0.0)

    weather = FakeWeather(with_series)
    analysis = use_case(weather=weather).execute(trip())

    # FakeWeather leaves the hourly series empty; the use case still assesses each checkpoint.
    assert analysis.routes[0].checkpoints[1].wind_risk == RiskLevel.NO_TRAVEL
    assert "NO_TRAVEL conditions" in analysis.recommendation.warnings[0]  # type: ignore[union-attr]


# Partial results


def test_provider_warnings_combine_routing_and_weather() -> None:
    weather = FakeWeather(warnings=("Weather forecasts could not be retrieved for 5 of 40 …",))

    analysis = use_case(weather=weather).execute(trip())

    assert analysis.provider_warnings == (
        "The routing provider returned 2 of up to 3 requested routes.",
        "Weather forecasts could not be retrieved for 5 of 40 …",
    )


def test_partial_weather_is_reported_as_unknown_not_safe() -> None:
    # Route A's checkpoints beyond mile 300 have no weather.
    def conditions(cp: Checkpoint) -> Conditions:
        if cp.route_id == "route-1" and cp.distance_from_origin_miles > 300:
            return (None, None, None)
        return (10.0, 0.0, 0.0)

    analysis = use_case(weather=FakeWeather(conditions)).execute(trip())

    metrics = analysis.routes[0].metrics
    assert metrics.unknown_miles == pytest.approx(536.2 - 300)
    assert metrics.weather_coverage_percent < 100
    assert any("risk is unknown" in w for w in analysis.recommendation.warnings)  # type: ignore[union-attr]


# Failures propagate as analysis errors


def test_geocoding_errors_stop_the_analysis() -> None:
    router = FakeRouter()
    error = GeocodingAmbiguousError("origin", [DENVER, SALT_LAKE_CITY])

    with pytest.raises(GeocodingAmbiguousError):
        use_case(geocoder=FakeGeocoder(error=error), router=router).execute(trip())
    assert router.calls == []


def test_routing_errors_stop_the_analysis() -> None:
    weather = FakeWeather()

    with pytest.raises(NoRouteFoundError):
        use_case(router=FakeRouter(error=NoRouteFoundError()), weather=weather).execute(trip())
    assert weather.calls == []


def test_complete_weather_failure_stops_the_analysis() -> None:
    with pytest.raises(ProviderTimeoutError):
        use_case(weather=FakeWeather(error=ProviderTimeoutError())).execute(trip())


def test_default_services_are_the_real_integrations() -> None:
    real = AnalyzeTripUseCase()

    assert isinstance(real._geocoder, OrsGeocodingService)
    assert isinstance(real._router, ValhallaRoutingService)
    assert isinstance(real._weather, CheckpointWeatherService)


# Checkpoint grouping by position


def test_each_route_keeps_its_own_checkpoints_in_order() -> None:
    routes = (route(1, 60.0, 1.0), route(2, 40.0, 0.8), route(3, 75.0, 1.2))
    weather = FakeWeather()

    analysis = use_case(router=FakeRouter(routes=routes), weather=weather).execute(trip())

    ((sent, _),) = weather.calls
    expected = {r.id: [cp.id for cp in sent if cp.route_id == r.id] for r in routes}
    for analyzed in analysis.routes:
        ids = [cp.id for cp in analyzed.checkpoints]
        assert ids == expected[analyzed.route.id]
        assert ids == [f"{analyzed.route.id}-cp-{n}" for n in range(len(ids))]
    # 25-mile interval: 0-25-50-60, 0-25-40, 0-25-50-75 (75 is a multiple, so not duplicated).
    assert [len(a.checkpoints) for a in analysis.routes] == [4, 3, 4]


def test_grouping_does_not_depend_on_the_returned_route_ids() -> None:
    # A weather service that (incorrectly) relabels route ids must not move checkpoints
    # between routes: grouping is by position. Metrics then reject the mismatched ids.
    class RelabellingWeather(FakeWeather):
        def apply(self, checkpoints, departure):  # type: ignore[no-untyped-def]
            result = super().apply(checkpoints, departure)
            relabelled = tuple(
                dataclasses.replace(cp, route_id="route-1") for cp in result.checkpoints
            )
            return CheckpointWeatherResult(relabelled, result.warnings)

    with pytest.raises(ValueError, match="route-2"):
        use_case(weather=RelabellingWeather()).execute(trip())


def test_weather_returning_a_different_number_of_checkpoints_is_rejected() -> None:
    class DroppingWeather(FakeWeather):
        def apply(self, checkpoints, departure):  # type: ignore[no-untyped-def]
            result = super().apply(checkpoints, departure)
            return CheckpointWeatherResult(result.checkpoints[:-1], result.warnings)

    with pytest.raises(ValueError, match="one checkpoint per checkpoint given"):
        use_case(weather=DroppingWeather()).execute(trip())


# HTTP client lifecycle


def test_every_use_case_shares_the_single_process_wide_http_client() -> None:
    first, second = AnalyzeTripUseCase(), AnalyzeTripUseCase()  # e.g. two API requests

    clients = {
        id(client)
        for uc in (first, second)
        for client in (uc._geocoder._client, uc._router._client, uc._weather._forecasts._client)
    }

    assert clients == {id(get_http_client())}
