from datetime import UTC, datetime, timedelta, timezone

import pytest

from modules.weather.services.forecast_matching import (
    data_status,
    match_forecast,
    nearest_forecast_hour,
)
from modules.weather.services.open_meteo import ForecastHour
from shared.types import DataStatus


def utc(hour: int, minute: int = 0, second: int = 0) -> datetime:
    return datetime(2026, 11, 5, hour, minute, second, tzinfo=UTC)


def hour(at: datetime, wind: float | None = 10.0) -> ForecastHour:
    return ForecastHour(at, wind, 0.0, 0.0)


@pytest.mark.parametrize(
    ("target", "expected"),
    [
        (utc(10), utc(10)),  # exactly on the hour
        (utc(10, 20), utc(10)),
        (utc(10, 29, 59), utc(10)),
        (utc(10, 30), utc(10)),  # tie: the earlier hour
        (utc(10, 30, 1), utc(11)),
        (utc(10, 40), utc(11)),
        (utc(23, 45), datetime(2026, 11, 6, 0, 0, tzinfo=UTC)),  # across midnight
    ],
)
def test_nearest_forecast_hour(target: datetime, expected: datetime) -> None:
    assert nearest_forecast_hour(target) == expected


def test_nearest_hour_is_in_utc_for_any_timezone() -> None:
    # 10:00 at UTC+05:30 is 04:30 UTC: a tie, so the earlier hour (04:00 UTC).
    india = timezone(timedelta(hours=5, minutes=30))

    assert nearest_forecast_hour(datetime(2026, 11, 5, 10, 0, tzinfo=india)) == utc(4)


def test_naive_target_is_rejected() -> None:
    with pytest.raises(ValueError):
        nearest_forecast_hour(datetime(2026, 11, 5, 10, 0))


def test_match_returns_the_nearest_hours_forecast() -> None:
    hours = {utc(10): hour(utc(10), wind=5.0), utc(11): hour(utc(11), wind=20.0)}

    assert match_forecast(hours, utc(10, 20)) == hours[utc(10)]
    assert match_forecast(hours, utc(10, 30)) == hours[utc(10)]
    assert match_forecast(hours, utc(10, 31)) == hours[utc(11)]


def test_match_matches_across_timezones() -> None:
    hours = {utc(15): hour(utc(15))}
    mountain = timezone(timedelta(hours=-7))

    assert match_forecast(hours, datetime(2026, 11, 5, 8, 10, tzinfo=mountain)) == hours[utc(15)]


def test_missing_nearest_hour_is_not_replaced_by_another_hour() -> None:
    # 11:00 exists but is not the nearest hour to 10:20, so nothing is substituted.
    hours = {utc(11): hour(utc(11))}

    assert match_forecast(hours, utc(10, 20)) is None
    assert match_forecast({}, utc(10)) is None


@pytest.mark.parametrize(
    ("forecast", "expected"),
    [
        (ForecastHour(utc(10), 10.0, 0.1, 0.0), DataStatus.AVAILABLE),
        (ForecastHour(utc(10), 0.0, 0.0, 0.0), DataStatus.AVAILABLE),  # zero is data
        (ForecastHour(utc(10), None, 0.1, 0.0), DataStatus.PARTIAL),
        (ForecastHour(utc(10), 10.0, None, None), DataStatus.PARTIAL),
        (ForecastHour(utc(10), None, None, None), DataStatus.UNAVAILABLE),
        (None, DataStatus.UNAVAILABLE),
    ],
)
def test_data_status(forecast: ForecastHour | None, expected: DataStatus) -> None:
    assert data_status(forecast) == expected
