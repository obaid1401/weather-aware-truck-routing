from datetime import UTC, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import pytest

from shared.datetimes import add_elapsed, require_timezone_aware

DENVER = ZoneInfo("America/Denver")
FALL_BACK_EVE = datetime(2026, 10, 31, 20, 0, tzinfo=DENVER)  # DST ends 2026-11-01 02:00
SPRING_FORWARD_EVE = datetime(2027, 3, 13, 20, 0, tzinfo=DENVER)  # DST starts 2027-03-14 02:00


@pytest.mark.parametrize("start", [FALL_BACK_EVE, SPRING_FORWARD_EVE])
@pytest.mark.parametrize("hours", [1, 6, 7, 24, 48])
def test_adds_real_elapsed_time_across_dst(start: datetime, hours: int) -> None:
    result = add_elapsed(start, timedelta(hours=hours))

    assert result.astimezone(UTC) - start.astimezone(UTC) == timedelta(hours=hours)
    assert result.tzinfo is DENVER


def test_naive_wall_clock_addition_would_be_wrong() -> None:
    # Documents the bug being avoided: plain addition is off by an hour across DST.
    wall_clock = FALL_BACK_EVE + timedelta(hours=48)
    real = add_elapsed(FALL_BACK_EVE, timedelta(hours=48))

    assert wall_clock.astimezone(UTC) - real.astimezone(UTC) == timedelta(hours=1)


def test_local_time_reflects_the_offset_change() -> None:
    assert add_elapsed(FALL_BACK_EVE, timedelta(hours=48)) == datetime(
        2026, 11, 2, 19, 0, tzinfo=DENVER
    )
    assert add_elapsed(SPRING_FORWARD_EVE, timedelta(hours=48)) == datetime(
        2027, 3, 15, 21, 0, tzinfo=DENVER
    )


def test_fixed_offsets_behave_exactly_as_before() -> None:
    mountain = timezone(timedelta(hours=-7))
    start = datetime(2026, 11, 5, 23, 15, tzinfo=mountain)

    result = add_elapsed(start, timedelta(hours=48, seconds=30))

    assert result == start + timedelta(hours=48, seconds=30)
    assert result.tzinfo is mountain


def test_naive_datetimes_are_rejected() -> None:
    with pytest.raises(ValueError, match="moment must be timezone-aware"):
        add_elapsed(datetime(2026, 11, 5, 8, 0), timedelta(hours=1))
    with pytest.raises(ValueError, match="departure_time must be timezone-aware"):
        require_timezone_aware(datetime(2026, 11, 5, 8, 0), "departure_time")
