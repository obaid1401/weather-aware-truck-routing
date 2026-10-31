# Weather-Aware Truck Routing — Requirements

## 1. Project Overview

Build a web application that helps truck drivers and dispatchers compare routes based on travel distance, estimated travel time, weather conditions, and cargo weight.

The user provides:

- Origin
- Destination
- Departure date and time
- Cargo weight in pounds

The application retrieves heavy-vehicle routes, generates weather checkpoints along each route, evaluates weather risks, and recommends the best route according to the assessment's ranking rules.

The application must provide an interactive map where users can inspect routes, checkpoints, weather conditions, and risk levels.

The goal is to deliver a reliable, explainable, and well-tested assessment project.

## 2. Main Objectives

1. Retrieve up to three genuine heavy-vehicle route alternatives.
2. Generate weather checkpoints at configurable distance intervals.
3. Estimate checkpoint arrival times.
4. Retrieve weather forecasts corresponding to checkpoint arrival times.
5. Calculate weather and cargo-related risks.
6. Compare routes using the specified ranking rules.
7. Display route information and weather risks on an interactive map.
8. Provide a 0–48-hour forecast slider.
9. Handle missing data and external API failures properly.

## 3. Technology and External Services

Use the following services:

| Purpose | Technology |
|---|---|
| Frontend | React, TypeScript, Vite |
| UI components | Material UI |
| Backend | Python, Django, Django REST Framework |
| HTTP requests | HTTPX |
| Routing | Valhalla (`truck` costing) |
| Geocoding | OpenRouteService |
| Weather | Open-Meteo |
| Interactive map | React Leaflet |
| Map data and tiles | OpenStreetMap |
| API documentation | OpenAPI / Swagger |
| Backend testing | Pytest, pytest-django |
| Frontend testing | Vitest, React Testing Library |

### External API restrictions

All external services must be usable without payment for the assessment within their applicable free usage limits.

**OpenRouteService**
- Use its geocoding service only.
- Respect its free request limits.

**Valhalla**
- Use Valhalla for heavy-vehicle routing with the `truck` costing model.
- Request up to two alternates (three routes in total).
- Use the public FOSSGIS server (`valhalla1.openstreetmap.de`) initially, and follow its usage policy. The server is configurable.
- Do not pass cargo weight to Valhalla; cargo-weight rules are applied by the risk logic.

Important: Valhalla may return fewer than three routes. If fewer routes are returned, display only those routes. Never fabricate or duplicate alternatives. The public server limits truck routes to 1,500 km; longer trips are rejected.

**Open-Meteo**
- Use hourly weather forecasts.
- The free service is intended for non-commercial use.
- Confirm that the assessment/demo use complies with its current terms.
- Commercial production use requires checking the appropriate licensing.

**OpenStreetMap**
- Use standard OSM tiles.
- Display the required attribution.
- Follow the tile usage policy.
- Do not bulk-download tiles or treat the public tile service as an unlimited production service.

General rules:
- Do not introduce paid APIs or paid SDKs.
- Do not require a paid subscription or credit card.
- Do not silently switch to paid providers when quotas are exceeded.
- Handle rate limits and provider failures gracefully.
- Keep provider integrations replaceable.
- Never invent routing or weather data.

## 4. User Workflow

1. User opens the application.
2. User enters origin and destination.
3. User selects departure date and time.
4. User enters cargo weight.
5. User selects checkpoint interval.
6. User submits the form.
7. Backend retrieves location coordinates.
8. Backend retrieves available heavy-vehicle routes.
9. Backend generates checkpoints for each route.
10. Backend estimates checkpoint arrival times.
11. Backend retrieves hourly weather forecasts.
12. Backend calculates checkpoint risk levels.
13. Backend calculates route-level metrics.
14. Backend ranks routes and selects a recommendation.
15. Frontend displays the results on a map and in route comparison panels.
16. User can change the forecast slider to inspect weather conditions over the next 48 hours.

## 5. Functional Requirements

### FR-01: Trip Input

The application must collect:

- Origin address
- Destination address
- Departure date and time
- Cargo weight in pounds
- Checkpoint interval

Validation:
- Origin and destination are required.
- Departure time must be valid and timezone-aware.
- Departure time must not be in the past. Reject past departure times with a validation error.
- Cargo weight must be a positive number.
- Checkpoint interval must be 10, 25, or 50 miles. If omitted, use 25 miles.
- Prevent duplicate submissions while analysis is running.
- Preserve form values if a request fails.

### FR-02: Checkpoint Intervals

Support:

- 10 miles
- 25 miles
- 50 miles

Use 25 miles as the default.

Checkpoint placement must use cumulative route distance, not the number of coordinates in the route geometry.

Checkpoint placement rules:

- Always include an origin checkpoint at mile 0.
- Place intermediate checkpoints at each multiple of the selected interval along the route.
- Always include a destination checkpoint at the route's total distance, even when it does not align with the selected interval.
- Do not create a duplicate checkpoint when the destination falls exactly on an interval multiple.

For every checkpoint, store:

- Checkpoint ID
- Route ID
- Cumulative distance from origin
- Latitude and longitude
- Estimated arrival time
- Actual forecast timestamp used
- Wind speed
- Precipitation
- Snowfall
- Individual weather risk levels
- Final risk level
- Data availability status
- Hourly forecast data for the 0–48-hour period after departure (see FR-12)

### FR-03: Route Generation

- Geocode the origin and destination using ORS.
- Route with Valhalla using the `truck` costing model.
- Request up to three routes (the primary route and up to two alternates).
- Normalize route geometry, distance, and duration.
- Validate returned route data.
- Assign stable application route IDs.
- Handle provider errors and unavailable alternatives.

Geocoding results:

- If an address returns no usable result, stop the analysis and return a geocoding error.
- If an address is ambiguous, stop the analysis and return an error that includes the candidate locations (label, latitude, longitude). Do not silently choose one.
- An address is ambiguous when the provider returns multiple plausible, materially different candidates with similar confidence scores. Approved thresholds:
  - A candidate is plausible when its confidence is within 0.1 of the best confidence.
  - Plausible candidates are materially different when they are more than 25 miles apart.
  - Only plausible candidates can be selected. When there is no ambiguity, the first plausible candidate in provider order is used.

Never create fake alternatives.

If the provider returns only one or two routes, show the actual number returned and explain the limitation.

If no valid route is returned, stop the analysis and display an appropriate error.

### FR-04: Checkpoint Arrival Time

Estimate the time at which the truck reaches each checkpoint.

Preferred approach:
- Use provider step or segment durations when sufficient information is available.

Fallback approach:

`checkpoint_elapsed_seconds = route_duration_seconds × (checkpoint_distance_miles / route_total_distance_miles)`

`checkpoint_eta = departure_time + checkpoint_elapsed_seconds`

This is an estimate, not a live traffic prediction.

Keep this calculation in a dedicated backend service and test it independently.

### FR-05: Weather Retrieval

Use Open-Meteo hourly forecasts for:

- Wind speed
- Precipitation
- Snowfall

Retrieve weather based on checkpoint coordinates and estimated arrival times.

Normalize units:

| Measurement | Internal Unit |
|---|---|
| Wind | mph |
| Rain | inches/hour |
| Snow | inches/hour |

Open-Meteo hourly precipitation values are accumulations in millimetres. Convert them to inches by dividing by 25.4.

Hourly snowfall values are provided in centimetres. Convert them to inches by dividing by 2.54.

For this assessment, treat the hourly accumulations as hourly rates when applying the supplied thresholds. Document this assumption.

Weather matching rules:

- Match checkpoint ETA to the nearest available hourly forecast timestamp.
- If two hourly timestamps are equally close to the ETA, choose the earlier timestamp.
- Store the timestamp actually used.
- Do not use current weather as a substitute for unavailable future weather.
- If forecast data is unavailable for the requested period (missing or outside the available horizon), mark it `UNKNOWN`.
- Never convert missing weather into `LOW`.

Use batching or multi-coordinate requests where supported. Avoid unnecessarily sending one request per checkpoint.

The same forecast retrieval must also provide the 0–48-hour hourly data required by FR-12. Do not make separate provider requests for the forecast slider.

### FR-06: Weather Risk Rules

Use the following thresholds.

| Factor | Low | Moderate | High | Severe | No Travel |
|---|---|---|---|---|---|
| Wind | <25 mph | 25 to <35 | 35 to <45 | 45 to <55 | >=55 mph |
| Rain | <0.10 in/hr | 0.10 to <0.25 | 0.25 to <0.50 | 0.50 to 1.00 | >1.00 in/hr |
| Snow | <0.5 in/hr | 0.5 to <1.0 | 1.0 to <2.0 | 2.0 to 3.0 | >3.0 in/hr |

Boundary handling must be consistent.

Examples:
- Exactly 55 mph wind is `NO_TRAVEL`.
- Exactly 1.00 in/hr rain is `SEVERE`.
- Exactly 3.00 in/hr snow is `SEVERE`.

### FR-07: Cargo Weight Rules

Apply the cargo rules to wind risk:

- Wind >=55 mph: `NO_TRAVEL` for every load.
- Wind >=45 and <55 mph with cargo weight >30,000 lb: `NO_TRAVEL`.
- Wind >=35 and <45 mph with cargo weight >40,000 lb: at least `SEVERE`.

Use strict greater-than comparisons.

Therefore:
- Exactly 30,000 lb does not trigger the >30,000 rule.
- Exactly 40,000 lb does not trigger the >40,000 rule.

If wind data is unknown, do not assume the load-related risk is safe.

### FR-08: Final Checkpoint Risk

Risk order:

`LOW < MODERATE < HIGH < SEVERE < NO_TRAVEL`

For every checkpoint:

1. Calculate wind risk.
2. Calculate rain risk.
3. Calculate snow risk.
4. Apply cargo-weight rules to wind risk.
5. Select the highest known risk.

Unknown handling:

- If one factor is unknown but another factor has a known risk, use the highest known risk and include an incomplete-data warning.
- If all factors are unknown, final risk is `UNKNOWN`.
- Never treat unknown as low.

Return factor-level risk values so the frontend can explain the final result.

### FR-09: Route Metrics

Calculate for each route:

- Total distance
- Estimated duration
- Estimated arrival time
- Number of checkpoints
- Low-risk miles
- Moderate-risk miles
- High-risk miles
- Severe-risk miles
- No-travel miles
- Unknown miles
- Average risk score
- Weather coverage percentage

Risk score mapping:

| Risk | Score |
|---|---:|
| LOW | 1 |
| MODERATE | 2 |
| HIGH | 3 |
| SEVERE | 4 |
| NO_TRAVEL | 5 |

Calculate the average risk using a distance-weighted average, not a simple average of checkpoint scores.

For mileage aggregation:

- Each pair of consecutive checkpoints defines a segment.
- Assign the segment the risk of its downstream checkpoint.
- Include the final partial segment.
- Count each route mile at most once.
- Keep unknown miles separate from known risk categories.
- Report weather coverage separately.

Document this segment-risk approximation.

### FR-10: Route Recommendation

Rank routes using this exact order:

1. Fewest severe-risk miles.
2. Fewest high-risk miles.
3. Lowest average risk score.
4. Shortest estimated travel time.

This must be a lexicographic comparison, not a weighted scoring formula.

Route metrics, ranking, and the recommendation must always use the weather matched to each checkpoint's estimated arrival time. The forecast slider (FR-12) never affects them.

If all four criteria are tied:
- Prefer the shorter route.
- If still tied, preserve provider order.

Important safety requirement:

`NO_TRAVEL` exposure must be displayed prominently.

The assessment's ranking order does not explicitly include no-travel miles. Do not silently change the ranking logic by adding it as a primary ranking criterion.

However:
- Display no-travel miles clearly.
- Warn users when a route contains no-travel conditions.
- If all routes contain no-travel exposure, state that none is free of those conditions.
- Show weather coverage so incomplete data is not mistaken for a fully safe assessment.

If there are no valid routes, do not produce a recommendation.

### FR-11: Interactive Map

The map must show:

- Origin marker
- Destination marker
- All genuine route alternatives
- Selected route with distinct styling
- Checkpoint markers
- Risk-based checkpoint colors
- Risk legend
- Checkpoint details when selected

The route comparison panel must display:

- Route name
- Distance
- Estimated duration
- Estimated arrival
- Severe miles
- High-risk miles
- No-travel miles
- Average risk
- Weather coverage
- Recommendation status

### FR-12: Forecast Slider

Provide a slider from 0 to 48 hours after departure.

Data contract:

- Each checkpoint contains hourly forecast data for the 0–48-hour period after departure, where available: one entry per hour offset from 0 to 48.
- Each entry's target time is `departure_time + hour_offset`. It is matched to a forecast timestamp using the FR-05 nearest-timestamp rule, including the earlier-timestamp tie-break.
- Each entry contains the normalized weather values, the individual factor risks, and the final risk, calculated by the backend using the trip's cargo weight.
- Missing forecast data is represented as `UNKNOWN`.

The slider selects an hour relative to departure and must:

- Display the selected hour.
- Display the corresponding timestamp.
- Update the checkpoint weather and risk visualization using the matching hourly entry.
- Show unavailable forecast values as `UNKNOWN` or `Unavailable`.

The slider shows the forecast conditions at each checkpoint location at the selected hour, regardless of when the truck is expected to reach that checkpoint.

Slider interaction is for visualization only:

- It must use previously retrieved forecast data.
- It must not trigger a new route-generation or weather request.
- It must not change route metrics, ranking, or the recommendation.
- The frontend must not calculate risk; it displays the risk values provided by the backend.

The map is a forecast-based checkpoint/corridor visualization, not live weather radar.

### FR-13: Error Handling

Handle:

- Invalid form input
- Departure times in the past
- Geocoding failures
- Ambiguous geocoding results (return the candidate locations)
- No routes returned
- Routing provider errors
- API quota/rate-limit errors
- Weather provider failures
- Partial weather data
- Missing forecast hours
- Network timeouts

Provide useful error messages and allow the user to retry without losing form values.

Never show a successful recommendation if the required analysis has failed.

## 6. API Contract

Primary endpoint:

`POST /api/v1/routes/analyze/`

Example request:

```json
{
  "origin": "Denver, CO",
  "destination": "Salt Lake City, UT",
  "departure_time": "2026-11-05T08:00:00-07:00",
  "load_weight_lbs": 36000,
  "checkpoint_interval_miles": 25
}
```

`checkpoint_interval_miles` is optional and defaults to 25.

Health endpoint: `GET /api/health/`

The response should contain:

- Trip information
- Geocoded origin and destination
- Available routes
- Route geometries
- Checkpoints
- Weather data
- Individual risk factors
- Final checkpoint risks
- Hourly checkpoint forecasts and risks for 0–48 hours after departure
- Route-level metrics
- Recommendation
- Ranking explanations
- Safety warnings
- Forecast window
- Provider warnings

Use ISO-8601 timestamps.

Use consistent risk enum values:

`LOW`, `MODERATE`, `HIGH`, `SEVERE`, `NO_TRAVEL`, `UNKNOWN`

Define concrete DRF serializers for the response. Do not expose raw provider responses as the public API contract.

Return structured errors with these HTTP status codes:

| Status | Use |
|---|---|
| 200 | Successful request |
| 400 | Invalid request |
| 422 | Ambiguous geocoding; address not found; no route found (including the routing server's distance limit) |
| 502 | Provider error |
| 503 | Provider rate limit or temporary unavailability |
| 504 | Provider timeout |

Keep all API credentials on the backend.

Add OpenAPI documentation.

## 7. Non-Functional Requirements

### Reliability
- External calls must have timeouts.
- Handle malformed provider responses.
- Handle rate limits.
- Support partial weather failures.
- Never fabricate data.

### Maintainability
- Separate provider integrations from business logic.
- Keep risk thresholds in one location.
- Keep API views thin.
- Avoid duplicated business rules.
- Use clear names and explicit types.

### Performance
- Batch weather requests where possible.
- Avoid repeating routing when the user changes the selected route or forecast slider.
- Use bounded concurrency.
- Show loading feedback.

### Security
- Keep API keys in environment variables.
- Never expose credentials in frontend code.
- Restrict CORS.
- Validate input.
- Do not expose internal stack traces.

### Usability
- Responsive layout.
- Accessible form labels.
- Keyboard-operable controls.
- Risk must be communicated through labels as well as colors.
- Clear loading, empty, success, and error states.

## 8. Acceptance Criteria

The project is ready for evaluation when:

1. A user can submit a valid trip.
2. Routing uses the heavy-vehicle profile.
3. Only genuine provider-returned alternatives are displayed.
4. Checkpoints are generated using cumulative route distance.
5. Checkpoint ETAs are calculated correctly.
6. Weather is matched to checkpoint ETA.
7. All weather thresholds are implemented correctly.
8. Cargo-weight overrides are implemented correctly.
9. Unknown weather is handled explicitly.
10. Route miles are aggregated without double-counting.
11. Average risk is distance-weighted.
12. Recommendation follows the exact required ranking order.
13. No-travel exposure is clearly displayed.
14. The map shows routes and risk-based checkpoints.
15. The forecast slider works without re-running routing and without changing the route ranking.
16. API and frontend errors are handled.
17. Core business logic has automated tests.
18. Setup and deployment instructions are documented.
19. The hosted application works with a real trip.
20. The demo video explains the working application and important engineering decisions.