"""Maps exceptions to the structured API error format.

Every error response has the shape:

    {"error": {"code": str, "message": str, "details": dict}}
"""

import logging
from typing import Any

from django.http import Http404
from rest_framework import status
from rest_framework.exceptions import APIException, NotFound, ValidationError
from rest_framework.response import Response

from shared.types import (
    AnalysisError,
    GeocodingAmbiguousError,
    ProviderError,
    ProviderRateLimitError,
    ProviderTimeoutError,
    ProviderUnavailableError,
)

logger = logging.getLogger(__name__)

ANALYSIS_ERROR_STATUS: dict[type[AnalysisError], int] = {
    GeocodingAmbiguousError: status.HTTP_422_UNPROCESSABLE_ENTITY,
    ProviderError: status.HTTP_502_BAD_GATEWAY,
    ProviderRateLimitError: status.HTTP_503_SERVICE_UNAVAILABLE,
    ProviderUnavailableError: status.HTTP_503_SERVICE_UNAVAILABLE,
    ProviderTimeoutError: status.HTTP_504_GATEWAY_TIMEOUT,
}


def error_response(code: str, message: str, details: dict[str, Any], status_code: int) -> Response:
    return Response(
        {"error": {"code": code, "message": message, "details": details}},
        status=status_code,
    )


def api_exception_handler(exc: Exception, context: dict[str, Any]) -> Response:
    if isinstance(exc, Http404):
        exc = NotFound()

    if isinstance(exc, AnalysisError):
        for error_type, status_code in ANALYSIS_ERROR_STATUS.items():
            if isinstance(exc, error_type):
                return error_response(exc.code, exc.message, exc.details, status_code)

    if isinstance(exc, ValidationError):
        details = exc.detail if isinstance(exc.detail, dict) else {"non_field_errors": exc.detail}
        return error_response(
            "VALIDATION_ERROR",
            "The request is invalid.",
            details,
            status.HTTP_400_BAD_REQUEST,
        )

    if isinstance(exc, APIException):
        return error_response(exc.default_code.upper(), str(exc.detail), {}, exc.status_code)

    # Unexpected errors: log the details, but never expose them to the client.
    logger.exception("Unhandled error while processing an API request.", exc_info=exc)
    return error_response(
        "INTERNAL_ERROR",
        "An unexpected error occurred.",
        {},
        status.HTTP_500_INTERNAL_SERVER_ERROR,
    )
