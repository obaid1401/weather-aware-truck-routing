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


def coordinate_from_lon_lat(value: object) -> Coordinate:
    """Converts a GeoJSON `[longitude, latitude, ...]` position, validating its range."""
    if not isinstance(value, list | tuple) or len(value) < 2:
        raise ValueError(f"expected a [longitude, latitude] position, got {value!r}")
    longitude, latitude = finite_number(value[0]), finite_number(value[1])
    if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
        raise ValueError(f"position out of range: {value!r}")
    return Coordinate(latitude, longitude)
