"""Cargo-weight rules (FR-07), final risk and unknown data (FR-08), and checkpoint and
hourly assessment."""

from datetime import UTC, datetime, timedelta

import pytest

from modules.risk.domain.assessment import (
    assess,
    assess_checkpoint,
    assess_hourly_forecast,
    highest_risk,
    wind_risk,
)
from shared.types import Checkpoint, DataStatus, HourlyForecast, RiskLevel

LOW, MODERATE, HIGH, SEVERE, NO_TRAVEL, UNKNOWN = (
    RiskLevel.LOW,
    RiskLevel.MODERATE,
    RiskLevel.HIGH,
    RiskLevel.SEVERE,
    RiskLevel.NO_TRAVEL,
    RiskLevel.UNKNOWN,
)
NOW = datetime(2026, 11, 5, 15, 0, tzinfo=UTC)

# Cargo-weight rules


@pytest.mark.parametrize(
    ("mph", "lbs", "expected"),
    [
        # >=55 mph: NO_TRAVEL for every load.
        (55.0, 1.0, NO_TRAVEL),
        (60.0, 80_000.0, NO_TRAVEL),
        # 45 to <55 mph: NO_TRAVEL only above 30,000 lb.
        (45.0, 30_000.0, SEVERE),  # exactly 30,000 lb: rule not triggered
        (45.0, 30_000.01, NO_TRAVEL),
        (54.99, 30_001.0, NO_TRAVEL),
        (50.0, 20_000.0, SEVERE),
        (45.0, 40_001.0, NO_TRAVEL),  # both rules apply; the stricter wins
        # 35 to <45 mph: at least SEVERE only above 40,000 lb.
        (35.0, 40_000.0, HIGH),  # exactly 40,000 lb: rule not triggered
        (35.0, 40_000.01, SEVERE),
        (44.99, 40_001.0, SEVERE),
        (40.0, 35_000.0, HIGH),  # over 30,000 but the 45 mph rule does not apply
        # Below 35 mph the load never changes the risk.
        (34.99, 80_000.0, MODERATE),
        (20.0, 80_000.0, LOW),
    ],
)
def test_cargo_weight_rules(mph: float, lbs: float, expected: RiskLevel) -> None:
    assert wind_risk(mph, lbs) == expected


@pytest.mark.parametrize("lbs", [1.0, 30_001.0, 80_000.0])
def test_unknown_wind_is_unknown_for_every_load(lbs: float) -> None:
    assert wind_risk(None, lbs) == UNKNOWN


@pytest.mark.parametrize("lbs", [0.0, -1.0, float("nan"), float("inf")])
def test_invalid_load_weight_is_rejected(lbs: float) -> None:
    with pytest.raises(ValueError):
        wind_risk(20.0, lbs)


# Final risk


def test_highest_risk_uses_severity_not_alphabetical_order() -> None:
    # Alphabetically "LOW" > "HIGH" and "SEVERE" > "NO_TRAVEL"; by severity they are not.
    assert highest_risk([LOW, HIGH]) == HIGH
    assert highest_risk([SEVERE, NO_TRAVEL]) == NO_TRAVEL
    assert highest_risk([MODERATE, UNKNOWN, LOW]) == MODERATE
    assert highest_risk([UNKNOWN, UNKNOWN]) == UNKNOWN
    assert highest_risk([]) == UNKNOWN


def test_final_risk_is_the_highest_factor_after_cargo_rules() -> None:
    # Wind 40 mph is HIGH, raised to SEVERE by a 45,000 lb load; rain is MODERATE.
    result = assess(40.0, 0.15, 0.0, 45_000.0)

    assert (result.wind_risk, result.rain_risk, result.snow_risk) == (SEVERE, MODERATE, LOW)
    assert result.final_risk == SEVERE
    assert result.missing_factors == ()


@pytest.mark.parametrize(
    ("values", "expected_final", "missing"),
    [
        ((None, 0.30, 0.0), HIGH, ("wind speed",)),
        ((None, 0.0, 0.0), LOW, ("wind speed",)),  # known factors say LOW; a warning flags the gap
        ((30.0, None, None), MODERATE, ("precipitation", "snowfall")),
        ((None, None, 2.5), SEVERE, ("wind speed", "precipitation")),
        ((None, None, None), UNKNOWN, ("wind speed", "precipitation", "snowfall")),
    ],
)
def test_partial_and_missing_data(
    values: tuple[float | None, ...], expected_final: RiskLevel, missing: tuple[str, ...]
) -> None:
    result = assess(*values, 45_000.0)

    assert result.final_risk == expected_final
    assert result.missing_factors == missing


def test_zero_is_data_not_missing() -> None:
    result = assess(0.0, 0.0, 0.0, 45_000.0)

    assert result.final_risk == LOW
    assert result.missing_factors == ()


# Checkpoints and hourly entries


def hourly(
    offset: int, wind: float | None, rain: float | None, snow: float | None
) -> HourlyForecast:
    known = sum(value is not None for value in (wind, rain, snow))
    return HourlyForecast(
        hour_offset=offset,
        target_time=NOW + timedelta(hours=offset),
        forecast_timestamp=NOW + timedelta(hours=offset),
        wind_speed_mph=wind,
        precipitation_inches_per_hour=rain,
        snowfall_inches_per_hour=snow,
        data_status=(
            DataStatus.AVAILABLE
            if known == 3
            else DataStatus.PARTIAL
            if known
            else DataStatus.UNAVAILABLE
        ),
    )


def checkpoint(
    wind: float | None = 10.0,
    rain: float | None = 0.0,
    snow: float | None = 0.0,
    series: tuple[HourlyForecast, ...] = (),
) -> Checkpoint:
    return Checkpoint(
        id="route-1-cp-1",
        route_id="route-1",
        distance_from_origin_miles=25.0,
        latitude=39.7,
        longitude=-105.0,
        estimated_arrival_time=NOW,
        forecast_timestamp=NOW,
        wind_speed_mph=wind,
        precipitation_inches_per_hour=rain,
        snowfall_inches_per_hour=snow,
        data_status=DataStatus.AVAILABLE,
        hourly_forecasts=series,
    )


def test_checkpoint_gets_factor_and_final_risks() -> None:
    assessed = assess_checkpoint(checkpoint(wind=47.0, rain=0.3, snow=0.0), 35_000.0)

    assert assessed.wind_risk == NO_TRAVEL  # 45-55 mph with more than 30,000 lb
    assert assessed.rain_risk == HIGH
    assert assessed.snow_risk == LOW
    assert assessed.final_risk == NO_TRAVEL
    assert assessed.warnings == ()


def test_assessment_keeps_all_other_checkpoint_fields() -> None:
    original = checkpoint(wind=30.0)

    assessed = assess_checkpoint(original, 20_000.0)

    for field in (
        "id",
        "route_id",
        "distance_from_origin_miles",
        "latitude",
        "longitude",
        "estimated_arrival_time",
        "forecast_timestamp",
        "wind_speed_mph",
        "precipitation_inches_per_hour",
        "snowfall_inches_per_hour",
        "data_status",
    ):
        assert getattr(assessed, field) == getattr(original, field)


def test_incomplete_data_warning() -> None:
    assessed = assess_checkpoint(checkpoint(wind=None, rain=0.3, snow=None), 50_000.0)

    assert assessed.final_risk == HIGH
    assert assessed.warnings == (
        "Incomplete weather data: wind speed and snowfall unavailable. The risk shown is "
        "based on the available data only. Cargo-weight wind limits could not be checked.",
    )


def test_incomplete_data_warning_without_wind_gap() -> None:
    assessed = assess_checkpoint(checkpoint(wind=10.0, rain=None, snow=0.0), 50_000.0)

    assert assessed.warnings == (
        "Incomplete weather data: precipitation unavailable. The risk shown is based on the "
        "available data only.",
    )


def test_checkpoint_without_any_weather_is_unknown() -> None:
    assessed = assess_checkpoint(checkpoint(wind=None, rain=None, snow=None), 50_000.0)

    assert (assessed.wind_risk, assessed.rain_risk, assessed.snow_risk) == (UNKNOWN,) * 3
    assert assessed.final_risk == UNKNOWN
    assert assessed.warnings == (
        "No weather data is available at this checkpoint, so its risk is UNKNOWN.",
    )


def test_assessing_twice_does_not_duplicate_warnings() -> None:
    once = assess_checkpoint(checkpoint(wind=None), 50_000.0)

    assert assess_checkpoint(once, 50_000.0) == once


def test_every_hourly_entry_is_assessed_independently() -> None:
    series = (
        hourly(0, 10.0, 0.0, 0.0),  # LOW
        hourly(1, 50.0, 0.0, 0.0),  # SEVERE, or NO_TRAVEL with more than 30,000 lb
        hourly(2, 10.0, 0.6, 0.0),  # rain SEVERE
        hourly(3, None, 0.0, 3.5),  # snow NO_TRAVEL, wind unknown
        hourly(4, None, None, None),  # UNKNOWN
    )

    assessed = assess_checkpoint(checkpoint(series=series), 35_000.0)

    assert [e.final_risk for e in assessed.hourly_forecasts] == [
        LOW,
        NO_TRAVEL,
        SEVERE,
        NO_TRAVEL,
        UNKNOWN,
    ]
    assert assessed.hourly_forecasts[1].wind_risk == NO_TRAVEL
    assert assessed.hourly_forecasts[3].wind_risk == UNKNOWN
    assert assessed.hourly_forecasts[4].rain_risk == UNKNOWN
    # The ETA-matched risk is independent of the hourly series.
    assert assessed.final_risk == LOW


def test_hourly_entry_uses_the_trip_load() -> None:
    entry = hourly(0, 40.0, 0.0, 0.0)

    assert assess_hourly_forecast(entry, 40_000.0).final_risk == HIGH
    assert assess_hourly_forecast(entry, 40_001.0).final_risk == SEVERE


def test_hourly_assessment_keeps_weather_fields() -> None:
    entry = hourly(7, 12.0, None, 0.2)

    assessed = assess_hourly_forecast(entry, 10_000.0)

    assert (
        assessed.hour_offset,
        assessed.wind_speed_mph,
        assessed.precipitation_inches_per_hour,
    ) == (
        7,
        12.0,
        None,
    )
    assert assessed.data_status == DataStatus.PARTIAL
    assert (assessed.wind_risk, assessed.rain_risk, assessed.snow_risk) == (LOW, UNKNOWN, LOW)
