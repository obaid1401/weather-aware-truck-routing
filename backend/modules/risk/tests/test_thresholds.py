"""Threshold boundaries for every factor (FR-06)."""

import pytest

from modules.risk.domain.assessment import rain_risk, snow_risk, wind_risk
from modules.risk.domain.thresholds import RISK_SCORES, SEVERITY_ORDER
from modules.weather.services.open_meteo import CM_PER_INCH, KMH_PER_MPH, MM_PER_INCH
from shared.types import RiskLevel

LOW, MODERATE, HIGH, SEVERE, NO_TRAVEL, UNKNOWN = (
    RiskLevel.LOW,
    RiskLevel.MODERATE,
    RiskLevel.HIGH,
    RiskLevel.SEVERE,
    RiskLevel.NO_TRAVEL,
    RiskLevel.UNKNOWN,
)
LIGHT_LOAD = 10_000.0  # below every cargo-weight rule


@pytest.mark.parametrize(
    ("mph", "expected"),
    [
        (0.0, LOW),
        (24.99, LOW),
        (25.0, MODERATE),
        (34.99, MODERATE),
        (35.0, HIGH),
        (44.99, HIGH),
        (45.0, SEVERE),
        (54.99, SEVERE),
        (55.0, NO_TRAVEL),  # exactly 55 mph is NO_TRAVEL
        (80.0, NO_TRAVEL),
    ],
)
def test_wind_thresholds(mph: float, expected: RiskLevel) -> None:
    assert wind_risk(mph, LIGHT_LOAD) == expected


@pytest.mark.parametrize(
    ("inches", "expected"),
    [
        (0.0, LOW),
        (0.0999, LOW),
        (0.10, MODERATE),
        (0.2499, MODERATE),
        (0.25, HIGH),
        (0.4999, HIGH),
        (0.50, SEVERE),
        (1.00, SEVERE),  # exactly 1.00 in/hr is SEVERE
        (1.0001, NO_TRAVEL),
        (2.0, NO_TRAVEL),
    ],
)
def test_rain_thresholds(inches: float, expected: RiskLevel) -> None:
    assert rain_risk(inches) == expected


@pytest.mark.parametrize(
    ("inches", "expected"),
    [
        (0.0, LOW),
        (0.4999, LOW),
        (0.5, MODERATE),
        (0.9999, MODERATE),
        (1.0, HIGH),
        (1.9999, HIGH),
        (2.0, SEVERE),
        (3.0, SEVERE),  # exactly 3.00 in/hr is SEVERE
        (3.0001, NO_TRAVEL),
        (6.0, NO_TRAVEL),
    ],
)
def test_snow_thresholds(inches: float, expected: RiskLevel) -> None:
    assert snow_risk(inches) == expected


@pytest.mark.parametrize(
    ("provider_value", "divisor", "classify", "expected"),
    [
        # Values in Open-Meteo's own units that convert exactly onto a boundary.
        (12.7, MM_PER_INCH, rain_risk, SEVERE),  # 0.50 in
        (25.4, MM_PER_INCH, rain_risk, SEVERE),  # 1.00 in
        (25.5, MM_PER_INCH, rain_risk, NO_TRAVEL),
        (2.5, MM_PER_INCH, rain_risk, LOW),  # 0.098 in
        (2.6, MM_PER_INCH, rain_risk, MODERATE),  # 0.102 in
        (1.27, CM_PER_INCH, snow_risk, MODERATE),  # 0.5 in
        (2.54, CM_PER_INCH, snow_risk, HIGH),  # 1.0 in
        (5.08, CM_PER_INCH, snow_risk, SEVERE),  # 2.0 in
        (7.62, CM_PER_INCH, snow_risk, SEVERE),  # 3.0 in
        (7.63, CM_PER_INCH, snow_risk, NO_TRAVEL),
    ],
)
def test_converted_provider_values_land_on_the_right_side_of_boundaries(
    provider_value: float, divisor: float, classify: object, expected: RiskLevel
) -> None:
    assert classify(provider_value / divisor) == expected  # type: ignore[operator]


@pytest.mark.parametrize(("kmh", "expected"), [(88.5, SEVERE), (88.6, NO_TRAVEL)])
def test_converted_wind_near_55_mph(kmh: float, expected: RiskLevel) -> None:
    # 55 mph is 88.51 km/h; Open-Meteo reports wind to 0.1 km/h.
    assert wind_risk(kmh / KMH_PER_MPH, LIGHT_LOAD) == expected


def test_missing_values_are_unknown_never_low() -> None:
    assert wind_risk(None, LIGHT_LOAD) == UNKNOWN
    assert rain_risk(None) == UNKNOWN
    assert snow_risk(None) == UNKNOWN


@pytest.mark.parametrize("value", [-0.01, float("nan"), float("inf")])
def test_invalid_weather_values_are_rejected(value: float) -> None:
    for classify in (rain_risk, snow_risk):
        with pytest.raises(ValueError):
            classify(value)
    with pytest.raises(ValueError):
        wind_risk(value, LIGHT_LOAD)


def test_severity_order_and_scores() -> None:
    assert SEVERITY_ORDER == (LOW, MODERATE, HIGH, SEVERE, NO_TRAVEL)
    assert [RISK_SCORES[level] for level in SEVERITY_ORDER] == [1, 2, 3, 4, 5]
    assert UNKNOWN not in RISK_SCORES
