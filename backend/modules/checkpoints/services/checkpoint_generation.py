from datetime import datetime

from modules.checkpoints.domain.eta import arrival_time, elapsed_times, require_timezone_aware
from modules.checkpoints.domain.placement import checkpoint_distances, cumulative_distances, locate
from shared.geo import interpolate
from shared.types import Checkpoint, Route


def generate_checkpoints(
    route: Route, interval_miles: float, departure_time: datetime
) -> tuple[Checkpoint, ...]:
    """Checkpoints at mile 0, every `interval_miles` along the route, and the destination.

    Positions are interpolated along the route geometry; arrival times come from the
    route's step durations when available, otherwise from its average speed.
    """
    require_timezone_aware(departure_time)
    targets = checkpoint_distances(route.distance_miles, interval_miles)
    distances = cumulative_distances(route)
    elapsed = elapsed_times(route, distances)

    checkpoints = []
    for number, target in enumerate(targets):
        index, fraction = locate(distances, target)
        position = interpolate(route.geometry[index], route.geometry[index + 1], fraction)
        checkpoints.append(
            Checkpoint(
                id=f"{route.id}-cp-{number}",
                route_id=route.id,
                distance_from_origin_miles=target,
                latitude=position.latitude,
                longitude=position.longitude,
                estimated_arrival_time=arrival_time(departure_time, elapsed.at(index, fraction)),
            )
        )
    return tuple(checkpoints)
