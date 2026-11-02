# Deployment Guide

This document explains how to deploy and configure the Weather-Aware Truck Routing application.

The application uses three deployed components:

| Component | Platform | Purpose |
|---|---|---|
| Backend | Render (Docker Web Service) | Django REST API |
| Frontend | Render (Static Site) | React application built with Vite |
| Weather Proxy | Cloudflare Workers | Securely forwards weather requests to Open-Meteo |

The application does not require a database, Redis instance, background worker, or paid infrastructure.

## 1. Prerequisites

Before deploying, make sure you have:

- A GitHub repository containing the project.
- A Render account connected to GitHub.
- A Cloudflare account.
- An OpenRouteService API key.
- Node.js and npm for local frontend development.
- Python and Docker for local backend development.

## 2. Cloudflare Weather Proxy

The backend uses a Cloudflare Worker to forward requests to Open-Meteo. This avoids relying directly on Render's shared outbound IP when accessing the weather provider.

### Worker configuration

The Worker is located at:

`cloudflare/open-meteo-proxy/`

Its responsibilities include:

- Authenticating requests using the `X-Proxy-Token` header.
- Validating incoming coordinates and supported query parameters.
- Forwarding validated requests to the fixed Open-Meteo forecast endpoint.
- Returning the upstream response to the backend.
- Applying request timeouts and handling upstream errors.
- Preventing arbitrary URLs or incoming headers from being forwarded.

### Deploy the Worker

The Worker has no npm dependencies; Wrangler runs through `npx`. From the project root:

```bash
cd cloudflare/open-meteo-proxy
npm test                                   # optional: the Worker's tests
npx wrangler@4.151.1 login
npx wrangler@4.151.1 secret put PROXY_TOKEN
npx wrangler@4.151.1 deploy
```

Set the secret before (or right after) the first deploy: until `PROXY_TOKEN` exists, the Worker answers every request with HTTP 500. Wrangler prompts for the value, so it does not appear in your shell history.

Use a securely generated random token (the Worker README has a PowerShell command for one). The same token must be configured in the Render backend environment.

The deployed Worker URL is:

`https://weather-aware-truck-routing-proxy.bediobaid.workers.dev`

The Worker configuration is maintained in `wrangler.toml`.

## 3. Backend Deployment (Render)

The backend is deployed as a Docker Web Service on Render.

### Service configuration

| Setting | Value |
|---|---|
| Service type | Web Service |
| Runtime | Docker |
| Branch | `main` |
| Root directory | `backend/` |
| Dockerfile path | `./Dockerfile` |
| Health check path | `/api/health/` |

Render builds the backend using the Docker configuration in the `backend/` directory. Render sets `PORT` itself; Gunicorn binds to it (`backend/gunicorn.conf.py`).

### Environment variables

Configure the following environment variables in the Render service dashboard:

| Variable | Required | Description |
|---|---|---|
| `DJANGO_SECRET_KEY` | Yes | Django secret key. Use a securely generated value. |
| `DJANGO_ALLOWED_HOSTS` | Yes | Comma-separated allowed hostnames, including the Render backend hostname. |
| `CORS_ALLOWED_ORIGINS` | Yes | Comma-separated frontend origins allowed to call the API. Without the deployed frontend's origin, the browser blocks every API request. |
| `ORS_API_KEY` | Yes | OpenRouteService API key for geocoding and location suggestions. |
| `ANALYZE_RATE_LIMIT` | Yes | Rate limit for trip analysis requests, such as `10/minute`. |
| `SUGGEST_RATE_LIMIT` | Yes | Rate limit for location suggestion requests, such as `30/minute`. |
| `DJANGO_DEBUG` | No | Leave unset or `False` in deployment (the default). |
| `VALHALLA_BASE_URL` | No | Valhalla routing server. Defaults to the public FOSSGIS server. |
| `OPEN_METEO_BASE_URL` | No | Open-Meteo proxy base URL. Defaults to the direct Open-Meteo API when omitted. |
| `OPEN_METEO_PROXY_TOKEN` | No | Authentication token sent to the Cloudflare Worker. Required when using the proxy. |

For the deployed configuration, set:

```env
DJANGO_ALLOWED_HOSTS=weather-aware-truck-routing-api-reau.onrender.com
CORS_ALLOWED_ORIGINS=https://weather-aware-truck-routing-3po3.onrender.com
OPEN_METEO_BASE_URL=https://weather-aware-truck-routing-proxy.bediobaid.workers.dev
OPEN_METEO_PROXY_TOKEN=<same-token-configured-in-cloudflare>
SUGGEST_RATE_LIMIT=30/minute
```

`CORS_ALLOWED_ORIGINS` must match the frontend's origin exactly: `https://`, no trailing slash.

Set `ANALYZE_RATE_LIMIT` to the desired analysis request limit.

The rate-limit variables are required at startup. The application validates their configuration and fails with a clear error if they are missing or invalid.

Keep all secret values in Render's environment settings. Never commit actual credentials or tokens to Git.

### Verify the backend

After deployment, open:

`https://weather-aware-truck-routing-api-reau.onrender.com/api/health/`

The health endpoint should return a successful response when the service is running.

## 4. Frontend Deployment (Render)

The frontend is deployed as a Render Static Site.

### Service configuration

| Setting | Value |
|---|---|
| Service type | Static Site |
| Branch | `main` |
| Root directory | `frontend/` |
| Build command | `npm install && npm run build` |
| Publish directory | `dist` |

### Environment variable

Configure the following environment variable:

```env
VITE_API_BASE_URL=https://weather-aware-truck-routing-api-reau.onrender.com
```

This tells the frontend which backend API to use.

After deployment, Render builds the Vite application and publishes the generated `dist` directory.

## 5. Deployment Order

For a fresh deployment, use the following order:

1. Deploy the Cloudflare Worker.
2. Configure the `PROXY_TOKEN` secret in Cloudflare.
3. Create the Render backend service and configure its environment variables.
4. Deploy the backend and verify its health endpoint.
5. Create the Render frontend Static Site.
6. Configure `VITE_API_BASE_URL` and deploy the frontend.
7. Open the frontend and test a complete trip analysis.

For subsequent updates, push changes to the configured GitHub branch. Render automatically deploys new commits when automatic deployments are enabled.

If the Worker changes, deploy it separately using Wrangler.

## 6. External Services

The application relies on the following external services:

| Service | Usage |
|---|---|
| OpenRouteService | Address geocoding and location autocomplete |
| Valhalla (FOSSGIS public routing service) | Truck route calculation |
| Open-Meteo | Weather forecasts |
| Cloudflare Workers | Weather API proxy |
| Render | Backend and frontend hosting |

The application uses public routing and weather services. Their availability, rate limits, and response times depend on the respective providers.

## 7. Troubleshooting

### Backend does not start

- Check that all required environment variables are configured.
- Verify that `DJANGO_ALLOWED_HOSTS` includes the deployed backend hostname.
- Check the Render deployment logs for configuration or startup errors.

### Location autocomplete does not work

- Verify that `ORS_API_KEY` is configured correctly.
- Check the backend logs for OpenRouteService errors.
- Confirm that `SUGGEST_RATE_LIMIT` is configured.

### Trip analysis fails with a weather provider error

- Verify that the Cloudflare Worker is deployed and accessible.
- Confirm that `OPEN_METEO_BASE_URL` points to the deployed Worker.
- Ensure `OPEN_METEO_PROXY_TOKEN` matches the Cloudflare `PROXY_TOKEN` secret.
- Check the Render backend logs and Cloudflare Worker logs for upstream errors.

### Frontend cannot reach the backend

- Check that `CORS_ALLOWED_ORIGINS` on the backend contains the frontend's exact origin (`https://…onrender.com`, no trailing slash). A CORS error in the browser console means it does not.
- Verify that `VITE_API_BASE_URL` points to the deployed backend. It is read at build time, so redeploy the frontend after changing it.
- Check that the backend health endpoint responds successfully.
- Inspect the browser console and network requests for API errors.

### Render service is slow to respond

Free-tier Render services may experience cold starts after periods of inactivity. The first request after inactivity can take longer than subsequent requests.

## 8. Security Notes

- Never commit API keys, Django secrets, or proxy tokens.
- Keep the Cloudflare proxy token configured as a Worker secret and a Render environment variable.
- The Worker only forwards validated requests to the configured Open-Meteo endpoint.
- Keep production secrets separate from local development environment files.
- Do not expose private environment variables through frontend configuration. Only variables intended for the browser, such as `VITE_API_BASE_URL`, should use the `VITE_` prefix.

## 9. Deployment URLs

| Component | URL |
|---|---|
| Frontend | `https://weather-aware-truck-routing-3po3.onrender.com` |
| Backend API | `https://weather-aware-truck-routing-api-reau.onrender.com` |
| Backend Health | `https://weather-aware-truck-routing-api-reau.onrender.com/api/health/` |
| Cloudflare Worker | `https://weather-aware-truck-routing-proxy.bediobaid.workers.dev` |