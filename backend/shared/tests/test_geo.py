import pytest

from shared.geo import coordinate_from_lon_lat, distance_miles
from shared.types import Coordinate


def test_distance_between_known_cities() -> None:
    denver = Coordinate(39.7392, -104.9903)
    salt_lake_city = Coordinate(40.7608, -111.8910)

    assert distance_miles(denver, salt_lake_city) == pytest.approx(371, abs=2)
    assert distance_miles(denver, denver) == 0


def test_geojson_position_is_converted_to_lat_lon() -> None:
    assert coordinate_from_lon_lat([-104.99, 39.74, 1600.0]) == Coordinate(39.74, -104.99)


@pytest.mark.parametrize(
    "value",
    [None, [], [1.0], [-104.99, 91.0], [181.0, 39.7], ["a", 39.7], [True, 39.7], [float("nan"), 1]],
)
def test_invalid_positions_are_rejected(value: object) -> None:
    with pytest.raises(ValueError):
        coordinate_from_lon_lat(value)
