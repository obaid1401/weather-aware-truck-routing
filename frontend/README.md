# Weather-Aware Truck Routing — Frontend

React + TypeScript client for the Weather-Aware Truck Routing application. It collects trip details, sends them to the backend analysis API, and displays the routes, checkpoints, risks, and recommendation on an interactive map.

The frontend only displays data from the backend. It never calls OpenRouteService or Open-Meteo directly and never calculates risk.

## Status

This folder currently contains the Vite starter template. The application UI is built in Phase 8 (Frontend Foundation) and Phase 9 (Results and Visualization). See [`../docs/CLAUDE.md`](../docs/CLAUDE.md).

## Stack

- React, TypeScript, Vite
- Material UI
- React Leaflet and Leaflet with OpenStreetMap tiles
- TanStack Query for the analysis request
- Axios as the HTTP client
- Vitest and React Testing Library for tests (added in Phase 8)

## Getting Started

Requires Node.js 24 and npm.

```bash
npm install
npm run dev
```

The development server runs at `http://localhost:5173/`.

## Scripts

| Command | Description |
|---|---|
| `npm run dev` | Start the development server |
| `npm run build` | Type-check and build for production into `dist/` |
| `npm run preview` | Serve the production build locally |
| `npm run lint` | Run ESLint |

## Environment Variables

Frontend variables (such as the backend API URL) will be listed in `.env.example` during Phase 8. Never put API keys or other secrets in frontend code or `.env` files: anything prefixed `VITE_` is bundled into the public build.

## Structure

The frontend is organized by feature. See section 4 and section 13 of [`../docs/architecture.md`](../docs/architecture.md) for the target layout.
