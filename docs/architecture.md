# Weather-Aware Truck Routing — Architecture

## 1. Architecture Overview

Build the application as a **Modular Monolith**.

The project will have:

- One React frontend.
- One Django backend.
- Clearly separated backend modules.
- Feature-based frontend organization.
- No microservices.
- A stateless backend: no database, models, migrations, Django admin, authentication, or sessions.
- No Docker or container configuration.

The main objective is to keep the code organized, testable, and easy to extend without introducing unnecessary complexity.

The backend is responsible for all calculations and business rules. The frontend is responsible for collecting user input and displaying the results.

## 2. High-Level Architecture

```text
                   Browser
                      |
                      v
             React + TypeScript
                      |
                      | HTTP / JSON
                      v
             Django REST Framework
                      |
              Analysis Orchestrator
                      |
        +-------------+-------------+
        |             |             |
        v             v             v
    Geocoding       Routing       Checkpoints
        |             |             |
        v             v             |
   OpenRouteService  Valhalla       |
                      |             |
                      +-------------+
                                    |
                                    v
                                Weather
                                    |
                                    v
                                Open-Meteo
                                    |
                                    v
                                  Risk
                                    |
                                    v
                              Recommendation
                                    |
                                    v
                            Analysis Response
                                    |
                                    v
                           React Results UI
```

The frontend must never call ORS, Valhalla, or Open-Meteo directly.

All external API credentials and provider-specific logic must remain in the backend.

## 3. Technology Stack

### Frontend

- React
- TypeScript
- Vite
- Material UI
- React Leaflet
- Leaflet
- TanStack Query
- Axios as the HTTP client
- Vitest and React Testing Library for testing

Use local component state for UI interactions. Do not introduce a global state library unless there is a demonstrated need.

### Backend

- Python
- Django
- Django REST Framework
- HTTPX
- django-cors-headers for CORS restriction
- python-dotenv for loading environment variables
- drf-spectacular for OpenAPI documentation
- Pytest, pytest-django, and pytest-cov for testing
- Ruff for linting

Dependency files:

- `requirements.txt` contains runtime dependencies only. Deployment installs only this file.
- `requirements-dev.txt` contains development and testing dependencies (Pytest, pytest-django, pytest-cov, Ruff). It must include `-r requirements.txt` so one install sets up a full development environment.

Use a Python version supported by the selected Django release and deployment platform.

### External Services

| Service | Responsibility |
|---|---|
| OpenRouteService | Geocoding |
| Valhalla | Heavy-vehicle routing |
| Open-Meteo | Hourly weather forecasts |
| OpenStreetMap | Map tiles |

Use Valhalla's `/route` endpoint with `truck` costing and `alternates: 2` (up to three routes). The server is configured by `VALHALLA_BASE_URL` and defaults to the public FOSSGIS server, which needs no API key but has a usage policy and a 1,500 km truck route limit. Valhalla can still return fewer than three routes.

Open-Meteo's free service is intended for non-commercial use. Do not assume assessment/demo usage grants commercial production rights.

## 4. Project Structure

Use the following structure:

```text
weather-aware-truck-routing/
│
├── backend/
│   ├── config/
│   │   ├── settings.py
│   │   ├── urls.py
│   │   ├── asgi.py
│   │   └── wsgi.py
│   │
│   ├── modules/
│   │   ├── geocoding/
│   │   │   ├── apps.py
│   │   │   ├── services/
│   │   │   └── tests/
│   │   │
│   │   ├── routing/
│   │   │   ├── apps.py
│   │   │   ├── services/
│   │   │   ├── domain/
│   │   │   └── tests/
│   │   │
│   │   ├── checkpoints/
│   │   │   ├── apps.py
│   │   │   ├── services/
│   │   │   ├── domain/
│   │   │   └── tests/
│   │   │
│   │   ├── weather/
│   │   │   ├── apps.py
│   │   │   ├── services/
│   │   │   └── tests/
│   │   │
│   │   ├── risk/
│   │   │   ├── apps.py
│   │   │   ├── domain/
│   │   │   └── tests/
│   │   │
│   │   └── recommendation/
│   │       ├── apps.py
│   │       ├── domain/
│   │       └── tests/
│   │
│   ├── api/
│   │   ├── serializers/
│   │   ├── views/
│   │   ├── urls.py
│   │   └── tests/
│   │
│   ├── application/
│   │   ├── use_cases/
│   │   │   └── analyze_trip.py
│   │   └── tests/
│   │
│   ├── shared/
│   │   ├── types.py
│   │   ├── geo.py
│   │   ├── http.py
│   │   ├── validation.py
│   │   ├── datetimes.py
│   │   └── tests/
│   │
│   ├── manage.py
│   ├── requirements.txt
│   ├── requirements-dev.txt
│   └── .env.example
│
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   ├── features/
│   │   │   ├── trip/
│   │   │   ├── routing/
│   │   │   ├── checkpoints/
│   │   │   ├── weather/
│   │   │   ├── risk/
│   │   │   └── recommendation/
│   │   │
│   │   ├── components/
│   │   │   ├── common/
│   │   │   └── layout/
│   │   │
│   │   ├── map/
│   │   ├── services/
│   │   ├── hooks/
│   │   ├── types/
│   │   ├── theme/
│   │   └── utils/
│   │
│   ├── package.json
│   └── .env.example
│
├── docs/
│   ├── requirements.md
│   ├── architecture.md
│   └── CLAUDE.md
│
├── CLAUDE.md
├── .gitignore
└── README.md
```

Do not create empty folders or unnecessary files simply to match this diagram. Create them when the corresponding implementation is needed.

Structure rules:

- Module tests live in a `tests/` package. Do not use `tests.py` files.
- Modules do not contain `models.py`, `admin.py`, `views.py`, or `migrations/`. The application is stateless, and HTTP views belong in `api/`.
- `backend/application/use_cases/analyze_trip.py` contains the analysis orchestrator (see Section 6). Its tests live in `backend/application/tests/`.
- `backend/shared/` contains code shared across modules:
  - `types.py`: shared types, contracts, and analysis errors (see Section 7). No Django, DRF, or HTTP dependencies.
  - `geo.py`: geometry utilities (great-circle distance, GeoJSON position validation). Must not depend on HTTP code.
  - `http.py`: the shared provider HTTP client (timeouts and User-Agent) and the conversion of transport failures and HTTP error statuses into analysis errors.
  - `validation.py`: small value-validation helpers used when parsing provider responses.
  - `datetimes.py`: timezone-aware time arithmetic that adds real elapsed time (correct across daylight-saving changes).
  - `tests/`: tests for the shared code.
- The root `CLAUDE.md` only imports `docs/CLAUDE.md`. Keep the instructions in `docs/CLAUDE.md`.

## 5. Backend Module Responsibilities

Each module should be a proper Django app with its own `apps.py` and tests. Modules have no models, migrations, or admin registrations.

### 5.1 Geocoding Module

Responsibilities:

- Send address queries to ORS.
- Normalize geocoding results.
- Return latitude and longitude.
- Handle missing results.
- Detect ambiguous results and return the candidate locations instead of choosing one. A result is ambiguous when the provider returns multiple plausible, materially different candidates with similar confidence scores. Approved thresholds: plausible means within 0.1 of the best confidence; materially different means more than 25 miles apart. Only plausible candidates can be selected.
- Handle provider errors and timeouts.

It should not calculate routes or weather risks.

### 5.2 Routing Module

Responsibilities:

- Communicate with Valhalla.
- Use the `truck` costing model.
- Request up to two alternate routes.
- Decode route geometry (encoded polyline, precision 6) and normalize it.
- Map provider maneuvers to route steps.
- Normalize distance and duration.
- Validate provider responses.
- Return genuine route alternatives.

It must not create fake alternatives when the provider returns fewer routes.

### 5.3 Checkpoints Module

Responsibilities:

- Accept normalized route geometry.
- Calculate cumulative route distance.
- Generate checkpoints at the selected interval.
- Interpolate checkpoint coordinates.
- Estimate checkpoint arrival times.
- Return ordered checkpoint data.

Checkpoint placement must use distance along the route, not the number of geometry coordinates.

### 5.4 Weather Module

Responsibilities:

- Communicate with Open-Meteo.
- Request hourly weather forecasts.
- Normalize weather values and units.
- Match forecast timestamps to checkpoint ETAs.
- Handle unavailable forecast data.
- Handle provider timeouts and rate limits.

It must not calculate final risk.

### 5.5 Risk Module

Responsibilities:

- Define risk thresholds.
- Calculate wind risk.
- Calculate rain risk.
- Calculate snow risk.
- Apply cargo-weight overrides.
- Determine final checkpoint risk.
- Handle unknown values.

Risk calculations should use pure functions wherever possible.

### 5.6 Recommendation Module

Responsibilities:

- Aggregate checkpoint risks into route metrics.
- Calculate risk miles.
- Calculate average risk score.
- Calculate weather coverage.
- Rank routes.
- Produce recommendation explanations.
- Return safety warnings.

The ranking logic must follow the exact order defined in `requirements.md`.

## 6. Backend Orchestration

Keep the API view thin.

Create one application-level orchestrator responsible for coordinating the analysis, located in `backend/application/use_cases/analyze_trip.py`.

Suggested flow:

```text
AnalyzeTripUseCase
       |
       v
1. Validate trip input
       |
       v
2. Geocode origin and destination
       |
       v
3. Retrieve heavy-vehicle routes
       |
       v
4. Normalize and validate routes
       |
       v
5. Generate checkpoints
       |
       v
6. Estimate checkpoint ETAs
       |
       v
7. Retrieve weather forecasts
       |
       v
8. Match forecasts to checkpoint ETAs and build 0–48-hour series
       |
       v
9. Calculate checkpoint risks (ETA-matched and hourly)
       |
       v
10. Aggregate route metrics
       |
       v
11. Rank available routes
       |
       v
12. Return normalized response
```

Do not place this entire workflow inside the API view.

Do not turn each step into a separate microservice.

A single orchestrator coordinating focused services is sufficient.

## 7. Internal Data Structures

Use lightweight Python dataclasses, typed dictionaries, or similar structures.

Database models are not used.

Define the types shared across modules in `backend/shared/types.py`: `Coordinate`, `TripInput`, `Location`, `Route`, `RouteStep`, `Checkpoint`, `HourlyForecast`, `RiskLevel`, `RouteMetrics`, and `Recommendation`. Types used only inside one module stay in that module. Risk thresholds and the risk severity/score mappings stay in the risk module.

### TripInput

- origin
- destination
- departure_time
- load_weight_lbs
- checkpoint_interval_miles (default 25)

### Location

- label
- latitude
- longitude

### Coordinate

- latitude
- longitude

### Route

- id
- label
- geometry (list of `Coordinate`)
- distance_miles
- duration_seconds
- steps (list of `RouteStep`; provider maneuvers, used for checkpoint ETAs)
- estimated_arrival_time
- checkpoints

### RouteStep

- start_index (index into the route geometry)
- end_index
- distance_miles
- duration_seconds

### Checkpoint

- id
- route_id
- distance_from_origin_miles
- latitude
- longitude
- estimated_arrival_time
- forecast_timestamp
- wind_speed_mph
- precipitation_inches_per_hour
- snowfall_inches_per_hour
- wind_risk
- rain_risk
- snow_risk
- final_risk
- data_status
- warnings
- hourly_forecasts (list of `HourlyForecast`)

### HourlyForecast

One entry per hour offset from 0 to 48 after departure (49 entries per checkpoint). Used only by the forecast slider.

- hour_offset
- target_time (`departure_time + hour_offset`)
- forecast_timestamp (null if unavailable)
- wind_speed_mph
- precipitation_inches_per_hour
- snowfall_inches_per_hour
- wind_risk
- rain_risk
- snow_risk
- final_risk
- data_status

### DataStatus

How many of the three weather values (wind, precipitation, snowfall) are known for a checkpoint or hourly entry:

- `AVAILABLE`: all three
- `PARTIAL`: some, but not all
- `UNAVAILABLE`: none (conditions unknown)

### RiskLevel

Use these exact values:

- `LOW`
- `MODERATE`
- `HIGH`
- `SEVERE`
- `NO_TRAVEL`
- `UNKNOWN`

Do not use alphabetical string sorting to determine risk severity. Define an explicit severity mapping.

### RouteMetrics

- distance_miles
- duration_seconds
- low_miles
- moderate_miles
- high_miles
- severe_miles
- no_travel_miles
- unknown_miles
- average_risk_score
- weather_coverage_percent
- complete_weather_coverage_percent

### Recommendation

- recommended_route_id
- ranked_route_ids
- ranking_reasons
- warnings

## 8. Route Geometry and Checkpoint Calculation

The routing provider returns a route geometry containing coordinates.

The checkpoint service must:

1. Decode the route geometry.
2. Calculate distances between consecutive coordinates.
3. Build cumulative route distance.
4. Generate target checkpoint distances.
5. Find the geometry segment containing each target distance.
6. Interpolate latitude and longitude along that segment.
7. Include an origin checkpoint at mile 0 and a destination checkpoint at the route's total distance, even when the destination does not align with the selected interval. Do not duplicate the destination checkpoint when it falls exactly on an interval multiple.

Use a reliable geodesic calculation or a suitable geometry library.

Implementation notes (`modules/checkpoints/`):

- Segment lengths are great-circle (haversine) distances, and checkpoint positions are interpolated along the great circle of the containing segment (`shared/geo.py`).
- Measured geometry length differs slightly from the provider's road distance (about 0.1% on Valhalla routes). Cumulative distances are scaled so the final geometry point is exactly at the provider's route distance. This keeps checkpoint mileage consistent with route totals.
- Checkpoint IDs are `<route id>-cp-<n>`, numbered from 0 at the origin.

Convert provider distances to miles at the provider normalization boundary.

Avoid repeatedly converting units throughout the application.

## 9. ETA and Weather Matching

All internal timestamps must be timezone-aware.

Elapsed time (checkpoint ETAs and hourly-series target times) is added in UTC and converted back to the departure's timezone (`shared/datetimes.py`). Adding a duration directly to a datetime with a named timezone adds wall-clock time, which is off by an hour across a daylight-saving change.

Departure times in the past are rejected during request validation.

Use provider step/segment durations when sufficient information is available.

Step durations are sufficient when the steps cover the whole geometry without gaps and their total is within 1% (or 60 seconds, whichever is larger) of the route duration. Steps must also run forward along the geometry and have non-negative, finite durations. Each step's duration is spread across its geometry in proportion to distance. A step with time but no length is a stop at that point: a checkpoint exactly at the point gets the arrival time, and later checkpoints include the full stop. The result is rescaled so the destination ETA equals `departure_time + route_duration`. This logic lives in `modules/checkpoints/domain/eta.py`.

Otherwise:

`elapsed_time = route_duration × checkpoint_distance / route_total_distance`

Then:

`checkpoint_eta = departure_time + elapsed_time`

Match checkpoint ETA to the nearest available hourly weather timestamp. If two timestamps are equally close, choose the earlier one.

Store both:
- Estimated checkpoint arrival time.
- Actual forecast timestamp used.

If forecast data is unavailable for the requested period, mark it as `UNKNOWN`.

Do not substitute unrelated weather data.

Implementation notes (`modules/weather/services/`):

- Matching uses whole UTC hours, because the forecast is hourly in UTC. Only the nearest hour is used. If that hour is missing (a gap, or beyond the 16-day horizon), the conditions are `UNKNOWN`; a neighbouring hour is never substituted.
- `data_status` records how many of the three values (wind, precipitation, snowfall) are known: `AVAILABLE` (all), `PARTIAL` (some), or `UNAVAILABLE` (none). Missing values stay `null`; a missing variable never discards the others, and zero is real data.
- A checkpoint within 0.1 mile of a location already being fetched shares the nearest such location's forecast (the earlier location on a tie). This removes the duplicate origin and shared stretches across routes. The model grid is kilometres wide, so the forecast is unchanged.
- The forecast horizon is computed from the server clock. If Open-Meteo's range ends earlier (HTTP 400, "out of allowed range from … to YYYY-MM-DD"), the request is retried once with the window ending at 23:00 UTC on that date. Available hours are kept and later hours stay `UNAVAILABLE`. Other 400 errors, or range messages that cannot be parsed, are not retried and become `ProviderError` as before.
- Provider responses are rejected as invalid (`ProviderError`) when units are missing or unexpected, when hourly timestamps are duplicated, out of order, or not on whole hours, or when `location_id` values show results out of request order.
- One fetch per location covers both ETA matching and the 0–48-hour series: from departure to the later of departure + 48 hours and the last checkpoint ETA.
- Locations are fetched in sequential batches of up to 100. Open-Meteo counts each location as one call (600 per minute on the free tier), and concurrent batches were measured to be no faster. After a rate-limit error, the remaining batches are skipped.
- Partial failures: if some batches fail, their checkpoints are `UNAVAILABLE` and a warning is returned. If every batch fails, the provider error is raised (HTTP 502, 503, or 504) and no analysis is returned.
- Forecast range: when checkpoint ETAs (or, failing that, forecast-slider hours) fall after the last hour Open-Meteo forecasts, a warning states the forecast end time and how many checkpoints are affected. Those values are `UNKNOWN` because no forecast exists yet. This is reported as a range limit, never as a provider failure.

### Hourly Forecast Series

For each checkpoint, the backend also returns an hourly series for the 0–48-hour period after departure (see `HourlyForecast` in Section 7):

- One entry per hour offset from 0 to 48.
- Each entry's target time is `departure_time + hour_offset`. Match it to a forecast timestamp using the same nearest-timestamp rule and earlier-timestamp tie-break.
- The risk module calculates each entry's factor risks and final risk using the trip's cargo weight.
- If forecast data is unavailable for an hour, that entry is `UNKNOWN`.
- Build the series from the same Open-Meteo data used for ETA matching. Do not make extra provider requests for the slider.

The series describes conditions at each checkpoint location at the selected hour, regardless of when the truck reaches it. It is for visualization only.

Route metrics, ranking, and the recommendation always use the ETA-matched values. The hourly series never affects them.

## 10. Weather and Risk Boundaries

Keep the following responsibilities separate:

```text
Open-Meteo Response
        |
        v
Weather Provider Adapter
        |
        v
Normalized Weather Values
        |
        v
Risk Domain Functions
        |
        v
Checkpoint Risk
```

The weather module handles provider data and units.

The risk module handles business rules.

The risk thresholds must exist in one source of truth.

The frontend must not independently calculate risk.

Implementation notes (`modules/risk/domain/`):

- `thresholds.py` is the single source of truth for the FR-06 bands, the FR-07 cargo-weight rules, the severity order, and the risk scores. Boundaries are compared exactly. Provider values that convert exactly onto a boundary (for example 25.4 mm = 1.00 in, or 7.62 cm = 3.00 in) land on the documented side; tests cover this.
- The most severe risk is chosen by explicit severity order, never by comparing the names.
- Rain risk uses Open-Meteo's hourly `precipitation`, as FR-05 specifies. That total includes the water equivalent of snow, so heavy snowfall can also raise rain risk. This is a conservative reading.
- Unknown wind stays `UNKNOWN` for every load, so cargo-weight limits are never assumed to be met. When some factors are unknown, the checkpoint gets an incomplete-data warning (which also says when cargo-weight wind limits could not be checked). When all are unknown, the warning says the risk is `UNKNOWN`.
- Every hourly forecast entry is assessed with the same rules and the trip's cargo weight. Hourly risks never affect route metrics.

## 11. Route Aggregation and Recommendation

Create a segment between each pair of consecutive checkpoints.

Use the downstream checkpoint's risk for the segment leading to it.

Include the final partial segment.

For average risk:

1. Map known risk levels to scores 1–5.
2. Multiply each segment's score by its distance.
3. Divide by total known-risk miles.
4. Exclude unknown miles.
5. Return `null` if there are no known-risk miles.
6. Return weather coverage separately.

Segment-risk approximation (`modules/recommendation/domain/metrics.py`):

- Each segment's risk is the risk at the checkpoint where it ends: the conditions forecast for when the truck arrives there. Conditions between checkpoints are not sampled, so a shorter checkpoint interval gives a finer picture.
- The origin checkpoint's risk covers no miles, because no segment ends at the origin.
- Every route mile belongs to exactly one segment, so the six risk-mile totals add up to the route distance.
- Two coverage figures use the same segments (downstream checkpoint, final partial segment included, each mile counted once):
  - **Weather coverage** (`weather_coverage_percent`, risk coverage): the percentage of route miles whose segment has a known final risk. A checkpoint with partial data but a known final risk counts as covered; its incomplete-data warning flags the gap. It always equals 100% minus the unknown-risk share of the route.
  - **Complete weather coverage** (`complete_weather_coverage_percent`): the percentage of route miles whose downstream checkpoint has all three weather values (`data_status` is `AVAILABLE`). Partial data does not count.
  - Example: if wind is missing everywhere but rain and snow are LOW, risk is LOW on every mile and weather coverage is 100%, but complete weather coverage is 0%. Showing both stops incomplete data from being mistaken for a fully safe assessment (FR-10). Neither figure changes risk miles, the average, or ranking.

Ranking must use a lexicographic comparator:

```python
(
    severe_miles,
    high_miles,
    average_risk_score,
    duration_seconds
)
```

All values are compared in ascending order.

If average risk is unavailable, treat it as worse than a known average at that comparison point. Document this policy.

After the required criteria, use:
1. Shorter distance.
2. Provider order.

Do not add no-travel miles as an undocumented primary ranking criterion. Display them prominently as a safety warning.

Implementation notes (`modules/recommendation/domain/ranking.py`):

- The sort key is `(severe_miles, high_miles, average, duration_seconds, distance_miles, provider_position)`, compared left to right; values are compared exactly.
- **Unknown average policy:** a route with no known-risk miles has no average risk score. At the average-risk step it ranks below every route with a known average. Two routes with unknown averages tie at that step and fall through to travel time. Earlier criteria (severe and high miles) still apply first.
- `recommend()` returns no recommendation (`None`) when there are no routes.
- `ranking_reasons` has one entry per ranked route, in rank order. The first explains why the recommended route was chosen. Each later entry explains why that route ranks below the one directly above it, naming the first criterion that separated them, with both values. When values look equal at normal precision, more precision is shown.
- Warnings, in this order:
  1. One per route with NO_TRAVEL miles, naming whether it is the recommended route.
  2. "No route is free of NO_TRAVEL conditions" when every route has them (or a single-route equivalent).
  3. Incomplete weather data per route: unknown-risk miles with weather coverage, or otherwise partial weather values with complete weather coverage.
  4. When no route has any known risk, a warning that the recommendation is based on travel time and distance only.
- Displayed coverage is rounded down, so incomplete coverage never appears as 100%. A non-zero NO_TRAVEL distance below 0.05 mi is shown as "<0.1 mi", never 0.0.

## 12. API Design

Primary endpoint:

`POST /api/v1/routes/analyze/`

Supporting endpoint:

`GET /api/health/` (intentionally unversioned)

The request serializer validates:

- Origin and destination.
- Timezone-aware departure time.
- Departure time not in the past.
- Positive cargo weight.
- Checkpoint interval of 10, 25, or 50 miles (optional; defaults to 25).

The response should contain normalized application data, not raw provider responses.

Use structured error responses:

```json
{
  "error": {
    "code": "ROUTING_PROVIDER_LIMIT",
    "message": "The routing provider could not return alternative routes.",
    "details": {}
  }
}
```

Ambiguous geocoding returns the candidate locations in `details`:

```json
{
  "error": {
    "code": "GEOCODING_AMBIGUOUS",
    "message": "The origin address matches multiple locations.",
    "details": {
      "field": "origin",
      "candidates": [
        { "label": "Springfield, IL, USA", "latitude": 39.80, "longitude": -89.64 },
        { "label": "Springfield, MO, USA", "latitude": 37.21, "longitude": -93.29 }
      ]
    }
  }
}
```

HTTP status codes:

| Status | Use |
|---|---|
| 200 | Successful request |
| 400 | Invalid request |
| 422 | Ambiguous geocoding (`GEOCODING_AMBIGUOUS`); address not found (`GEOCODING_NOT_FOUND`); no route found (`ROUTE_NOT_FOUND`, `ROUTE_DISTANCE_LIMIT`) |
| 429 | Too many analysis requests from one client (`RATE_LIMITED`, with a `Retry-After` header) |
| 502 | Provider error |
| 503 | Provider rate limit or temporary unavailability |
| 504 | Provider timeout |

Generate OpenAPI documentation.

Keep frontend TypeScript types aligned with the backend contract.

Implementation notes (`api/serializers/analysis.py`, `api/views/analyze.py`):

- The view validates the request, calls `AnalyzeTripUseCase.execute()`, and serializes the result. Errors from any step are mapped to the status table above by the existing exception handler.
- Successful response (`200`), top-level fields:
  - `trip`: the validated request.
  - `origin`, `destination`: geocoded locations (label, latitude, longitude).
  - `forecast_window`: `start` (departure) and `end` (departure + 48 hours).
  - `routes`: in provider order. Each has `id`, `label`, `distance_miles`, `duration_seconds`, `estimated_arrival_time`, `checkpoint_count`, `geometry` (`[latitude, longitude]` pairs), `metrics` (`RouteMetrics`), and `checkpoints`. Each checkpoint carries its ETA-matched weather, factor and final risks, `data_status`, `warnings`, and 49 `hourly_forecasts`.
  - `recommendation`: `recommended_route_id`, `ranked_route_ids`, `ranking_reasons` (one per ranked route, same order), and `warnings`, the safety warnings (NO_TRAVEL exposure, incomplete weather data).
  - `provider_warnings`: provider limitations, such as fewer routes than requested or weather that could not be retrieved.
- All timestamps are ISO-8601 in UTC (`Z`), except `trip.departure_time`, which echoes the request with the UTC offset the client sent. Missing weather values are `null`, never `0`. Risk and data-status values use the `RiskLevelEnum` and `DataStatusEnum` schema components.
- The orchestrator sends every route's checkpoints to the weather service in one list and recovers each route's checkpoints by position, not by route id. The weather service must return them in the same order and number.
- Each request builds a lightweight use case, but all provider services share the single process-wide HTTP client (`shared/http.py`), so connections are reused and no client is created per request.
- Rate limit: the analysis endpoint (only) uses DRF's `ScopedRateThrottle`, per client IP, at `ANALYZE_RATE_LIMIT`, which is required from the environment (for example `10/minute` in `.env`), with no built-in value. Every analysis uses shared provider quotas. The counters live in Django's default in-process cache, so each server process counts separately; behind a proxy, DRF's `NUM_PROXIES` must be set so the client IP is read correctly.

## 13. Frontend Architecture

Organize frontend code by feature.

### `features/trip`

- Trip form
- Input validation
- Departure date/time
- Load weight
- Checkpoint interval

### `features/routing`

- Route comparison cards
- Route selection
- Route summary

### `features/checkpoints`

- Checkpoint list
- Checkpoint details
- Checkpoint selection

### `features/weather`

- Forecast slider (reads each checkpoint's `hourly_forecasts`)
- Weather information
- Selected forecast timestamp

The slider displays backend-provided values only. It does not calculate risk or change the route ranking.

### `features/risk`

- Risk labels
- Risk legend
- Risk explanations

### `features/recommendation`

- Recommended route
- Ranking explanation
- Safety warnings

### `map`

- Map container
- Route polylines
- Origin and destination markers
- Checkpoint markers
- Risk legend
- Selected route styling

### `services`

- API client
- Request and response types
- API error handling

The map should receive normalized data through props. It should not communicate with external providers or calculate risk.

## 14. Frontend State Management

Keep server data separate from UI state.

Server data:
- Analysis response
- Routes
- Checkpoints
- Weather
- Risk results
- Recommendation

UI state:
- Selected route ID
- Selected checkpoint ID
- Forecast offset
- Form values

Expected behavior:

- Form submission calls the analysis endpoint.
- Selecting another route changes the displayed route.
- Selecting a checkpoint changes the detail panel.
- Moving the forecast slider updates displayed weather.
- These UI interactions must not trigger new routing requests.
- The forecast offset changes only the displayed weather and risk. It never changes route metrics, ranking, or the recommendation.

TanStack Query can manage the analysis request lifecycle.

## 15. Error Handling

Handle these application errors explicitly:

- Geocoding result not found.
- Geocoding provider unavailable.
- Routing provider unavailable.
- No route returned.
- Alternative routing limitation.
- Weather provider unavailable.
- Partial weather data.
- Missing forecast hours.
- Provider rate limits.
- Provider timeouts.

Return safe and useful error messages.

Do not expose API keys, stack traces, or provider request headers.

## 16. Testing Strategy

Backend module tests live in each module's `tests/` package. Orchestrator tests live in `backend/application/tests/`.

### Backend Unit Tests

Prioritize:

- Wind thresholds.
- Rain thresholds.
- Snow thresholds.
- Cargo-weight overrides.
- Unknown data handling.
- Checkpoint distance calculations.
- Origin and destination checkpoints.
- Coordinate interpolation.
- ETA calculations.
- Weather unit conversions.
- Forecast timestamp matching, including the earlier-timestamp tie-break.
- Hourly forecast series construction and hourly risks.
- Route mileage aggregation.
- Weighted average risk.
- Route ranking.

### Backend Integration Tests

Mock external requests.

Test:
- ORS geocoding.
- Ambiguous geocoding results.
- Valhalla routing, including polyline decoding and maneuver mapping.
- One, two, and three returned routes.
- Valhalla no-route and distance-limit errors.
- No routes returned.
- Provider rate limits.
- Provider timeouts.
- Malformed responses.
- Open-Meteo valid data.
- Open-Meteo missing data.
- Partial weather failures.

Normal tests must not require live API keys.

### API Tests

Test:
- Valid requests.
- Invalid input.
- Past departure times.
- Default checkpoint interval.
- Unsupported intervals.
- Ambiguous geocoding error with candidates.
- Provider errors.
- Partial weather coverage.
- Response structure.

### Frontend Tests

Use Vitest and React Testing Library.

Test:
- Form validation.
- Loading and error states.
- Route selection.
- Checkpoint selection.
- Forecast slider.
- No repeated analysis request when the slider changes.
- Slider changes do not change the ranking or recommendation display.

## 17. Security and Configuration

- Store secrets in environment variables.
- Never commit `.env`.
- Commit `.env.example`.
- Restrict CORS.
- Disable Django debug mode in deployment.
- Configure allowed hosts.
- Keep API keys out of frontend bundles.
- Set external request timeouts.
- Validate user input.
- Use HTTPS in deployment.

## 18. Deployment

Deploy the frontend and backend separately if that is the simplest reliable approach.

Deployment requirements:

- Configure production environment variables.
- Configure CORS.
- Verify HTTPS.
- Verify backend health endpoint.
- Test a complete trip on the hosted application.
- Verify map tiles and attribution.
- Document hosting free-tier limitations.
- Do not introduce paid infrastructure without approval.

Free hosting providers may impose sleeping, cold starts, or usage limits. Verify current terms before selecting a provider.

Production serving requirements (to be selected and approved before deployment; not installed yet):

- A production WSGI server. Do not use Django's development server in deployment.
- Static-file handling for collected static files (for example, DRF and API documentation assets) when `DEBUG` is off.

Install only `requirements.txt` in production. Docker is not used.

## 19. Architecture Decisions

| Decision | Choice | Reason |
|---|---|---|
| Backend architecture | Modular monolith | Clear separation without microservice complexity |
| Persistence | None (stateless) | No models, migrations, admin, authentication, or sessions |
| Containerization | None | Docker is not part of this project |
| Orchestrator location | `application/use_cases/analyze_trip.py` | One coordinator outside the API views |
| Shared contracts | `shared/types.py` | One set of cross-module types; avoids circular imports |
| Geocoding | ORS | Free geocoding with confidence scores |
| Routing | Valhalla `truck` | Heavy-vehicle routing with up to three genuine routes, including long trips |
| Weather | Open-Meteo | Non-commercial assessment use within its terms |
| Map | Leaflet + OSM | Open-source mapping |
| Risk calculations | Backend domain functions | One authoritative implementation |
| Recommendation | Lexicographic comparison | Matches assessment requirements |
| Frontend state | Local state + TanStack Query | Avoid unnecessary complexity |
| Forecast slider | Backend-provided hourly series per checkpoint | No re-routing, no frontend risk logic, ranking unaffected |
| Frontend testing | Vitest + React Testing Library | Integrates with Vite |
| Frontend HTTP client | Axios | One client for the API service layer |
| Provider integration | Backend adapters | Easier replacement and testing |

## 20. Definition of Done

The architecture is implemented correctly when:

- Backend modules have clear responsibilities.
- Provider integrations are separated from domain logic.
- API views remain thin.
- Risk calculations are independently testable.
- Route ranking is independently testable.
- Frontend components are organized by feature.
- The map uses backend-provided data.
- External services are not called directly by the frontend.
- No unnecessary infrastructure has been introduced.