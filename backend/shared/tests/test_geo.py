import pytest

from shared.geo import coordinate_from_lon_lat, distance_miles, interpolate
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


# Great-circle interpolation


def test_interpolate_along_the_equator() -> None:
    point = interpolate(Coordinate(0.0, 0.0), Coordinate(0.0, 10.0), 0.5)

    assert point.latitude == pytest.approx(0.0, abs=1e-9)
    assert point.longitude == pytest.approx(5.0)


def test_interpolated_point_is_the_requested_fraction_of_the_distance() -> None:
    denver, salt_lake_city = Coordinate(39.7392, -104.9903), Coordinate(40.7608, -111.8910)

    point = interpolate(denver, salt_lake_city, 0.3)

    total = distance_miles(denver, salt_lake_city)
    assert distance_miles(denver, point) == pytest.approx(0.3 * total)
    assert distance_miles(point, salt_lake_city) == pytest.approx(0.7 * total)


def test_interpolation_endpoints_are_exact() -> None:
    a, b = Coordinate(39.7392, -104.9903), Coordinate(40.7608, -111.8910)

    assert interpolate(a, b, 0) == a
    assert interpolate(a, b, 1) == b


def test_interpolating_a_zero_length_segment_returns_the_point() -> None:
    a = Coordinate(39.7392, -104.9903)

    assert interpolate(a, a, 0.5) == a


@pytest.mark.parametrize("fraction", [-0.1, 1.1])
def test_interpolation_fraction_must_be_between_0_and_1(fraction: float) -> None:
    with pytest.raises(ValueError):
        interpolate(Coordinate(0, 0), Coordinate(0, 1), fraction)


def test_interpolating_between_antipodal_points_is_rejected() -> None:
    with pytest.raises(ValueError, match="antipodal"):
        interpolate(Coordinate(0.0, 0.0), Coordinate(0.0, 180.0), 0.5)


def test_interpolating_nearly_antipodal_points_still_works() -> None:
    point = interpolate(Coordinate(0.0, 0.0), Coordinate(0.0, 179.0), 0.5)

    assert point.latitude == pytest.approx(0.0, abs=1e-9)
    assert point.longitude == pytest.approx(89.5)
