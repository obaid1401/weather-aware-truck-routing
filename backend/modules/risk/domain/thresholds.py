"""Risk thresholds, severity order, and scores: the single source of truth for FR-06 to FR-09."""

from dataclasses import dataclass

from shared.types import RiskLevel


@dataclass(frozen=True)
class Band:
    """A risk band ending at `upper`. A value equal to `upper` belongs to this band only
    when `inclusive` is true; otherwise it belongs to the next band."""

    level: RiskLevel
    upper: float
    inclusive: bool = False


# A value falls in the first band it fits. Anything above the last band is NO_TRAVEL.
WIND_BANDS_MPH = (
    Band(RiskLevel.LOW, 25),
    Band(RiskLevel.MODERATE, 35),
    Band(RiskLevel.HIGH, 45),
    Band(RiskLevel.SEVERE, 55),  # exactly 55 mph is NO_TRAVEL
)
RAIN_BANDS_INCHES_PER_HOUR = (
    Band(RiskLevel.LOW, 0.10),
    Band(RiskLevel.MODERATE, 0.25),
    Band(RiskLevel.HIGH, 0.50),
    Band(RiskLevel.SEVERE, 1.00, inclusive=True),  # exactly 1.00 in/hr is SEVERE
)
SNOW_BANDS_INCHES_PER_HOUR = (
    Band(RiskLevel.LOW, 0.5),
    Band(RiskLevel.MODERATE, 1.0),
    Band(RiskLevel.HIGH, 2.0),
    Band(RiskLevel.SEVERE, 3.0, inclusive=True),  # exactly 3.00 in/hr is SEVERE
)

# Cargo-weight wind rules (FR-07). Weights use strict greater-than comparisons.
# Wind at or above this speed with cargo over the weight is NO_TRAVEL.
CARGO_NO_TRAVEL_WIND_MPH = 45.0
CARGO_NO_TRAVEL_WEIGHT_LBS = 30_000.0
# Wind at or above this speed with cargo over the weight is at least SEVERE.
CARGO_SEVERE_WIND_MPH = 35.0
CARGO_SEVERE_WEIGHT_LBS = 40_000.0

# Known risk levels from least to most severe (FR-08). UNKNOWN is not part of the order.
SEVERITY_ORDER = (
    RiskLevel.LOW,
    RiskLevel.MODERATE,
    RiskLevel.HIGH,
    RiskLevel.SEVERE,
    RiskLevel.NO_TRAVEL,
)

# Risk scores for distance-weighted averages (FR-09).
RISK_SCORES = {
    RiskLevel.LOW: 1,
    RiskLevel.MODERATE: 2,
    RiskLevel.HIGH: 3,
    RiskLevel.SEVERE: 4,
    RiskLevel.NO_TRAVEL: 5,
}
