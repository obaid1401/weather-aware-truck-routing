from datetime import datetime, timedelta, timezone

import pytest

from api.serializers.trip import TripAnalysisRequestSerializer
from shared.types import TripInput


def future_departure(hours: int = 24) -> str:
    offset = timezone(timedelta(hours=-7))
    return (datetime.now(offset) + timedelta(hours=hours)).replace(microsecond=0).isoformat()


def valid_payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "origin": "Denver, CO",
        "destination": "Salt Lake City, UT",
        "departure_time": future_departure(),
        "load_weight_lbs": 36000,
        "checkpoint_interval_miles": 25,
    }
    payload.update(overrides)
    return payload


def validate(payload: dict[str, object]) -> TripAnalysisRequestSerializer:
    serializer = TripAnalysisRequestSerializer(data=payload)
    serializer.is_valid()
    return serializer


def test_valid_payload_produces_trip_input() -> None:
    payload = valid_payload()
    serializer = validate(payload)

    assert serializer.errors == {}
    trip = serializer.to_trip_input()
    assert trip == TripInput(
        origin="Denver, CO",
        destination="Salt Lake City, UT",
        departure_time=datetime.fromisoformat(str(payload["departure_time"])),
        load_weight_lbs=36000.0,
        checkpoint_interval_miles=25,
    )


def test_departure_time_keeps_client_utc_offset() -> None:
    trip = validate(valid_payload()).to_trip_input()

    assert trip.departure_time.utcoffset() == timedelta(hours=-7)


def test_checkpoint_interval_defaults_to_25_miles() -> None:
    payload = valid_payload()
    del payload["checkpoint_interval_miles"]

    assert validate(payload).to_trip_input().checkpoint_interval_miles == 25


@pytest.mark.parametrize("interval", [10, 25, 50])
def test_supported_checkpoint_intervals_are_accepted(interval: int) -> None:
    serializer = validate(valid_payload(checkpoint_interval_miles=interval))

    assert serializer.errors == {}
    assert serializer.to_trip_input().checkpoint_interval_miles == interval


@pytest.mark.parametrize("interval", [0, 5, 30, 100, None])
def test_unsupported_checkpoint_intervals_are_rejected(interval: object) -> None:
    errors = validate(valid_payload(checkpoint_interval_miles=interval)).errors

    assert "checkpoint_interval_miles" in errors


@pytest.mark.parametrize("field", ["origin", "destination", "departure_time", "load_weight_lbs"])
def test_required_fields(field: str) -> None:
    payload = valid_payload()
    del payload[field]

    assert field in validate(payload).errors


@pytest.mark.parametrize("value", ["", "   "])
def test_blank_addresses_are_rejected(value: str) -> None:
    errors = validate(valid_payload(origin=value, destination=value)).errors

    assert "origin" in errors
    assert "destination" in errors


def test_naive_departure_time_is_rejected() -> None:
    naive = (datetime.now() + timedelta(days=1)).replace(microsecond=0).isoformat()

    errors = validate(valid_payload(departure_time=naive)).errors

    assert "timezone offset" in str(errors["departure_time"][0])


def test_past_departure_time_is_rejected() -> None:
    errors = validate(valid_payload(departure_time=future_departure(hours=-1))).errors

    assert str(errors["departure_time"][0]) == "Departure time must not be in the past."


def test_invalid_departure_time_is_rejected() -> None:
    assert "departure_time" in validate(valid_payload(departure_time="not-a-date")).errors


@pytest.mark.parametrize("weight", [0, -1, -36000, "inf", "nan", "heavy"])
def test_non_positive_or_invalid_cargo_weight_is_rejected(weight: object) -> None:
    assert "load_weight_lbs" in validate(valid_payload(load_weight_lbs=weight)).errors


def test_fractional_cargo_weight_is_accepted() -> None:
    assert validate(valid_payload(load_weight_lbs=0.5)).to_trip_input().load_weight_lbs == 0.5
