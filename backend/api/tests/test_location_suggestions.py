"""GET /api/v1/locations/suggestions/: place suggestions while the user types an address."""

from typing import Any

import httpx
import pytest
from django.test import Client
from rest_framework.throttling import ScopedRateThrottle

URL = "/api/v1/locations/suggestions/"


class FakeAutocomplete:
    """Answers like ORS /geocode/autocomplete and records every request."""

    def __init__(self, response: httpx.Response | None = None) -> None:
        self.requests: list[httpx.Request] = []
        self.response = response or httpx.Response(
            200,
            json={
                "features": [
                    {
                        "geometry": {"coordinates": [-104.986, 39.741]},
                        "properties": {"label": "Denver, CO, USA"},
                    },
                    {
                        "geometry": {"coordinates": [-74.477, 40.892]},
                        "properties": {"label": "Denville, NJ, USA"},
                    },
                ]
            },
        )

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        return self.response


def use(monkeypatch: pytest.MonkeyPatch, fake: FakeAutocomplete) -> FakeAutocomplete:
    client = httpx.Client(transport=httpx.MockTransport(fake))
    monkeypatch.setattr("modules.geocoding.services.ors_geocoding.get_http_client", lambda: client)
    return fake


def test_returns_suggested_places(client: Client, monkeypatch: pytest.MonkeyPatch) -> None:
    fake = use(monkeypatch, FakeAutocomplete())

    response = client.get(URL, {"q": "Denv"})

    assert response.status_code == 200
    assert response.json() == {
        "suggestions": [
            {"label": "Denver, CO, USA", "latitude": 39.741, "longitude": -104.986},
            {"label": "Denville, NJ, USA", "latitude": 40.892, "longitude": -74.477},
        ]
    }
    (request,) = fake.requests
    assert request.url.params["text"] == "Denv"


def test_no_match_returns_an_empty_list(client: Client, monkeypatch: pytest.MonkeyPatch) -> None:
    use(monkeypatch, FakeAutocomplete(httpx.Response(200, json={"features": []})))

    response = client.get(URL, {"q": "Qzxw"})

    assert response.status_code == 200
    assert response.json() == {"suggestions": []}


@pytest.mark.parametrize("params", [{}, {"q": ""}, {"q": "De"}, {"q": "   "}, {"q": "x" * 201}])
def test_invalid_queries_are_rejected_without_calling_the_provider(
    client: Client, monkeypatch: pytest.MonkeyPatch, params: dict[str, Any]
) -> None:
    fake = use(monkeypatch, FakeAutocomplete())

    response = client.get(URL, params)

    assert response.status_code == 400
    error = response.json()["error"]
    assert error["code"] == "VALIDATION_ERROR"
    assert "q" in error["details"]
    assert fake.requests == []


def test_provider_rate_limit_is_reported_as_503(
    client: Client, monkeypatch: pytest.MonkeyPatch
) -> None:
    use(monkeypatch, FakeAutocomplete(httpx.Response(429)))

    response = client.get(URL, {"q": "Denv"})

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "PROVIDER_RATE_LIMITED"


def test_only_get_is_allowed(client: Client) -> None:
    assert client.post(URL, {"q": "Denv"}).status_code == 405


def test_too_many_suggestion_requests_get_429(
    client: Client, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        ScopedRateThrottle, "THROTTLE_RATES", {"analyze": "10/minute", "suggest": "2/minute"}
    )
    fake = use(monkeypatch, FakeAutocomplete())

    statuses = [client.get(URL, {"q": "Denv"}).status_code for _ in range(2)]
    throttled = client.get(URL, {"q": "Denv"})

    assert statuses == [200, 200]
    assert throttled.status_code == 429
    error = throttled.json()["error"]
    assert error["code"] == "RATE_LIMITED"
    assert error["message"] == (
        "Too many place suggestion requests. Keep typing, or try again shortly."
    )
    assert throttled["Retry-After"] == str(error["details"]["retry_after_seconds"])
    assert len(fake.requests) == 2  # the third request never reached the provider


def test_suggestion_rate_limit_comes_from_the_environment() -> None:
    from django.conf import settings

    assert ScopedRateThrottle.THROTTLE_RATES["suggest"] == settings.SUGGEST_RATE_LIMIT


def test_is_documented_in_the_openapi_schema(client: Client) -> None:
    schema = client.get("/api/schema/", HTTP_ACCEPT="application/vnd.oai.openapi+json").json()

    operation = schema["paths"][URL]["get"]
    assert [p["name"] for p in operation["parameters"]] == ["q"]
    assert set(operation["responses"]) == {"200", "400", "429", "502", "503", "504"}
