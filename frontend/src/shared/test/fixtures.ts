import { AxiosError, AxiosHeaders, type AxiosResponse } from 'axios'

import type { ApiErrorBody, Checkpoint, TripAnalysisResponse } from '../../features/analysis/types/api'

/** A checkpoint shaped exactly like the backend's CheckpointSerializer output. */
export function checkpoint(routeId: string, n: number, miles: number): Checkpoint {
  return {
    id: `${routeId}-cp-${n}`,
    route_id: routeId,
    distance_from_origin_miles: miles,
    latitude: 39.741,
    longitude: -104.986,
    estimated_arrival_time: '2026-11-05T15:00:00Z',
    forecast_timestamp: '2026-11-05T15:00:00Z',
    wind_speed_mph: 10,
    precipitation_inches_per_hour: 0,
    snowfall_inches_per_hour: 0,
    data_status: 'AVAILABLE',
    wind_risk: 'LOW',
    rain_risk: 'LOW',
    snow_risk: 'LOW',
    final_risk: 'LOW',
    warnings: [],
    hourly_forecasts: [],
  }
}

/** A response shaped exactly like the backend's TripAnalysisSerializer output. */
export const analysisResponse: TripAnalysisResponse = {
  trip: {
    origin: 'Denver, CO',
    destination: 'Salt Lake City, UT',
    departure_time: '2026-11-05T08:00:00-07:00',
    load_weight_lbs: 36000,
    checkpoint_interval_miles: 25,
  },
  origin: { label: 'Denver, CO, USA', latitude: 39.741, longitude: -104.986 },
  destination: { label: 'Salt Lake City, UT, USA', latitude: 40.773, longitude: -111.934 },
  forecast_window: { start: '2026-11-05T15:00:00Z', end: '2026-11-07T15:00:00Z' },
  routes: [
    {
      id: 'route-1',
      label: 'Route A',
      distance_miles: 536.2,
      duration_seconds: 28580,
      estimated_arrival_time: '2026-11-05T22:56:20Z',
      checkpoint_count: 2,
      geometry: [
        [39.741, -104.986],
        [40.773, -111.934],
      ],
      metrics: {
        distance_miles: 536.2,
        duration_seconds: 28580,
        low_miles: 536.2,
        moderate_miles: 0,
        high_miles: 0,
        severe_miles: 0,
        no_travel_miles: 0,
        unknown_miles: 0,
        average_risk_score: 1,
        weather_coverage_percent: 100,
        complete_weather_coverage_percent: 100,
      },
      checkpoints: [checkpoint('route-1', 0, 0), checkpoint('route-1', 1, 536.2)],
    },
  ],
  recommendation: {
    recommended_route_id: 'route-1',
    ranked_route_ids: ['route-1'],
    ranking_reasons: [
      'Route A is recommended because it is the only route available (0.0 mi severe-risk).',
    ],
    warnings: ['NO_TRAVEL conditions: Route A (the recommended route) has 3.0 mi of no-travel conditions.'],
  },
  provider_warnings: [
    'The routing provider returned 1 of up to 3 requested routes. Only genuine provider routes are shown.',
  ],
}

/** An Axios error carrying a backend error response. */
export function apiError(
  status: number,
  body: ApiErrorBody | unknown,
  headers: Record<string, string> = {},
): AxiosError {
  const config = { headers: new AxiosHeaders() }
  const response = {
    status,
    statusText: '',
    data: body,
    headers,
    config,
  } as AxiosResponse
  return new AxiosError('Request failed', 'ERR_BAD_RESPONSE', config, {}, response)
}

export function errorBody(code: string, message: string, details: Record<string, unknown> = {}) {
  return { error: { code, message, details } }
}
