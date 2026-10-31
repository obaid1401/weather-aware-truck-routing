# Weather-Aware Truck Routing

A web application that helps truck drivers and dispatchers compare heavy-vehicle routes by distance, travel time, forecast weather, and cargo weight.

Given an origin, destination, departure time, and cargo weight, the application:

1. Geocodes the addresses with OpenRouteService and retrieves up to three genuine truck routes from Valhalla (`truck` costing).
2. Places weather checkpoints along each route at 10, 25, or 50-mile intervals.
3. Estimates when the truck reaches each checkpoint and matches it to an Open-Meteo hourly forecast.
4. Rates wind, rain, and snow risk at each checkpoint, including cargo-weight rules for high wind.
5. Ranks the routes and recommends one, while clearly flagging any no-travel conditions.
6. Shows the routes, checkpoints, and risks on an interactive map with a 0–48-hour forecast slider.

## Project Status

Implementation follows the phases in [`docs/CLAUDE.md`](docs/CLAUDE.md).

- **Phase 1 (Backend Foundation):** done. Environment-based settings, DRF, CORS, request validation, the error format, the health endpoint, and OpenAPI docs.
- **Phase 2 (External API Integrations):** done. ORS geocoding, Valhalla truck routing, and Open-Meteo hourly forecasts.
- **Phase 3 (Route and Checkpoint Processing):** done. Checkpoints at mile 0, every 10/25/50 miles along the route geometry, and at the destination, with step-based arrival time estimates.
- **Phase 4 (Weather Processing):** done. Forecasts matched to each checkpoint's arrival time, a 0–48-hour hourly series per checkpoint, shared locations fetched once, and missing data kept as unknown.
- **Phase 5 (Risk Calculation):** done. Wind, rain, and snow risk with cargo-weight rules, final checkpoint and hourly risks, and route risk miles, distance-weighted average risk, and weather coverage.
- **Phase 6 (Route Recommendation):** done. Lexicographic ranking (severe miles, high miles, average risk, travel time, then distance and provider order), explanations for every route, and NO_TRAVEL and incomplete-data warnings.
- **Next:** Phase 7 (Backend Integration). The trip analysis endpoint and the frontend UI are not built yet.

## Documentation

| Document | Purpose |
|---|---|
| [`docs/requirements.md`](docs/requirements.md) | What the application must do: business rules, risk thresholds, ranking order, API contract |
| [`docs/architecture.md`](docs/architecture.md) | How it is built: modules, data structures, API design, testing strategy |
| [`docs/CLAUDE.md`](docs/CLAUDE.md) | Implementation rules and phase plan |

## Technology Stack

| Area | Technology |
|---|---|
| Frontend | React, TypeScript, Vite, Material UI, React Leaflet, TanStack Query, Axios |
| Backend | Python 3.12, Django, Django REST Framework, HTTPX, drf-spectacular |
| Geocoding | OpenRouteService |
| Truck routing | Valhalla |
| Weather | Open-Meteo |
| Map tiles | OpenStreetMap |
| Backend testing | Pytest, pytest-django |
| Frontend testing | Vitest, React Testing Library |

The application is a stateless modular monolith: one Django backend, one React frontend, no database. The frontend never calls external providers directly; all provider access and risk calculation happen in the backend.

## Repository Structure

```text
weather-aware-truck-routing/
├── backend/     Django REST API (modules: geocoding, routing, checkpoints, weather, risk, recommendation)
├── frontend/    React + TypeScript + Vite client
├── docs/        Requirements, architecture, and implementation instructions
└── .github/     CI workflow
```

See [`docs/architecture.md`](docs/architecture.md) for the full target structure.

## Local Setup

### Prerequisites

- Python 3.12
- Node.js 24 and npm
- A free OpenRouteService API key (for geocoding). Valhalla's public server needs no key.

### Backend

```bash
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env    # then edit the values
python manage.py check
python manage.py runserver
```

The backend runs at `http://127.0.0.1:8000/`.

| URL | Purpose |
|---|---|
| `/api/health/` | Health check |
| `/api/docs/` | Swagger UI |
| `/api/schema/` | OpenAPI schema |

`requirements.txt` holds runtime dependencies only (used for deployment). `requirements-dev.txt` adds Pytest, pytest-django, pytest-cov, and Ruff.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

The frontend runs at `http://localhost:5173/`.

## Environment Variables

Secrets are kept in environment variables and never committed. Copy `.env.example` to `.env` and fill in the values.

Backend (`backend/.env`):

| Variable | Description |
|---|---|
| `DJANGO_SECRET_KEY` | **Required** in every environment; startup fails if missing |
| `DJANGO_DEBUG` | `True` for local development only; defaults to `False` |
| `DJANGO_ALLOWED_HOSTS` | Comma-separated host names |
| `CORS_ALLOWED_ORIGINS` | Comma-separated frontend origins allowed to call the API |
| `ORS_API_KEY` | **Required.** OpenRouteService API key, used for geocoding; startup fails if missing |
| `VALHALLA_BASE_URL` | Valhalla server for truck routing; defaults to `https://valhalla1.openstreetmap.de` |

Frontend variables are defined in Phase 8.

## Testing

Backend, from `backend/` with the virtual environment active:

```bash
pytest                 # run tests
pytest --cov           # run tests with coverage
ruff check .           # lint
ruff format --check .  # check formatting
```

Tests never call live external APIs. Frontend tests (Vitest and React Testing Library) are added in Phase 8.

CI runs Ruff, `manage.py check`, and Pytest for the backend, and a production build for the frontend, on pushes and pull requests to `main`.

## Deployment

Deployment instructions will be added in Phase 10. The frontend and backend will be deployed separately on free-tier hosting.

## External Service Terms

- **OpenRouteService:** free tier with daily and per-minute request limits. Used for geocoding only.
- **Valhalla (FOSSGIS public server):** free, no API key, fair-use policy. Truck routes are limited to 1,500 km; longer trips are rejected.
- **Open-Meteo:** the free API is for non-commercial use.
- **OpenStreetMap:** tiles are used under the OSM tile usage policy, with attribution shown on the map.
