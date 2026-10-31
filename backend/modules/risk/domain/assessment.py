"""Weather risk assessment (FR-06 to FR-08). Pure functions; missing values are UNKNOWN,
never LOW."""

import dataclasses
import math
from collections.abc import Iterable
from dataclasses import dataclass

from modules.risk.domain.thresholds import (
    CARGO_NO_TRAVEL_WEIGHT_LBS,
    CARGO_NO_TRAVEL_WIND_MPH,
    CARGO_SEVERE_WEIGHT_LBS,
    CARGO_SEVERE_WIND_MPH,
    RAIN_BANDS_INCHES_PER_HOUR,
    SEVERITY_ORDER,
    SNOW_BANDS_INCHES_PER_HOUR,
    WIND_BANDS_MPH,
    Band,
)
from shared.types import Checkpoint, HourlyForecast, RiskLevel


@dataclass(frozen=True)
class RiskAssessment:
    wind_risk: RiskLevel
    rain_risk: RiskLevel
    snow_risk: RiskLevel
    final_risk: RiskLevel
    missing_factors: tuple[str, ...]  # weather values that were unavailable


def classify(value: float | None, bands: tuple[Band, ...]) -> RiskLevel:
    """The risk band for `value`; UNKNOWN when the value is missing."""
    if value is None:
        return RiskLevel.UNKNOWN
    if not math.isfinite(value) or value < 0:
        raise ValueError(f"weather value must be a non-negative number, got {value!r}")
    for band in bands:
        if value < band.upper or (band.inclusive and value == band.upper):
            return band.level
    return RiskLevel.NO_TRAVEL


def wind_risk(wind_speed_mph: float | None, load_weight_lbs: float) -> RiskLevel:
    """Wind risk with the cargo-weight rules applied. Unknown wind stays UNKNOWN for every
    load: a missing value never counts as safe."""
    _require_valid_weight(load_weight_lbs)
    risk = classify(wind_speed_mph, WIND_BANDS_MPH)
    if wind_speed_mph is None:
        return risk
    if wind_speed_mph >= CARGO_NO_TRAVEL_WIND_MPH and load_weight_lbs > CARGO_NO_TRAVEL_WEIGHT_LBS:
        return RiskLevel.NO_TRAVEL
    if wind_speed_mph >= CARGO_SEVERE_WIND_MPH and load_weight_lbs > CARGO_SEVERE_WEIGHT_LBS:
        return highest_risk([risk, RiskLevel.SEVERE])
    return risk


def rain_risk(precipitation_inches_per_hour: float | None) -> RiskLevel:
    return classify(precipitation_inches_per_hour, RAIN_BANDS_INCHES_PER_HOUR)


def snow_risk(snowfall_inches_per_hour: float | None) -> RiskLevel:
    return classify(snowfall_inches_per_hour, SNOW_BANDS_INCHES_PER_HOUR)


def highest_risk(risks: Iterable[RiskLevel]) -> RiskLevel:
    """The most severe known risk, by explicit severity order; UNKNOWN if none is known."""
    known = [risk for risk in risks if risk is not RiskLevel.UNKNOWN]
    if not known:
        return RiskLevel.UNKNOWN
    return max(known, key=SEVERITY_ORDER.index)


def assess(
    wind_speed_mph: float | None,
    precipitation_inches_per_hour: float | None,
    snowfall_inches_per_hour: float | None,
    load_weight_lbs: float,
) -> RiskAssessment:
    factors = {
        "wind speed": wind_risk(wind_speed_mph, load_weight_lbs),
        "precipitation": rain_risk(precipitation_inches_per_hour),
        "snowfall": snow_risk(snowfall_inches_per_hour),
    }
    return RiskAssessment(
        wind_risk=factors["wind speed"],
        rain_risk=factors["precipitation"],
        snow_risk=factors["snowfall"],
        final_risk=highest_risk(factors.values()),
        missing_factors=tuple(name for name, risk in factors.items() if risk is RiskLevel.UNKNOWN),
    )


def assess_checkpoint(checkpoint: Checkpoint, load_weight_lbs: float) -> Checkpoint:
    """The checkpoint with factor and final risks for its ETA-matched weather and for every
    hourly forecast entry. Its warnings are replaced, so assessing twice is harmless."""
    result = assess(
        checkpoint.wind_speed_mph,
        checkpoint.precipitation_inches_per_hour,
        checkpoint.snowfall_inches_per_hour,
        load_weight_lbs,
    )
    return dataclasses.replace(
        checkpoint,
        wind_risk=result.wind_risk,
        rain_risk=result.rain_risk,
        snow_risk=result.snow_risk,
        final_risk=result.final_risk,
        warnings=incomplete_data_warnings(result),
        hourly_forecasts=tuple(
            assess_hourly_forecast(entry, load_weight_lbs) for entry in checkpoint.hourly_forecasts
        ),
    )


def assess_hourly_forecast(entry: HourlyForecast, load_weight_lbs: float) -> HourlyForecast:
    result = assess(
        entry.wind_speed_mph,
        entry.precipitation_inches_per_hour,
        entry.snowfall_inches_per_hour,
        load_weight_lbs,
    )
    return dataclasses.replace(
        entry,
        wind_risk=result.wind_risk,
        rain_risk=result.rain_risk,
        snow_risk=result.snow_risk,
        final_risk=result.final_risk,
    )


def incomplete_data_warnings(result: RiskAssessment) -> tuple[str, ...]:
    if not result.missing_factors:
        return ()
    if result.final_risk is RiskLevel.UNKNOWN:
        return ("No weather data is available at this checkpoint, so its risk is UNKNOWN.",)
    missing = " and ".join(result.missing_factors)
    warning = (
        f"Incomplete weather data: {missing} unavailable. "
        "The risk shown is based on the available data only."
    )
    if "wind speed" in result.missing_factors:
        warning += " Cargo-weight wind limits could not be checked."
    return (warning,)


def _require_valid_weight(load_weight_lbs: float) -> None:
    if not (math.isfinite(load_weight_lbs) and load_weight_lbs > 0):
        raise ValueError(f"load weight must be a positive number, got {load_weight_lbs!r}")
