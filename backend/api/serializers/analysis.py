"""Response serializers for `POST /api/v1/routes/analyze/` (the public API contract).

Timestamps are ISO-8601 in UTC, except `trip.departure_time`, which echoes the request with
its original UTC offset. Missing weather values are `null`, never zero; risk and data-status
values use the documented enums.
"""

from rest_framework import serializers

from api.serializers.trip import TimezoneAwareDateTimeField
from shared.types import DataStatus, RiskLevel

RISK_LEVELS = [level.value for level in RiskLevel]
DATA_STATUSES = [status.value for status in DataStatus]


class RiskFieldsMixin(serializers.Serializer):
    wind_risk = serializers.ChoiceField(choices=RISK_LEVELS)
    rain_risk = serializers.ChoiceField(choices=RISK_LEVELS)
    snow_risk = serializers.ChoiceField(choices=RISK_LEVELS)
    final_risk = serializers.ChoiceField(choices=RISK_LEVELS)


class WeatherFieldsMixin(serializers.Serializer):
    forecast_timestamp = serializers.DateTimeField(allow_null=True)
    wind_speed_mph = serializers.FloatField(allow_null=True)
    precipitation_inches_per_hour = serializers.FloatField(allow_null=True)
    snowfall_inches_per_hour = serializers.FloatField(allow_null=True)
    data_status = serializers.ChoiceField(choices=DATA_STATUSES)


class HourlyForecastSerializer(WeatherFieldsMixin, RiskFieldsMixin):
    hour_offset = serializers.IntegerField()
    target_time = serializers.DateTimeField()


class CheckpointSerializer(WeatherFieldsMixin, RiskFieldsMixin):
    id = serializers.CharField()
    route_id = serializers.CharField()
    distance_from_origin_miles = serializers.FloatField()
    latitude = serializers.FloatField()
    longitude = serializers.FloatField()
    estimated_arrival_time = serializers.DateTimeField()
    warnings = serializers.ListField(child=serializers.CharField())
    hourly_forecasts = HourlyForecastSerializer(many=True)


class RouteMetricsSerializer(serializers.Serializer):
    distance_miles = serializers.FloatField()
    duration_seconds = serializers.FloatField()
    low_miles = serializers.FloatField()
    moderate_miles = serializers.FloatField()
    high_miles = serializers.FloatField()
    severe_miles = serializers.FloatField()
    no_travel_miles = serializers.FloatField()
    unknown_miles = serializers.FloatField()
    average_risk_score = serializers.FloatField(allow_null=True)
    weather_coverage_percent = serializers.FloatField()
    complete_weather_coverage_percent = serializers.FloatField()


class AnalyzedRouteSerializer(serializers.Serializer):
    id = serializers.CharField(source="route.id")
    label = serializers.CharField(source="route.label")
    distance_miles = serializers.FloatField(source="route.distance_miles")
    duration_seconds = serializers.FloatField(source="route.duration_seconds")
    estimated_arrival_time = serializers.DateTimeField()
    checkpoint_count = serializers.SerializerMethodField()
    geometry = serializers.ListField(
        source="route.geometry",
        child=serializers.ListField(child=serializers.FloatField(), min_length=2, max_length=2),
        help_text="Route line as [latitude, longitude] pairs, origin to destination.",
    )
    metrics = RouteMetricsSerializer()
    checkpoints = CheckpointSerializer(many=True)

    def get_checkpoint_count(self, analyzed_route: object) -> int:
        return len(analyzed_route.checkpoints)  # type: ignore[attr-defined]


class LocationSerializer(serializers.Serializer):
    label = serializers.CharField()
    latitude = serializers.FloatField()
    longitude = serializers.FloatField()


class TripSerializer(serializers.Serializer):
    origin = serializers.CharField()
    destination = serializers.CharField()
    # Keeps the offset the client sent (for example -07:00) instead of converting to UTC.
    departure_time = TimezoneAwareDateTimeField()
    load_weight_lbs = serializers.FloatField()
    checkpoint_interval_miles = serializers.IntegerField()


class ForecastWindowSerializer(serializers.Serializer):
    start = serializers.DateTimeField(source="forecast_window_start")
    end = serializers.DateTimeField(source="forecast_window_end")


class RecommendationSerializer(serializers.Serializer):
    recommended_route_id = serializers.CharField()
    ranked_route_ids = serializers.ListField(child=serializers.CharField())
    ranking_reasons = serializers.ListField(
        child=serializers.CharField(),
        help_text="One explanation per ranked route, in the order of ranked_route_ids.",
    )
    warnings = serializers.ListField(
        child=serializers.CharField(),
        help_text="Safety warnings: NO_TRAVEL exposure and incomplete weather data.",
    )


class TripAnalysisSerializer(serializers.Serializer):
    trip = TripSerializer()
    origin = LocationSerializer()
    destination = LocationSerializer()
    forecast_window = ForecastWindowSerializer(source="*")
    routes = AnalyzedRouteSerializer(many=True)
    recommendation = RecommendationSerializer(allow_null=True)
    provider_warnings = serializers.ListField(
        child=serializers.CharField(),
        help_text="Provider limitations, such as fewer routes than requested or weather "
        "that could not be retrieved.",
    )


class ErrorDetailSerializer(serializers.Serializer):
    code = serializers.CharField()
    message = serializers.CharField()
    details = serializers.JSONField()


class ErrorResponseSerializer(serializers.Serializer):
    error = ErrorDetailSerializer()
