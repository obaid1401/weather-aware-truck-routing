from drf_spectacular.utils import extend_schema
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from api.serializers.health import HealthResponseSerializer


class HealthView(APIView):
    @extend_schema(summary="Health check", responses=HealthResponseSerializer)
    def get(self, request: Request) -> Response:
        return Response({"status": "ok"})
