"""The trip analysis use case: the single orchestrator that connects every module.

Geocode, route, place checkpoints, apply weather, assess risk, aggregate route metrics, and
rank. Each step is delegated to its module; no business rule lives here.

Failures: geocoding, routing, and complete weather failures raise the shared analysis
errors (mapped to HTTP statuses by the API). Partial results are returned with warnings:
fewer routes than requested, or weather batches that could not be retrieved.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta

from modules.checkpoints.services.checkpoint_generation import generate_checkpoints
from modules.geocoding.services.ors_geocoding import OrsGeocodingService
from modules.recommendation.domain.metrics import route_metrics
from modules.recommendation.domain.ranking import recommend
from modules.risk.domain.assessment import assess_checkpoint
from modules.routing.services.valhalla_routing import ValhallaRoutingService
from modules.weather.services.checkpoint_weather import SERIES_HOURS, CheckpointWeatherService
from shared.datetimes import add_elapsed
from shared.types import Checkpoint, Location, Recommendation, Route, RouteMetrics, TripInput


@dataclass(frozen=True)
class AnalyzedRoute:
    route: Route
    estimated_arrival_time: datetime
    checkpoints: tuple[Checkpoint, ...]
    metrics: RouteMetrics


@dataclass(frozen=True)
class TripAnalysis:
    trip: TripInput
    origin: Location
    destination: Location
    routes: tuple[AnalyzedRoute, ...]  # in provider order
    recommendation: Recommendation | None
    forecast_window_start: datetime
    forecast_window_end: datetime
    provider_warnings: tuple[str, ...]


class AnalyzeTripUseCase:
    def __init__(
        self,
        geocoder: OrsGeocodingService | None = None,
        router: ValhallaRoutingService | None = None,
        weather: CheckpointWeatherService | None = None,
    ) -> None:
        self._geocoder = geocoder or OrsGeocodingService()
        self._router = router or ValhallaRoutingService()
        self._weather = weather or CheckpointWeatherService()

    def execute(self, trip: TripInput) -> TripAnalysis:
        origin = self._geocoder.geocode(trip.origin, "origin")
        destination = self._geocoder.geocode(trip.destination, "destination")

        routing = self._router.get_routes(origin, destination)
        generated = [
            generate_checkpoints(route, trip.checkpoint_interval_miles, trip.departure_time)
            for route in routing.routes
        ]

        # One weather fetch for every route, so shared locations are requested once. The
        # weather service returns checkpoints in the order given, so each route's checkpoints
        # are recovered by position rather than by route id.
        flattened = [cp for checkpoints in generated for cp in checkpoints]
        weather = self._weather.apply(flattened, trip.departure_time)
        if len(weather.checkpoints) != len(flattened):
            raise ValueError("the weather service must return one checkpoint per checkpoint given")
        assessed = [assess_checkpoint(cp, trip.load_weight_lbs) for cp in weather.checkpoints]

        analyzed = []
        offset = 0
        for route, original in zip(routing.routes, generated, strict=True):
            route_checkpoints = tuple(assessed[offset : offset + len(original)])
            offset += len(original)
            analyzed.append(
                AnalyzedRoute(
                    route=route,
                    estimated_arrival_time=route_checkpoints[-1].estimated_arrival_time,
                    checkpoints=route_checkpoints,
                    metrics=route_metrics(route, route_checkpoints),
                )
            )

        return TripAnalysis(
            trip=trip,
            origin=origin,
            destination=destination,
            routes=tuple(analyzed),
            recommendation=recommend(routing.routes, {a.route.id: a.metrics for a in analyzed}),
            forecast_window_start=trip.departure_time,
            forecast_window_end=add_elapsed(trip.departure_time, timedelta(hours=SERIES_HOURS)),
            provider_warnings=routing.warnings + weather.warnings,
        )
