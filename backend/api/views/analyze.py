from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from api.serializers.analysis import ErrorResponseSerializer, TripAnalysisSerializer
from api.serializers.trip import TripAnalysisRequestSerializer
from application.use_cases.analyze_trip import AnalyzeTripUseCase


def _error(description: str) -> OpenApiResponse:
    return OpenApiResponse(response=ErrorResponseSerializer, description=description)


class AnalyzeTripView(APIView):
    # Per-client limit (ANALYZE_RATE_LIMIT), because every analysis uses shared provider quotas.
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "analyze"

    @extend_schema(
        summary="Analyze a truck trip",
        request=TripAnalysisRequestSerializer,
        responses={
            200: TripAnalysisSerializer,
            400: _error("Invalid request."),
            422: _error("Ambiguous or unknown address, or no route found."),
            429: _error("Too many analysis requests from this client; see Retry-After."),
            502: _error("A provider returned an error or an invalid response."),
            503: _error("A provider's rate limit was reached or it is unavailable."),
            504: _error("A provider did not respond in time."),
        },
    )
    def post(self, request: Request) -> Response:
        serializer = TripAnalysisRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        analysis = AnalyzeTripUseCase().execute(serializer.to_trip_input())
        return Response(TripAnalysisSerializer(analysis).data)
