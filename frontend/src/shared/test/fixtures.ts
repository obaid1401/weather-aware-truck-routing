import { AxiosError, AxiosHeaders, type AxiosResponse } from 'axios'

import type {
  AnalyzedRoute,
  ApiErrorBody,
  Checkpoint,
  HourlyForecast,
  RiskLevel,
  TripAnalysisResponse,
} from '../../features/analysis/types/api'

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

const DEPARTURE_UTC_MS = Date.parse('2026-11-05T15:00:00Z')

const hoursAfterDeparture = (hour: number) =>
  new Date(DEPARTURE_UTC_MS + hour * 3_600_000).toISOString().replace('.000Z', 'Z')

/** An hourly entry shaped like HourlyForecastSerializer output. UNKNOWN entries have no values,
 * as the backend returns them. */
export function hourly(hour: number, risk: RiskLevel): HourlyForecast {
  const time = hoursAfterDeparture(hour)
  if (risk === 'UNKNOWN') {
    return {
      hour_offset: hour,
      target_time: time,
      forecast_timestamp: null,
      wind_speed_mph: null,
      precipitation_inches_per_hour: null,
      snowfall_inches_per_hour: null,
      data_status: 'UNAVAILABLE',
      wind_risk: 'UNKNOWN',
      rain_risk: 'UNKNOWN',
      snow_risk: 'UNKNOWN',
      final_risk: 'UNKNOWN',
    }
  }
  return {
    hour_offset: hour,
    target_time: time,
    forecast_timestamp: time,
    wind_speed_mph: 12.3,
    precipitation_inches_per_hour: 0.04,
    snowfall_inches_per_hour: 0,
    data_status: 'AVAILABLE',
    wind_risk: risk,
    rain_risk: 'LOW',
    snow_risk: 'LOW',
    final_risk: risk,
  }
}

/** Hourly entries for hours 0 to 48; `riskAt` returns null to leave an hour out. */
function series(riskAt: (hour: number) => RiskLevel | null): HourlyForecast[] {
  const entries: HourlyForecast[] = []
  for (let hour = 0; hour <= 48; hour++) {
    const risk = riskAt(hour)
    if (risk) entries.push(hourly(hour, risk))
  }
  return entries
}

function placedCheckpoint(
  routeId: string,
  n: number,
  miles: number,
  [latitude, longitude]: [number, number],
  risk: RiskLevel,
  hourlyForecasts: HourlyForecast[],
): Checkpoint {
  const base = checkpoint(routeId, n, miles)
  const arrival = hoursAfterDeparture(n * 2)
  const unknown = risk === 'UNKNOWN'
  return {
    ...base,
    latitude,
    longitude,
    estimated_arrival_time: arrival,
    forecast_timestamp: unknown ? null : arrival,
    wind_speed_mph: unknown ? null : 20,
    precipitation_inches_per_hour: unknown ? null : 0.12,
    snowfall_inches_per_hour: unknown ? null : 0,
    data_status: unknown ? 'UNAVAILABLE' : 'AVAILABLE',
    wind_risk: unknown ? 'UNKNOWN' : 'LOW',
    rain_risk: risk,
    snow_risk: unknown ? 'UNKNOWN' : 'LOW',
    final_risk: risk,
    warnings: unknown ? ['Weather data is unavailable for this checkpoint.'] : [],
    hourly_forecasts: hourlyForecasts,
  }
}

function metrics(overrides: Partial<AnalyzedRoute['metrics']>): AnalyzedRoute['metrics'] {
  return {
    distance_miles: 50,
    duration_seconds: 3600,
    low_miles: 25,
    moderate_miles: 25,
    high_miles: 0,
    severe_miles: 0,
    no_travel_miles: 0,
    unknown_miles: 0,
    average_risk_score: 1.5,
    weather_coverage_percent: 100,
    complete_weather_coverage_percent: 100,
    ...overrides,
  }
}

/** Two routes with hourly forecasts. Route A (recommended): its checkpoints are LOW, MODERATE,
 * and UNKNOWN at arrival; at hour 6 the origin is SEVERE, and checkpoint 1 has no entry for
 * hour 48. Route B has no-travel miles. */
export const multiRouteAnalysis: TripAnalysisResponse = {
  ...analysisResponse,
  trip: { ...analysisResponse.trip, checkpoint_interval_miles: 25 },
  routes: [
    {
      id: 'route-1',
      label: 'Route A',
      distance_miles: 50,
      duration_seconds: 3600,
      estimated_arrival_time: '2026-11-05T16:00:00Z',
      checkpoint_count: 3,
      geometry: [
        [39.74, -104.99],
        [39.9, -105.3],
        [40.0, -105.6],
      ],
      metrics: metrics({ unknown_miles: 25, weather_coverage_percent: 50 }),
      checkpoints: [
        placedCheckpoint('route-1', 0, 0, [39.74, -104.99], 'LOW', series((h) => (h === 6 ? 'SEVERE' : 'LOW'))),
        placedCheckpoint('route-1', 1, 25, [39.9, -105.3], 'MODERATE', series((h) => (h === 48 ? null : 'MODERATE'))),
        placedCheckpoint('route-1', 2, 50, [40.0, -105.6], 'UNKNOWN', series(() => 'UNKNOWN')),
      ],
    },
    {
      id: 'route-2',
      label: 'Route B',
      distance_miles: 62,
      duration_seconds: 4500,
      estimated_arrival_time: '2026-11-05T16:15:00Z',
      checkpoint_count: 2,
      geometry: [
        [39.74, -104.99],
        [39.6, -105.4],
        [40.0, -105.6],
      ],
      metrics: metrics({
        distance_miles: 62,
        duration_seconds: 4500,
        severe_miles: 12.5,
        high_miles: 30,
        no_travel_miles: 3,
        average_risk_score: null,
      }),
      checkpoints: [
        placedCheckpoint('route-2', 0, 0, [39.74, -104.99], 'LOW', series(() => 'LOW')),
        placedCheckpoint('route-2', 1, 62, [40.0, -105.6], 'NO_TRAVEL', series(() => 'NO_TRAVEL')),
      ],
    },
  ],
  recommendation: {
    recommended_route_id: 'route-1',
    ranked_route_ids: ['route-1', 'route-2'],
    ranking_reasons: [
      'Route A is recommended: it has the fewest severe-risk miles (0.0 mi vs 12.5 mi).',
      'Route B ranks 2nd: 12.5 mi severe-risk.',
    ],
    warnings: ['NO_TRAVEL conditions: Route B has 3.0 mi of no-travel conditions.'],
  },
}
