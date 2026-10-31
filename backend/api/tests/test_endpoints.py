from django.test import Client
from django.test.utils import override_settings


def test_health_returns_ok(client: Client) -> None:
    response = client.get("/api/health/")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_health_rejects_unsupported_methods_with_structured_error(client: Client) -> None:
    response = client.post("/api/health/")

    assert response.status_code == 405
    assert response.json()["error"]["code"] == "METHOD_NOT_ALLOWED"


def test_openapi_schema_is_served(client: Client) -> None:
    response = client.get("/api/schema/", HTTP_ACCEPT="application/vnd.oai.openapi+json")

    assert response.status_code == 200
    schema = response.json()
    assert schema["info"]["title"] == "Weather-Aware Truck Routing API"
    assert "/api/health/" in schema["paths"]


def test_swagger_ui_is_served(client: Client) -> None:
    response = client.get("/api/docs/")

    assert response.status_code == 200
    assert b"swagger" in response.content.lower()


@override_settings(CORS_ALLOWED_ORIGINS=["http://localhost:5173"])
def test_cors_allows_configured_origin(client: Client) -> None:
    response = client.get("/api/health/", HTTP_ORIGIN="http://localhost:5173")

    assert response["Access-Control-Allow-Origin"] == "http://localhost:5173"


@override_settings(CORS_ALLOWED_ORIGINS=["http://localhost:5173"])
def test_cors_rejects_unknown_origin(client: Client) -> None:
    response = client.get("/api/health/", HTTP_ORIGIN="https://evil.example")

    assert "Access-Control-Allow-Origin" not in response
