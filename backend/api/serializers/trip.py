import math
from datetime import datetime

from django.utils import timezone
from rest_framework import serializers

from shared.types import (
    CHECKPOINT_INTERVAL_CHOICES_MILES,
    DEFAULT_CHECKPOINT_INTERVAL_MILES,
    Coordinate,
    TripInput,
)


class TimezoneAwareDateTimeField(serializers.DateTimeField):
    """Accepts only timezone-aware datetimes and keeps the client's UTC offset."""

    default_error_messages = {
        "naive": "Include a timezone offset, for example 2026-11-05T08:00:00-07:00.",
    }

    def enforce_timezone(self, value: datetime) -> datetime:
        if timezone.is_naive(value):
            self.fail("naive")
        return value


class CoordinatesSerializer(serializers.Serializer):
    # FloatField also rejects NaN and infinity.
    latitude = serializers.FloatField(min_value=-90, max_value=90)
    longitude = serializers.FloatField(min_value=-180, max_value=180)


CHOSEN_PLACE_HELP = (
    "Optional. The coordinates of a place the user chose from the suggestions; the address is "
    "then used as given instead of being geocoded."
)


class TripAnalysisRequestSerializer(serializers.Serializer):
    origin = serializers.CharField(max_length=200)
    destination = serializers.CharField(max_length=200)
    origin_coordinates = CoordinatesSerializer(
        required=False, allow_null=True, help_text=CHOSEN_PLACE_HELP
    )
    destination_coordinates = CoordinatesSerializer(
        required=False, allow_null=True, help_text=CHOSEN_PLACE_HELP
    )
    departure_time = TimezoneAwareDateTimeField()
    load_weight_lbs = serializers.FloatField()
    checkpoint_interval_miles = serializers.ChoiceField(
        choices=CHECKPOINT_INTERVAL_CHOICES_MILES,
        default=DEFAULT_CHECKPOINT_INTERVAL_MILES,
    )

    def validate_departure_time(self, value: datetime) -> datetime:
        if value < timezone.now():
            raise serializers.ValidationError("Departure time must not be in the past.")
        return value

    def validate_load_weight_lbs(self, value: float) -> float:
        # An empty truck (0 lb) is a valid load.
        if not math.isfinite(value) or value < 0:
            raise serializers.ValidationError("Cargo weight must be 0 or more pounds.")
        return value

    def to_trip_input(self) -> TripInput:
        data = dict(self.validated_data)
        origin = data.pop("origin_coordinates", None)
        destination = data.pop("destination_coordinates", None)
        return TripInput(
            **data,
            origin_coordinate=Coordinate(**origin) if origin else None,
            destination_coordinate=Coordinate(**destination) if destination else None,
        )
