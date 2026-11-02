from django.urls import path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from api.views.analyze import AnalyzeTripView
from api.views.health import HealthView
from api.views.locations import LocationSuggestionsView

urlpatterns = [
    path("health/", HealthView.as_view(), name="health"),
    path("v1/routes/analyze/", AnalyzeTripView.as_view(), name="analyze-trip"),
    path(
        "v1/locations/suggestions/",
        LocationSuggestionsView.as_view(),
        name="location-suggestions",
    ),
    path("schema/", SpectacularAPIView.as_view(), name="schema"),
    path("docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="docs"),
]
