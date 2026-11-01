# Claude Code Instructions

## 1. Read Project Documentation

Before starting implementation, read these files:

1. `docs/requirements.md`
2. `docs/architecture.md`

Follow both documents throughout development.

- `requirements.md` defines what the application must do.
- `architecture.md` defines how the application must be structured and built.
- This file defines how implementation should be carried out.

The root `CLAUDE.md` imports this file so Claude Code loads it automatically. Keep all instructions here.

Do not independently redesign the architecture or introduce new technologies.

## 2. Implementation Rules

- Implement only the requirements documented in the project.
- Follow the approved architecture and folder structure.
- Keep modules and components focused on their responsibilities.
- Keep API views thin and business logic separate.
- Avoid duplicated logic and unnecessary abstractions.
- Use clear naming and type hints where appropriate.
- Use TypeScript types instead of `any`.
- Validate external API responses.
- Handle errors and missing data explicitly.
- Keep API credentials in environment variables.
- Never expose API keys in frontend code.
- Never commit `.env` files.
- Do not fabricate routes, weather data, or analysis results.
- Do not treat unknown weather as low risk.
- Do not change business rules or route-ranking criteria.
- Do not add a database, models, migrations, Django admin, authentication, sessions, Docker, Redis, Celery, or other infrastructure unless explicitly approved.
- Do not install unnecessary dependencies.
- Put runtime dependencies in `backend/requirements.txt` and development/testing dependencies in `backend/requirements-dev.txt`.
- Place module tests in `tests/` packages, not `tests.py` files.

## 3. Implementation Phases

Implement the project phase by phase, in the following order.

### Phase 1 — Backend Foundation

- Configure Django as a stateless application (no database, admin, authentication, or sessions).
- Configure Django REST Framework.
- Implement environment-based settings using `python-dotenv`, and document required variables in `.env.example`.
- Configure CORS using `django-cors-headers`.
- Set up the approved backend structure: modules, `api/`, `application/use_cases/`, and `shared/types.py`.
- Split dependencies into `requirements.txt` and `requirements-dev.txt`.
- Configure Pytest and pytest-django.
- Implement request serializers and validation, including past-departure rejection and the default 25-mile interval.
- Establish the API response and error formats and the documented HTTP status codes, including the ambiguous-geocoding error with candidate locations.
- Add the `/api/health/` endpoint.
- Configure API documentation.

**Completion criteria:** Backend starts successfully, request validation works, and the API contract is established.

### Phase 2 — External API Integrations

- Implement OpenRouteService geocoding, returning candidate locations when a result is ambiguous.
- Apply the approved ambiguity thresholds (confidence within 0.1, more than 25 miles apart); only plausible candidates can be selected.
- Implement heavy-vehicle routing with Valhalla using `truck` costing.
- Request up to two genuine alternate routes.
- Implement the Open-Meteo client.
- Normalize provider responses.
- Configure timeouts and error handling.
- Handle rate limits and missing responses.

**Completion criteria:** Both providers return normalized data, and provider failures are handled correctly. Never fabricate alternative routes.

### Phase 3 — Route and Checkpoint Processing

- Process route geometry.
- Calculate cumulative route distances.
- Generate checkpoints at 10, 25, and 50-mile intervals.
- Include an origin checkpoint at mile 0 and always include a destination checkpoint.
- Interpolate checkpoint coordinates.
- Calculate estimated checkpoint arrival times.
- Handle final partial segments.

**Completion criteria:** Checkpoints are positioned using actual route distance, and ETA calculations are tested.

### Phase 4 — Weather Processing

- Retrieve hourly forecasts for checkpoints.
- Normalize wind, precipitation, and snowfall units.
- Match forecasts to estimated checkpoint arrival times, choosing the earlier timestamp when two are equally close.
- Store the forecast timestamp used.
- Build each checkpoint's 0–48-hour hourly forecast series from the same provider data.
- Handle unavailable forecast hours.
- Handle partial weather responses.

**Completion criteria:** Weather values are correctly normalized and matched to checkpoint ETAs. Missing data remains `UNKNOWN`.

### Phase 5 — Risk Calculation

- Implement wind, rain, and snow thresholds.
- Implement cargo-weight overrides.
- Calculate individual weather risks.
- Calculate final checkpoint risk.
- Calculate risks for each hourly forecast entry.
- Handle unknown values.
- Aggregate route risk miles.
- Calculate distance-weighted average risk.
- Calculate weather coverage.

**Completion criteria:** All business rules match `requirements.md`, including threshold boundaries and cargo-weight conditions. Add unit tests for each rule.

### Phase 6 — Route Recommendation

- Implement the required lexicographic ranking.
- Compare severe-risk miles.
- Compare high-risk miles.
- Compare average risk.
- Compare travel time.
- Implement documented tie-breakers.
- Generate recommendation explanations.
- Generate no-travel and incomplete-data warnings.

**Completion criteria:** Routes are ranked using the exact required criteria and ETA-matched weather only. Do not replace the ranking logic with an alternative weighted score.

### Phase 7 — Backend Integration

- Connect all backend services through the analysis orchestrator.
- Implement `POST /api/v1/routes/analyze/`.
- Return normalized trip, route, checkpoint, weather, risk, and recommendation data.
- Handle provider failures and partial analysis results.
- Add orchestrator tests in `backend/application/tests/`.
- Add API integration tests.

**Completion criteria:** A complete trip analysis works through one API request, and the response follows the documented API contract.

### Phase 8 — Frontend Foundation

- Replace the Vite template content (React, TypeScript, and Vite are already initialized).
- Configure Vitest and React Testing Library.
- Configure Material UI.
- Implement the approved frontend structure.
- Create the API client using Axios.
- Define request and response types.
- Build the trip input form.
- Implement validation, loading, and error states.
- Connect the form to the backend.

**Completion criteria:** A user can submit a valid trip and receive the backend analysis.

### Phase 9 — Results and Visualization

- Implement route comparison components.
- Display route metrics and recommendation explanations.
- Implement the interactive Leaflet map.
- Display origin and destination markers.
- Display route alternatives.
- Display risk-colored checkpoints.
- Implement checkpoint details.
- Implement the 0–48-hour forecast slider using each checkpoint's hourly forecast data. The slider must not calculate risk or change route ranking.
- Display a weather heatmap overlay along the selected route's trip corridor using the available forecast data from the backend response (see `requirements.md` FR-12 and `architecture.md` §13, "Weather heatmap").
- Update the heatmap when the user changes the 0–48-hour forecast slider, using the hourly forecast entries for the selected hour. Do not request new data from the backend.
- Include a clear colour legend explaining the risk levels shown by the heatmap, including `UNKNOWN`/`Unavailable`. Do not rely on colour alone; show labels as well.
- Use only actual backend forecast data for the heatmap. Do not fabricate weather values between checkpoints, and do not present interpolated or blended values as actual provider measurements. Show unavailable (`UNKNOWN`) data as unavailable, never as low risk.
- Build the heatmap with the approved mapping libraries (React Leaflet and Leaflet). Do not add a heatmap plugin or other dependency without approval.
- Display unavailable forecast data clearly.
- Implement responsive layouts.

**Completion criteria:** Users can inspect routes, checkpoints, risks, forecast data, and the weather heatmap, which updates with the forecast slider. Changing the selected route, checkpoint, or forecast hour must not unnecessarily trigger another routing analysis.

### Phase 10 — Testing and Delivery

- Run backend unit and integration tests.
- Run frontend tests.
- Fix identified defects.
- Run linting and production builds.
- Select a production WSGI server and static-file handling, and get approval before installing them.
- Configure deployment environment variables.
- Deploy frontend and backend.
- Test the complete hosted application.
- Update the README with setup, environment, API, testing, and deployment instructions.
- Document known limitations.
- Prepare the 5–10-minute demonstration video.

**Completion criteria:** The hosted application works, the main tests pass, documentation is complete, and the assessment can be demonstrated.

## 4. Testing Requirements

- Write unit tests for business logic.
- Test threshold boundaries and cargo-weight conditions.
- Test checkpoint distance and ETA calculations.
- Test weather conversions and timestamp matching.
- Test route aggregation and ranking.
- Mock external API requests.
- Test provider failures and incomplete data.
- Test frontend form validation and forecast interactions using Vitest and React Testing Library.
- Run relevant tests before completing each phase.

Never claim a test passed unless it was actually executed.

## 5. Phase Execution Rules

- Work on only one phase at a time.
- Do not start the next phase until the current phase is complete.
- Do not implement future phases prematurely.
- Inspect existing code before modifying files.
- Do not overwrite working code without a reason.
- Do not create unnecessary files or folders.
- Do not make unrelated changes.
- If an architectural change becomes necessary, explain why and request approval before implementing it.

At the end of each phase, provide:

1. Implementation summary.
2. Files created or modified.
3. Tests executed and their actual results.
4. Remaining issues or limitations.
5. Confirmation that the phase is ready for review.

Wait for approval before proceeding to the next phase.