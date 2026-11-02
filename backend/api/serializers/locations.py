"""Serializers for `GET /api/v1/locations/suggestions/` (place suggestions while typing)."""

from rest_framework import serializers

from api.serializers.analysis import LocationSerializer

# Matches the trip form: suggestions start from the third character, and addresses are at most
# 200 characters (api/serializers/trip.py).
MIN_QUERY_LENGTH = 3
MAX_QUERY_LENGTH = 200


class LocationSuggestionsRequestSerializer(serializers.Serializer):
    q = serializers.CharField(
        min_length=MIN_QUERY_LENGTH,
        max_length=MAX_QUERY_LENGTH,
        help_text="The partly typed address, at least 3 characters.",
    )


class LocationSuggestionsSerializer(serializers.Serializer):
    suggestions = LocationSerializer(
        many=True, help_text="Up to 5 matching places, best first. Empty when nothing matches."
    )
