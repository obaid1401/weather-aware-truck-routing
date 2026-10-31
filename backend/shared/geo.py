import math

from shared.types import Coordinate
from shared.validation import finite_number

EARTH_RADIUS_MILES = 3958.7613


def distance_miles(a: Coordinate, b: Coordinate) -> float:
    """Great-circle (haversine) distance between two coordinates."""
    lat1, lon1, lat2, lon2 = map(math.radians, (a.latitude, a.longitude, b.latitude, b.longitude))
    h = (
        math.sin((lat2 - lat1) / 2) ** 2
        + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2
    )
    return 2 * EARTH_RADIUS_MILES * math.asin(math.sqrt(h))


def interpolate(a: Coordinate, b: Coordinate, fraction: float) -> Coordinate:
    """Point at `fraction` (0..1) of the great-circle path from `a` to `b`."""
    if not 0 <= fraction <= 1:
        raise ValueError(f"fraction must be between 0 and 1, got {fraction!r}")
    if fraction == 0:
        return a
    if fraction == 1:
        return b
    lat1, lon1, lat2, lon2 = map(math.radians, (a.latitude, a.longitude, b.latitude, b.longitude))
    angle = distance_miles(a, b) / EARTH_RADIUS_MILES
    if angle < 1e-12:
        return a
    if math.pi - angle < 1e-9:
        # Every great circle through antipodal points is equally short, so no path is defined.
        raise ValueError("cannot interpolate between antipodal points")

    weight_a = math.sin((1 - fraction) * angle) / math.sin(angle)
    weight_b = math.sin(fraction * angle) / math.sin(angle)
    x = weight_a * math.cos(lat1) * math.cos(lon1) + weight_b * math.cos(lat2) * math.cos(lon2)
    y = weight_a * math.cos(lat1) * math.sin(lon1) + weight_b * math.cos(lat2) * math.sin(lon2)
    z = weight_a * math.sin(lat1) + weight_b * math.sin(lat2)
    return Coordinate(math.degrees(math.atan2(z, math.hypot(x, y))), math.degrees(math.atan2(y, x)))


def coordinate_from_lon_lat(value: object) -> Coordinate:
    """Converts a GeoJSON `[longitude, latitude, ...]` position, validating its range."""
    if not isinstance(value, list | tuple) or len(value) < 2:
        raise ValueError(f"expected a [longitude, latitude] position, got {value!r}")
    longitude, latitude = finite_number(value[0]), finite_number(value[1])
    if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
        raise ValueError(f"position out of range: {value!r}")
    return Coordinate(latitude, longitude)
