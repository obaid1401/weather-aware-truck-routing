"""Startup configuration: required variables fail clearly, with no fallback values.

Each case runs Django's settings in a fresh interpreter, since settings are read once at
import. A variable set to an empty string is never overridden by a local `.env` file, so
these tests behave the same with or without one.
"""

import os
import subprocess
import sys
from pathlib import Path

import pytest

BACKEND_DIR = Path(__file__).resolve().parents[2]
LOAD_SETTINGS = (
    "import os; os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings'; "
    "import django; django.setup(); from django.conf import settings; "
    "print(settings.SECRET_KEY, settings.ORS_API_KEY, settings.VALHALLA_BASE_URL, sep='|')"
)
VALID = {"DJANGO_SECRET_KEY": "test-secret-key", "ORS_API_KEY": "test-ors-key"}


def start_django(**overrides: str) -> subprocess.CompletedProcess[str]:
    env = {**os.environ, **VALID, **overrides}
    return subprocess.run(
        [sys.executable, "-c", LOAD_SETTINGS],
        cwd=BACKEND_DIR,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


def test_valid_configuration_starts() -> None:
    result = start_django(VALHALLA_BASE_URL="https://valhalla.example")

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "test-secret-key|test-ors-key|https://valhalla.example"


@pytest.mark.parametrize("debug", ["False", "True"])
@pytest.mark.parametrize("value", ["", "   "])
def test_missing_secret_key_fails_in_every_mode(debug: str, value: str) -> None:
    result = start_django(DJANGO_SECRET_KEY=value, DJANGO_DEBUG=debug)

    assert result.returncode != 0
    assert "ImproperlyConfigured: DJANGO_SECRET_KEY is not set." in result.stderr


@pytest.mark.parametrize("value", ["", "   "])
def test_missing_ors_api_key_fails_at_startup(value: str) -> None:
    result = start_django(ORS_API_KEY=value)

    assert result.returncode != 0
    assert "ImproperlyConfigured: ORS_API_KEY is not set." in result.stderr


def test_error_message_says_how_to_fix_it() -> None:
    result = start_django(ORS_API_KEY="")

    assert "Add it to backend/.env (see .env.example) or to the environment." in result.stderr
