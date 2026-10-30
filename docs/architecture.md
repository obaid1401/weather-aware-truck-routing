# Weather-Aware Truck Routing — Architecture

## 1. Architecture Overview

Build the application as a **Modular Monolith**.

The project will have:

- One React frontend.
- One Django backend.
- Clearly separated backend modules.
- Feature-based frontend organization.
- No microservices.
- No database for the initial assessment implementation.

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
   OpenRouteService  ORS HGV        |
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

The frontend must never call ORS or Open-Meteo directly.

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
- Axios or Fetch API

Use local component state for UI interactions. Do not introduce a global state library unless there is a demonstrated need.

### Backend

- Python
- Django
- Django REST Framework
- HTTPX
- Pytest
- pytest-django
- drf-spectacular for OpenAPI documentation

Use a Python version supported by the selected Django release and deployment platform.

### External Services

| Service | Responsibility |
|---|---|
| OpenRouteService | Geocoding |
| OpenRouteService | Heavy-vehicle routing |
| Open-Meteo | Hourly weather forecasts |
| OpenStreetMap | Map tiles |

Use ORS `driving-hgv` for routing.

Keep in mind that ORS alternative-route functionality has documented distance restrictions. Verify feasibility before building around the assumption that three alternatives are always available.

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
│   ├── manage.py
│   ├── requirements.txt
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
├── .gitignore
└── README.md
```

Do not create empty folders or unnecessary files simply to match this diagram. Create them when the corresponding implementation is needed.

## 5. Backend Module Responsibilities

Each module should be a proper Django app with its own `apps.py` and tests.

### 5.1 Geocoding Module

Responsibilities:

- Send address queries to ORS.
- Normalize geocoding results.
- Return latitude and longitude.
- Handle missing or ambiguous results.
- Handle provider errors and timeouts.

It should not calculate routes or weather risks.

### 5.2 Routing Module

Responsibilities:

- Communicate with ORS.
- Use the `driving-hgv` profile.
- Request alternative routes where supported.
- Normalize route geometry.
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

Create one application-level orchestrator responsible for coordinating the analysis.

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
8. Match forecasts to checkpoint ETAs
       |
       v
9. Calculate checkpoint risks
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

Database models are not required for this assessment.

### TripInput

- origin
- destination
- departure_time
- load_weight_lbs
- checkpoint_interval_miles

### Location

- label
- latitude
- longitude

### Route

- id
- label
- geometry
- distance_miles
- duration_seconds
- estimated_arrival_time
- checkpoints

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
- estimated_arrival_time
- low_miles
- moderate_miles
- high_miles
- severe_miles
- no_travel_miles
- unknown_miles
- average_risk_score
- weather_coverage_percent

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
7. Include the destination as the final endpoint where appropriate.

Use a reliable geodesic calculation or a suitable geometry library.

Convert provider distances to miles at the provider normalization boundary.

Avoid repeatedly converting units throughout the application.

## 9. ETA and Weather Matching

All internal timestamps must be timezone-aware.

Use provider step/segment durations when sufficient information is available.

Otherwise:

`elapsed_time = route_duration × checkpoint_distance / route_total_distance`

Then:

`checkpoint_eta = departure_time + elapsed_time`

Match checkpoint ETA to the nearest available hourly weather timestamp.

Store both:
- Estimated checkpoint arrival time.
- Actual forecast timestamp used.

If the forecast is unavailable, mark it as `UNKNOWN`.

Do not substitute unrelated weather data.

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

## 12. API Design

Primary endpoint:

`POST /api/v1/routes/analyze/`

Supporting endpoint:

`GET /api/health/`

The request serializer validates:

- Origin and destination.
- Timezone-aware departure time.
- Positive cargo weight.
- Checkpoint interval of 10, 25, or 50 miles.

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

Generate OpenAPI documentation.

Keep frontend TypeScript types aligned with the backend contract.

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

- Forecast slider
- Weather information
- Selected forecast timestamp

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

### Backend Unit Tests

Prioritize:

- Wind thresholds.
- Rain thresholds.
- Snow thresholds.
- Cargo-weight overrides.
- Unknown data handling.
- Checkpoint distance calculations.
- Coordinate interpolation.
- ETA calculations.
- Weather unit conversions.
- Forecast timestamp matching.
- Route mileage aggregation.
- Weighted average risk.
- Route ranking.

### Backend Integration Tests

Mock external requests.

Test:
- ORS geocoding.
- ORS routing.
- One, two, and three returned routes.
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
- Unsupported intervals.
- Provider errors.
- Partial weather coverage.
- Response structure.

### Frontend Tests

Test:
- Form validation.
- Loading and error states.
- Route selection.
- Checkpoint selection.
- Forecast slider.
- No repeated analysis request when the slider changes.

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

## 19. Architecture Decisions

| Decision | Choice | Reason |
|---|---|---|
| Backend architecture | Modular monolith | Clear separation without microservice complexity |
| Persistence | No database initially | Stateless assessment workflow |
| Routing | ORS `driving-hgv` | Heavy-vehicle routing |
| Weather | Open-Meteo | Non-commercial assessment use within its terms |
| Map | Leaflet + OSM | Open-source mapping |
| Risk calculations | Backend domain functions | One authoritative implementation |
| Recommendation | Lexicographic comparison | Matches assessment requirements |
| Frontend state | Local state + TanStack Query | Avoid unnecessary complexity |
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