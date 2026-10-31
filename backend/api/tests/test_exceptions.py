import pytest
from django.http import Http404
from rest_framework.exceptions import MethodNotAllowed, ValidationError

from api.exceptions import api_exception_handler
from shared.types import (
    AnalysisError,
    GeocodingAmbiguousError,
    GeocodingNotFoundError,
    Location,
    NoRouteFoundError,
    ProviderError,
    ProviderRateLimitError,
    ProviderTimeoutError,
    ProviderUnavailableError,
)


def test_geocoding_not_found_returns_422() -> None:
    response = api_exception_handler(GeocodingNotFoundError("destination"), {})

    assert response.status_code == 422
    assert response.data["error"] == {
        "code": "GEOCODING_NOT_FOUND",
        "message": "No location was found for the destination address.",
        "details": {"field": "destination"},
    }


def test_no_route_found_returns_422() -> None:
    response = api_exception_handler(NoRouteFoundError(), {})

    assert response.status_code == 422
    assert response.data["error"]["code"] == "ROUTE_NOT_FOUND"


@pytest.mark.parametrize(
    ("exc", "status_code", "code"),
    [
        (ProviderError(), 502, "PROVIDER_ERROR"),
        (ProviderRateLimitError(), 503, "PROVIDER_RATE_LIMITED"),
        (ProviderUnavailableError(), 503, "PROVIDER_UNAVAILABLE"),
        (ProviderTimeoutError(), 504, "PROVIDER_TIMEOUT"),
    ],
)
def test_provider_errors_map_to_documented_status_codes(
    exc: AnalysisError, status_code: int, code: str
) -> None:
    response = api_exception_handler(exc, {})

    assert response.status_code == status_code
    assert response.data == {
        "error": {"code": code, "message": exc.default_message, "details": {}},
    }


def test_analysis_error_code_and_details_can_be_overridden() -> None:
    exc = ProviderUnavailableError(
        message="The routing provider is unavailable.",
        details={"provider": "openrouteservice"},
        code="ROUTING_PROVIDER_UNAVAILABLE",
    )

    response = api_exception_handler(exc, {})

    assert response.status_code == 503
    assert response.data["error"] == {
        "code": "ROUTING_PROVIDER_UNAVAILABLE",
        "message": "The routing provider is unavailable.",
        "details": {"provider": "openrouteservice"},
    }


def test_ambiguous_geocoding_returns_422_with_candidates() -> None:
    exc = GeocodingAmbiguousError(
        field="origin",
        candidates=[
            Location(label="Springfield, IL, USA", latitude=39.80, longitude=-89.64),
            Location(label="Springfield, MO, USA", latitude=37.21, longitude=-93.29),
        ],
    )

    response = api_exception_handler(exc, {})

    assert response.status_code == 422
    assert response.data == {
        "error": {
            "code": "GEOCODING_AMBIGUOUS",
            "message": "The origin address matches multiple locations.",
            "details": {
                "field": "origin",
                "candidates": [
                    {"label": "Springfield, IL, USA", "latitude": 39.80, "longitude": -89.64},
                    {"label": "Springfield, MO, USA", "latitude": 37.21, "longitude": -93.29},
                ],
            },
        },
    }


def test_validation_error_returns_400_with_field_details() -> None:
    response = api_exception_handler(ValidationError({"origin": ["This field is required."]}), {})

    assert response.status_code == 400
    assert response.data["error"]["code"] == "VALIDATION_ERROR"
    assert response.data["error"]["details"] == {"origin": ["This field is required."]}


def test_non_dict_validation_error_is_wrapped() -> None:
    response = api_exception_handler(ValidationError("Invalid."), {})

    assert response.status_code == 400
    assert response.data["error"]["details"] == {"non_field_errors": ["Invalid."]}


def test_other_api_exceptions_keep_their_status() -> None:
    response = api_exception_handler(MethodNotAllowed("DELETE"), {})

    assert response.status_code == 405
    assert response.data["error"]["code"] == "METHOD_NOT_ALLOWED"


def test_django_404_is_structured() -> None:
    response = api_exception_handler(Http404("secret internal detail"), {})

    assert response.status_code == 404
    assert response.data["error"]["code"] == "NOT_FOUND"
    assert "secret" not in str(response.data)


def test_unexpected_errors_return_500_without_internal_details() -> None:
    response = api_exception_handler(RuntimeError("database password is hunter2"), {})

    assert response.status_code == 500
    assert response.data == {
        "error": {
            "code": "INTERNAL_ERROR",
            "message": "An unexpected error occurred.",
            "details": {},
        },
    }
