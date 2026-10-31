import math
from datetime import datetime

from django.utils import timezone
from rest_framework import serializers

from shared.types import (
    CHECKPOINT_INTERVAL_CHOICES_MILES,
    DEFAULT_CHECKPOINT_INTERVAL_MILES,
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


class TripAnalysisRequestSerializer(serializers.Serializer):
    origin = serializers.CharField(max_length=200)
    destination = serializers.CharField(max_length=200)
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
        if not math.isfinite(value) or value <= 0:
            raise serializers.ValidationError("Cargo weight must be a positive number of pounds.")
        return value

    def to_trip_input(self) -> TripInput:
        return TripInput(**self.validated_data)
