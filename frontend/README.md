# Weather-Aware Truck Routing — Frontend

React + TypeScript client for the Weather-Aware Truck Routing application. It collects trip details, sends them to the backend analysis API, and displays the result.

The frontend only displays data from the backend. It never calls OpenRouteService, Valhalla, or Open-Meteo directly and never calculates risk.

## Status

- **Phase 8 (Frontend Foundation):** done. Trip form with validation, loading and error states, connected to `POST /api/v1/routes/analyze/`, with a summary of the recommendation and all warnings.
- **Next:** Phase 9 (Results and Visualization): route comparison, the interactive map, the forecast slider, and the weather heatmap.

## Stack

- React, TypeScript (strict), Vite
- Material UI
- TanStack Query for the analysis request
- Axios as the HTTP client
- Vitest and React Testing Library for tests
- React Leaflet and Leaflet (used from Phase 9)

## Getting Started

Requires Node.js 24 and npm, and the backend running (see the root README).

```bash
npm install
cp .env.example .env   # Windows: copy .env.example .env
npm run dev
```

The development server runs at `http://localhost:5173/`. Open it at that address: the backend allows this origin in `CORS_ALLOWED_ORIGINS`.

## Scripts

| Command | Description |
|---|---|
| `npm run dev` | Start the development server |
| `npm run build` | Type-check and build for production into `dist/` |
| `npm run preview` | Serve the production build locally |
| `npm run lint` | Run ESLint |
| `npm test` | Run the tests once |
| `npm run test:watch` | Run the tests in watch mode |

## Environment Variables

Copy `.env.example` to `.env`. Never put API keys or other secrets here: anything prefixed `VITE_` is bundled into the public build.

| Variable | Description |
|---|---|
| `VITE_API_BASE_URL` | **Required.** Base URL of the Django backend, for example `http://127.0.0.1:8000`. If it is missing, the app shows a configuration error instead of starting. |

## Structure

```text
src/
├── main.tsx
├── app/                     App, providers, configuration
│   └── pages/               TripAnalysisPage (composes the features)
├── features/
│   ├── analysis/
│   │   ├── api/             analyzeTrip (POST /api/v1/routes/analyze/)
│   │   ├── hooks/           useAnalyzeTrip (TanStack Query mutation)
│   │   ├── services/        analysisResponse: runtime response checks; apiProblem: error normalization
│   │   └── types/           Request, response, and error types (mirror the backend serializers)
│   ├── trip/
│   │   ├── components/      TripForm
│   │   └── schemas/         tripFormSchema: form values and validation
│   └── recommendation/
│       └── components/      AnalysisSummary (recommendation and warnings)
└── shared/
    ├── api/                 Axios client
    ├── components/          AppShell, ConfigurationErrorScreen
    ├── theme/               Material UI theme
    ├── utils/               Date/time and display formatting
    └── test/                Vitest setup and fixtures
```

Each feature has only the subfolders it uses (`api/`, `components/`, `hooks/`, `schemas/`, `services/`, `store/`, `types/`). Code used by more than one feature goes in `shared/`. Tests sit next to the file they test.

See section 4 and section 13 of [`../docs/architecture.md`](../docs/architecture.md) for the full target layout.

## Departure Time

The departure time is entered in the browser's local time zone and sent with that zone's UTC offset (for example `2026-11-05T08:00:00-07:00`), shown under the field as "Your local time (UTC−07:00)".
