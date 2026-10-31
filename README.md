# Weather-Aware Truck Routing

A web application that helps truck drivers and dispatchers compare heavy-vehicle routes by distance, travel time, forecast weather, and cargo weight.

Given an origin, destination, departure time, and cargo weight, the application:

1. Retrieves up to three genuine heavy-vehicle routes from OpenRouteService (`driving-hgv`).
2. Places weather checkpoints along each route at 10, 25, or 50-mile intervals.
3. Estimates when the truck reaches each checkpoint and matches it to an Open-Meteo hourly forecast.
4. Rates wind, rain, and snow risk at each checkpoint, including cargo-weight rules for high wind.
5. Ranks the routes and recommends one, while clearly flagging any no-travel conditions.
6. Shows the routes, checkpoints, and risks on an interactive map with a 0–48-hour forecast slider.

## Project Status

The project is set up but not yet implemented. The backend and frontend contain framework scaffolding only. Implementation follows the phases in [`docs/CLAUDE.md`](docs/CLAUDE.md); Phase 1 (Backend Foundation) is next.

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
| Routing and geocoding | OpenRouteService |
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
- A free OpenRouteService API key (needed once the provider integrations are implemented)

### Backend

```bash
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
python manage.py check
python manage.py runserver
```

The backend runs at `http://127.0.0.1:8000/`.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

The frontend runs at `http://localhost:5173/`.

## Environment Variables

Secrets are kept in environment variables and never committed. Each app will have a `.env.example` listing its required variables; copy it to `.env` and fill in the values. The variables are defined during Phase 1 (backend) and Phase 8 (frontend).

## Testing

Backend tests (Pytest) and frontend tests (Vitest and React Testing Library) are added as each phase is implemented. CI currently runs `manage.py check` for the backend and a production build for the frontend on pushes and pull requests to `main`.

## Deployment

Deployment instructions will be added in Phase 10. The frontend and backend will be deployed separately on free-tier hosting.

## External Service Terms

- **OpenRouteService:** free tier with daily and per-minute request limits.
- **Open-Meteo:** the free API is for non-commercial use.
- **OpenStreetMap:** tiles are used under the OSM tile usage policy, with attribution shown on the map.
