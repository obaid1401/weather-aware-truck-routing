// Types for the backend API. They mirror the DRF serializers in
// backend/api/serializers/{trip,analysis}.py and the error format in backend/api/exceptions.py.
// Timestamps are ISO-8601 strings: UTC ("Z"), except trip.departure_time, which echoes the
// UTC offset that was sent. Missing weather values are null, never 0.

export type RiskLevel = 'LOW' | 'MODERATE' | 'HIGH' | 'SEVERE' | 'NO_TRAVEL' | 'UNKNOWN'

export type DataStatus = 'AVAILABLE' | 'PARTIAL' | 'UNAVAILABLE'

export const CHECKPOINT_INTERVALS_MILES = [10, 25, 50] as const
export type CheckpointIntervalMiles = (typeof CHECKPOINT_INTERVALS_MILES)[number]
export const DEFAULT_CHECKPOINT_INTERVAL_MILES: CheckpointIntervalMiles = 25

// POST /api/v1/routes/analyze/

export interface TripAnalysisRequest {
  origin: string
  destination: string
  /** ISO-8601 with a UTC offset, for example 2026-11-05T08:00:00-07:00. */
  departure_time: string
  load_weight_lbs: number
  checkpoint_interval_miles: CheckpointIntervalMiles
}

interface WeatherFields {
  forecast_timestamp: string | null
  wind_speed_mph: number | null
  precipitation_inches_per_hour: number | null
  snowfall_inches_per_hour: number | null
  data_status: DataStatus
}

interface RiskFields {
  wind_risk: RiskLevel
  rain_risk: RiskLevel
  snow_risk: RiskLevel
  final_risk: RiskLevel
}

export interface HourlyForecast extends WeatherFields, RiskFields {
  hour_offset: number
  target_time: string
}

export interface Checkpoint extends WeatherFields, RiskFields {
  id: string
  route_id: string
  distance_from_origin_miles: number
  latitude: number
  longitude: number
  estimated_arrival_time: string
  warnings: string[]
  hourly_forecasts: HourlyForecast[]
}

export interface RouteMetrics {
  distance_miles: number
  duration_seconds: number
  low_miles: number
  moderate_miles: number
  high_miles: number
  severe_miles: number
  no_travel_miles: number
  unknown_miles: number
  /** null when no mile has a known risk. */
  average_risk_score: number | null
  weather_coverage_percent: number
  complete_weather_coverage_percent: number
}

/** [latitude, longitude] */
export type LatLng = [number, number]

export interface AnalyzedRoute {
  id: string
  label: string
  distance_miles: number
  duration_seconds: number
  estimated_arrival_time: string
  checkpoint_count: number
  geometry: LatLng[]
  metrics: RouteMetrics
  checkpoints: Checkpoint[]
}

export interface GeocodedLocation {
  label: string
  latitude: number
  longitude: number
}

export interface TripEcho {
  origin: string
  destination: string
  departure_time: string
  load_weight_lbs: number
  checkpoint_interval_miles: number
}

export interface ForecastWindow {
  start: string
  end: string
}

export interface Recommendation {
  recommended_route_id: string
  ranked_route_ids: string[]
  /** One explanation per ranked route, in the order of ranked_route_ids. */
  ranking_reasons: string[]
  /** Safety warnings: NO_TRAVEL exposure and incomplete weather data. */
  warnings: string[]
}

export interface TripAnalysisResponse {
  trip: TripEcho
  origin: GeocodedLocation
  destination: GeocodedLocation
  forecast_window: ForecastWindow
  /** In provider order. */
  routes: AnalyzedRoute[]
  recommendation: Recommendation | null
  provider_warnings: string[]
}

// Errors: {"error": {"code", "message", "details"}}

export type ApiErrorCode =
  | 'VALIDATION_ERROR'
  | 'GEOCODING_AMBIGUOUS'
  | 'GEOCODING_NOT_FOUND'
  | 'ROUTE_NOT_FOUND'
  | 'ROUTE_DISTANCE_LIMIT'
  | 'RATE_LIMITED'
  | 'PROVIDER_ERROR'
  | 'PROVIDER_RATE_LIMITED'
  | 'PROVIDER_UNAVAILABLE'
  | 'PROVIDER_TIMEOUT'
  | 'INTERNAL_ERROR'

export interface ApiErrorBody {
  error: {
    code: ApiErrorCode | (string & {})
    message: string
    details: Record<string, unknown>
  }
}

export interface AmbiguityCandidate {
  label: string
  latitude: number
  longitude: number
}
