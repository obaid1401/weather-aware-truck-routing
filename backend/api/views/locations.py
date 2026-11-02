from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from api.serializers.analysis import ErrorResponseSerializer
from api.serializers.locations import (
    LocationSuggestionsRequestSerializer,
    LocationSuggestionsSerializer,
)
from modules.geocoding.services.ors_geocoding import OrsGeocodingService


def _error(description: str) -> OpenApiResponse:
    return OpenApiResponse(response=ErrorResponseSerializer, description=description)


class LocationSuggestionsView(APIView):
    # Per-client limit (SUGGEST_RATE_LIMIT): every suggestion uses the shared geocoding quota.
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "suggest"

    @extend_schema(
        summary="Suggest places for a partly typed address",
        parameters=[
            OpenApiParameter("q", str, description="The partly typed address (3-200 characters).")
        ],
        responses={
            200: LocationSuggestionsSerializer,
            400: _error("The query is missing, too short, or too long."),
            429: _error("Too many suggestion requests from this client; see Retry-After."),
            502: _error("The geocoding provider returned an error or an invalid response."),
            503: _error("The geocoding provider's rate limit was reached or it is unavailable."),
            504: _error("The geocoding provider did not respond in time."),
        },
    )
    def get(self, request: Request) -> Response:
        serializer = LocationSuggestionsRequestSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        suggestions = OrsGeocodingService().suggest(serializer.validated_data["q"])
        return Response(LocationSuggestionsSerializer({"suggestions": suggestions}).data)
