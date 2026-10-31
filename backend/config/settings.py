"""
Django settings for the Weather-Aware Truck Routing backend.

All configuration comes from environment variables. For local development, copy
`.env.example` to `.env`; variables already set in the environment take precedence.
Required variables have no fallback: startup fails with a clear error if one is missing.

The application is stateless: no database, models, admin, authentication, or sessions.
"""

import os
import re
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / ".env")


def env_bool(name: str, default: bool) -> bool:
    value = os.environ.get(name, "").strip().lower()
    if not value:
        return default
    if value in {"1", "true", "yes", "on"}:
        return True
    if value in {"0", "false", "no", "off"}:
        return False
    raise ImproperlyConfigured(f"{name} must be a boolean value, got {value!r}.")


def env_list(name: str) -> list[str]:
    return [item.strip() for item in os.environ.get(name, "").split(",") if item.strip()]


def env_required(name: str) -> str:
    """The value of a required variable; blank values count as missing."""
    value = os.environ.get(name, "").strip()
    if not value:
        raise ImproperlyConfigured(
            f"{name} is not set. Add it to backend/.env (see .env.example) or to the environment."
        )
    return value


# Core

DEBUG = env_bool("DJANGO_DEBUG", default=False)

SECRET_KEY = env_required("DJANGO_SECRET_KEY")

ALLOWED_HOSTS = env_list("DJANGO_ALLOWED_HOSTS")


# Application definition

INSTALLED_APPS = [
    "django.contrib.staticfiles",
    "corsheaders",
    "rest_framework",
    "drf_spectacular",
    "modules.geocoding",
    "modules.routing",
    "modules.checkpoints",
    "modules.weather",
    "modules.risk",
    "modules.recommendation",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# Stateless application: no database is configured.
DATABASES = {}


# Internationalization

LANGUAGE_CODE = "en-us"

TIME_ZONE = "UTC"

USE_I18N = True

USE_TZ = True


# Static files

STATIC_URL = "static/"


# Django REST Framework


def env_rate(name: str) -> str:
    """A required DRF throttle rate such as "10/minute" (periods: second, minute, hour, day)."""
    value = env_required(name)
    if not re.fullmatch(r"[1-9]\d*/[smhd][a-z]*", value):
        raise ImproperlyConfigured(
            f"{name} must be a rate such as 10/minute or 100/hour, got {value!r}."
        )
    return value


# Each analysis calls ORS, Valhalla, and Open-Meteo (dozens of location calls), all with
# shared free-tier limits, so the analysis endpoint is rate-limited per client. The rate
# comes from the environment (.env); there is no built-in value.
ANALYZE_RATE_LIMIT = env_rate("ANALYZE_RATE_LIMIT")

REST_FRAMEWORK = {
    "DEFAULT_THROTTLE_RATES": {"analyze": ANALYZE_RATE_LIMIT},
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "DEFAULT_PARSER_CLASSES": ["rest_framework.parsers.JSONParser"],
    "DEFAULT_AUTHENTICATION_CLASSES": [],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.AllowAny"],
    "UNAUTHENTICATED_USER": None,
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "EXCEPTION_HANDLER": "api.exceptions.api_exception_handler",
}

SPECTACULAR_SETTINGS = {
    "TITLE": "Weather-Aware Truck Routing API",
    "DESCRIPTION": "Compares heavy-vehicle routes by distance, travel time, weather, and cargo.",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    # One schema name for each shared enum used by several response fields.
    "ENUM_NAME_OVERRIDES": {
        "RiskLevelEnum": "shared.types.RiskLevel",
        "DataStatusEnum": "shared.types.DataStatus",
    },
    # Swagger UI's syntax highlighter crashes the browser on large responses (a full trip
    # analysis is over 1 MB), so responses are shown as plain text.
    "SWAGGER_UI_SETTINGS": {"syntaxHighlight": False},
}


# CORS

CORS_ALLOWED_ORIGINS = env_list("CORS_ALLOWED_ORIGINS")
CORS_URLS_REGEX = r"^/api/.*$"


# External providers

# OpenRouteService is used for geocoding only.
ORS_API_KEY = env_required("ORS_API_KEY")

# Valhalla is used for truck routing. The public FOSSGIS server is subject to its usage policy.
VALHALLA_BASE_URL = os.environ.get("VALHALLA_BASE_URL", "https://valhalla1.openstreetmap.de")
