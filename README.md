# Weather-Aware Truck Routing

A web application that helps truck drivers and dispatchers compare heavy-vehicle routes by distance, travel time, forecast weather, and cargo weight.

Given an origin, destination, departure time, and cargo weight, the application:

1. Suggests places while the user types each address, then geocodes the addresses with OpenRouteService (a place chosen from the suggestions is used as given) and retrieves up to three genuine truck routes from Valhalla (`truck` costing).
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
- **Phase 7 (Backend Integration):** done. `POST /api/v1/routes/analyze/` runs the full analysis in one request and returns routes, checkpoints, weather, risks, metrics, and the recommendation.
- **Phase 8 (Frontend Foundation):** done. Trip form with validation, loading and error states, connected to the analysis API, with a summary of the recommendation and warnings.
- **Phase 9 (Results and Visualization):** done. Route comparison in ranked order, an interactive map with every route, risk-coloured checkpoints, checkpoint details, a 0–48-hour forecast slider, and a weather heatmap along the selected route, with a legend that labels every risk level.
- **Phase 10 (Testing and Delivery):** in progress. Deployed on Render (backend Docker service and frontend static site) with a Cloudflare Worker proxying Open-Meteo; see [`docs/deployment.md`](docs/deployment.md). Since Phase 9: place suggestions while typing addresses, chosen places used without re-geocoding, and 0 lb (empty truck) accepted as a cargo weight.

## Documentation

| Document | Purpose |
|---|---|
| [`docs/requirements.md`](docs/requirements.md) | What the application must do: business rules, risk thresholds, ranking order, API contract |
| [`docs/architecture.md`](docs/architecture.md) | How it is built: modules, data structures, API design, testing strategy |
| [`docs/deployment.md`](docs/deployment.md) | How the backend, frontend, and weather proxy are deployed and configured |
| [`docs/CLAUDE.md`](docs/CLAUDE.md) | Implementation rules and phase plan |
| [`frontend/README.md`](frontend/README.md) | Frontend setup, structure, and design |
| [`cloudflare/open-meteo-proxy/README.md`](cloudflare/open-meteo-proxy/README.md) | The Open-Meteo proxy Worker: security rules, tests, and deployment |

## Technology Stack

| Area | Technology |
|---|---|
| Frontend | React, TypeScript, Vite, Material UI, React Leaflet, TanStack Query, Axios |
| Backend | Python 3.12, Django, Django REST Framework, HTTPX, drf-spectacular, Gunicorn |
| Geocoding and address suggestions | OpenRouteService |
| Truck routing | Valhalla |
| Weather | Open-Meteo, through a Cloudflare Worker proxy in deployment |
| Map tiles | OpenStreetMap |
| Hosting | Render (Docker web service and static site), Cloudflare Workers |
| Backend testing | Pytest, pytest-django |
| Frontend testing | Vitest, React Testing Library |

The application is a stateless modular monolith: one Django backend, one React frontend, no database. The frontend never calls external providers directly; all provider access and risk calculation happen in the backend.

## Repository Structure

```text
weather-aware-truck-routing/
├── backend/     Django REST API (modules: geocoding, routing, checkpoints, weather, risk, recommendation)
├── frontend/    React + TypeScript + Vite client
├── cloudflare/  open-meteo-proxy: Cloudflare Worker that forwards weather requests in deployment
├── docs/        Requirements, architecture, deployment, and implementation instructions
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
| `/api/v1/routes/analyze/` | Trip analysis (`POST`) |
| `/api/v1/locations/suggestions/?q=…` | Place suggestions while typing an address (`GET`, at least 3 characters) |
| `/api/health/` | Health check |
| `/api/docs/` | Swagger UI |
| `/api/schema/` | OpenAPI schema |

Example request:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/routes/analyze/ \
  -H "Content-Type: application/json" \
  -d '{"origin": "Denver, CO", "destination": "Salt Lake City, UT",
       "departure_time": "2026-11-05T08:00:00-07:00", "load_weight_lbs": 36000,
       "checkpoint_interval_miles": 25}'
```

The departure time must include a UTC offset and must not be in the past. The full response shape is described in [`docs/architecture.md`](docs/architecture.md) (§12) and in Swagger UI.

`requirements.txt` holds runtime dependencies only (used for deployment), including Gunicorn, the production server. `requirements-dev.txt` adds Pytest, pytest-django, pytest-cov, and Ruff.

### Backend with Docker

`backend/Dockerfile` builds the production image: Python 3.12, runtime dependencies only, and Gunicorn serving `config.wsgi`. The image contains no secrets: `.dockerignore` keeps `.env`, tests, and local tooling out, and every setting is read from the environment when the container starts.

Build and run it locally (Docker Desktop or Docker Engine), from `backend/`:

```bash
docker build -t weather-aware-truck-routing-api .
docker run --rm -p 8000:8000 --env-file .env -e PORT=8000 -e DJANGO_DEBUG=False weather-aware-truck-routing-api
```

The API is then at `http://localhost:8000/api/health/`. `--env-file .env` passes the same variables as local development (see [Environment Variables](#environment-variables)); `-e` values take precedence over the file. `PORT` is required: Gunicorn binds to it and fails clearly if it is missing (Render sets it automatically).

Gunicorn settings live in `backend/gunicorn.conf.py`: 2 worker processes with 4 threads each, and a 120-second timeout, longer than the frontend's 90-second wait for an analysis. Override them without rebuilding through Gunicorn's `GUNICORN_CMD_ARGS` variable, for example `-e GUNICORN_CMD_ARGS="--workers 1"`. The analysis rate limit is counted per worker process, so with 2 workers a client can make up to twice `ANALYZE_RATE_LIMIT`.

The API serves JSON only, and Swagger UI loads its scripts from a CDN, so there are no static files to serve and no static-file middleware (such as WhiteNoise) is needed.

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
| `OPEN_METEO_BASE_URL` | Optional. Where weather forecasts are requested; defaults to the public `https://api.open-meteo.com`. Set it to an https proxy (for example a Cloudflare Worker) in deployment; leave it unset locally |
| `OPEN_METEO_PROXY_TOKEN` | Optional secret for that proxy, sent only to it in the `X-Proxy-Token` header. Analyses fail with a configuration error (logged by the backend) if it is set while `OPEN_METEO_BASE_URL` points to Open-Meteo itself, or to a non-https proxy other than `localhost` |
| `ANALYZE_RATE_LIMIT` | **Required.** Analysis requests allowed per client, such as `10/minute`; startup fails if missing or invalid. Excess requests get HTTP 429 |
| `SUGGEST_RATE_LIMIT` | **Required.** Place-suggestion requests allowed per client while typing, such as `30/minute`; startup fails if missing or invalid. Each one is an OpenRouteService call |

Frontend (`frontend/.env`): `VITE_API_BASE_URL` is **required**, the backend URL, for example `http://127.0.0.1:8000`. See `frontend/.env.example`.

## Testing

Backend, from `backend/` with the virtual environment active:

```bash
pytest                 # run tests
pytest --cov           # run tests with coverage
ruff check .           # lint
ruff format --check .  # check formatting
```

Tests never call live external APIs.

Frontend, from `frontend/`: `npm test` (Vitest and React Testing Library), `npm run lint`, and `npm run build`.

Weather proxy Worker, from `cloudflare/open-meteo-proxy/`: `npm test` (Node.js built-in test runner, no dependencies).

CI runs Ruff, `manage.py check`, and Pytest for the backend, and ESLint, the Vitest tests, and a production build for the frontend, on pushes and pull requests to `main`.

## Deployment

The backend runs as a Docker web service and the frontend as a static site on Render, and a Cloudflare Worker forwards weather requests to Open-Meteo. All three use free tiers. [`docs/deployment.md`](docs/deployment.md) covers the service settings, every environment variable, the deployment order, and troubleshooting.

## External Service Terms

- **OpenRouteService:** free tier with daily and per-minute request limits. Used for geocoding and address suggestions only.
- **Valhalla (FOSSGIS public server):** free, no API key, fair-use policy. Truck routes are limited to 1,500 km; longer trips are rejected.
- **Open-Meteo:** the free API is for non-commercial use. Its limits are per IP address, so the deployed backend reaches it through the Cloudflare Worker.
- **Cloudflare Workers:** free plan with a daily request allowance. Hosts the Open-Meteo proxy only.
- **OpenStreetMap:** tiles are used under the OSM tile usage policy, with attribution shown on the map.
