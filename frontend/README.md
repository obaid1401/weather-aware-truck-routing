# Weather-Aware Truck Routing — Frontend

React + TypeScript client for the Weather-Aware Truck Routing application. It collects trip details, sends them to the backend analysis API, and displays the result.

The frontend only displays data from the backend. It never calls OpenRouteService, Valhalla, or Open-Meteo directly and never calculates risk.

## Status

- **Phase 8 (Frontend Foundation):** done. Trip form with validation, loading and error states, connected to `POST /api/v1/routes/analyze/`, with a summary of the recommendation and all warnings.
- **Phase 9 (Results and Visualization):** done. Route comparison in the backend's ranked order, an interactive map (routes, origin and destination, risk-coloured checkpoints), checkpoint details, a 0–48-hour forecast slider, and a weather heatmap along the selected route. Changing the route, checkpoint, or hour never sends a request.
- **Next:** Phase 10 (Testing and Delivery).

## Stack

- React, TypeScript (strict), Vite
- Material UI
- TanStack Query for the analysis request
- Axios as the HTTP client
- Vitest and React Testing Library for tests
- React Leaflet and Leaflet, with OpenStreetMap tiles

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
│   └── pages/               TripAnalysisPage and AnalysisResults (compose the features and hold
│                            the selected route, checkpoint, and forecast hour), ForecastPanel,
│                            and workspace (the page layout)
├── features/
│   ├── analysis/
│   │   ├── api/             analyzeTrip (POST /api/v1/routes/analyze/)
│   │   ├── hooks/           useAnalyzeTrip (TanStack Query mutation)
│   │   ├── services/        analysisResponse: runtime response checks; apiProblem: error normalization
│   │   └── types/           Request, response, and error types (mirror the backend serializers)
│   ├── trip/
│   │   ├── components/      TripForm, TripSummary
│   │   └── schemas/         tripFormSchema: form values and validation
│   ├── recommendation/
│   │   └── components/      AnalysisSummary (recommendation and warnings)
│   ├── routing/
│   │   ├── components/      RouteComparison (route cards), RouteRiskBar (backend miles by risk)
│   │   └── services/        rankedRoutes: routes in the backend's ranked order
│   ├── checkpoints/
│   │   ├── components/      CheckpointList, CheckpointDetails, RouteStrip (strip map)
│   │   └── services/        checkpointLabel: Origin / Checkpoint n / Destination
│   ├── weather/
│   │   ├── components/      ForecastSlider
│   │   └── services/        hourlyForecast: the backend's entry for a slider hour
│   ├── risk/
│   │   ├── components/      RiskBadge, RiskScale, RiskLegend
│   │   └── services/        riskDisplay: label and colour for each backend risk level
│   └── map/
│       ├── components/      RouteMap (React Leaflet), BaseMap, MapKey
│       └── services/        mapStyles: line, marker, and heatmap circle styles; baseMap: tiles
└── shared/
    ├── api/                 Axios client
    ├── components/          AppShell, ConfigurationErrorScreen
    ├── theme/               Material UI theme, design tokens, and the self-hosted Overpass font
    ├── utils/               Date/time and display formatting, visually hidden text
    └── test/                Vitest setup and fixtures
```

## Layout and Visual Design

- **Map first.** A navy header, then on wide screens a column of white panels on the left and the map filling the rest of the window, in view while the panels scroll. The forecast panel floats over the bottom of the map: the slider hour (time) beside a strip map of the selected route (distance), one tick per checkpoint coloured by the backend's risk for that hour. The panel is at most half the map's height, and the map keeps the routes above it. "How to read the map" opens the full map key as a pop-up. On narrow screens the page stacks: trip, map and forecast panel, then results.
- **Panels.** After an analysis the form folds into a trip summary ("Edit trip" reopens it with the entered values). The verdict panel shows the recommended route, its key figures, safety warnings, and why it was chosen. Below it, two tabs: **Routes** (one card per route in ranked order, each with a bar of the backend's miles by risk level and every metric) and **Checkpoints** (one table comparing a checkpoint's forecast at arrival with the selected hour, and the full list). Choosing a checkpoint on the map or strip opens its details.
- **Type.** Overpass, an open-source typeface derived from Highway Gothic (US road-sign lettering), self-hosted under the SIL Open Font License (`src/shared/theme/fonts/OFL.txt`). Numbers use tabular figures.
- **Colour.** Navy header, white rounded panels on a light blue-grey background, and one interface blue for buttons, focus, selection, and the selected route. Risk colours are used only for risk, and every risk colour has a text label.

Each feature has only the subfolders it uses (`api/`, `components/`, `hooks/`, `schemas/`, `services/`, `store/`, `types/`). Code used by more than one feature goes in `shared/`. Tests sit next to the file they test.

See section 4 and section 13 of [`../docs/architecture.md`](../docs/architecture.md) for the full target layout.

## Departure Time

The departure time is entered in the browser's local time zone and sent with that zone's UTC offset (for example `2026-11-05T08:00:00-07:00`), shown under the field as "Your local time (UTC−07:00)".
