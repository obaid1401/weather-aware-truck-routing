from datetime import UTC, datetime, timedelta


def require_timezone_aware(moment: datetime, name: str = "datetime") -> None:
    if moment.tzinfo is None or moment.utcoffset() is None:
        raise ValueError(f"{name} must be timezone-aware")


def add_elapsed(moment: datetime, elapsed: timedelta) -> datetime:
    """The instant `elapsed` real time after `moment`, in `moment`'s timezone.

    Adding a timedelta directly to a datetime with a named timezone (such as
    `ZoneInfo("America/Denver")`) adds wall-clock time, which is off by an hour across a
    daylight-saving change. Adding in UTC always gives the true elapsed duration.
    """
    require_timezone_aware(moment, "moment")
    return (moment.astimezone(UTC) + elapsed).astimezone(moment.tzinfo)
