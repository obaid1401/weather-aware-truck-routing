import type { TripAnalysisResponse } from '../types/api'

/** The analysis response is missing fields the UI reads, or they have the wrong type. */
export class InvalidAnalysisResponseError extends Error {
  constructor(invalidFields: string[]) {
    super(`Invalid analysis response: ${invalidFields.join(', ')}`)
    this.name = 'InvalidAnalysisResponseError'
  }
}

export const isRecord = (value: unknown): value is Record<string, unknown> =>
  typeof value === 'object' && value !== null && !Array.isArray(value)

const isString = (value: unknown): value is string => typeof value === 'string'
const isNumber = (value: unknown): value is number =>
  typeof value === 'number' && Number.isFinite(value)
const isTimestamp = (value: unknown): value is string =>
  isString(value) && !Number.isNaN(Date.parse(value))
const isStringList = (value: unknown): value is string[] =>
  Array.isArray(value) && value.every(isString)

const isNumberOrNull = (value: unknown) => value === null || isNumber(value)
const isTimestampOrNull = (value: unknown) => value === null || isTimestamp(value)
const oneOf =
  (...allowed: string[]) =>
  (value: unknown) =>
    isString(value) && allowed.includes(value)

const isRisk = oneOf('LOW', 'MODERATE', 'HIGH', 'SEVERE', 'NO_TRAVEL', 'UNKNOWN')
const isDataStatus = oneOf('AVAILABLE', 'PARTIAL', 'UNAVAILABLE')

const isLocation = (value: unknown) =>
  isRecord(value) && isString(value.label) && isNumber(value.latitude) && isNumber(value.longitude)

const isTrip = (value: unknown) =>
  isRecord(value) && isTimestamp(value.departure_time) && isNumber(value.checkpoint_interval_miles)

/** A forecast with its factor risks: the shape shared by checkpoints and hourly entries. */
const isForecast = (value: Record<string, unknown>) =>
  isTimestampOrNull(value.forecast_timestamp) &&
  isNumberOrNull(value.wind_speed_mph) &&
  isNumberOrNull(value.precipitation_inches_per_hour) &&
  isNumberOrNull(value.snowfall_inches_per_hour) &&
  isDataStatus(value.data_status) &&
  isRisk(value.wind_risk) &&
  isRisk(value.rain_risk) &&
  isRisk(value.snow_risk) &&
  isRisk(value.final_risk)

const isHourlyForecast = (value: unknown) =>
  isRecord(value) && isNumber(value.hour_offset) && isTimestamp(value.target_time) && isForecast(value)

const isCheckpoint = (value: unknown) =>
  isRecord(value) &&
  isString(value.id) &&
  isNumber(value.distance_from_origin_miles) &&
  isNumber(value.latitude) &&
  isNumber(value.longitude) &&
  isTimestamp(value.estimated_arrival_time) &&
  isForecast(value) &&
  isStringList(value.warnings) &&
  Array.isArray(value.hourly_forecasts) &&
  value.hourly_forecasts.every(isHourlyForecast)

const isLatLng = (value: unknown) =>
  Array.isArray(value) && value.length === 2 && isNumber(value[0]) && isNumber(value[1])

const isMetrics = (value: unknown) =>
  isRecord(value) &&
  isNumber(value.severe_miles) &&
  isNumber(value.high_miles) &&
  isNumber(value.no_travel_miles) &&
  isNumber(value.unknown_miles) &&
  isNumberOrNull(value.average_risk_score) &&
  isNumber(value.weather_coverage_percent)

const isRoute = (value: unknown) =>
  isRecord(value) &&
  isString(value.id) &&
  isString(value.label) &&
  isNumber(value.distance_miles) &&
  isNumber(value.duration_seconds) &&
  isTimestamp(value.estimated_arrival_time) &&
  Array.isArray(value.geometry) &&
  value.geometry.every(isLatLng) &&
  isMetrics(value.metrics) &&
  Array.isArray(value.checkpoints) &&
  value.checkpoints.every(isCheckpoint)

const isRecommendation = (value: unknown) =>
  value === null ||
  (isRecord(value) &&
    isString(value.recommended_route_id) &&
    isStringList(value.ranking_reasons) &&
    isStringList(value.warnings))

/** Checks, at runtime, the response fields the UI displays (summary, route comparison, map,
 * checkpoint details, and forecast slider), so a malformed response, or a risk level the UI
 * does not know, becomes a clear error instead of a crash or a wrong colour. The full shape is
 * described by TripAnalysisResponse. */
export function parseAnalysisResponse(data: unknown): TripAnalysisResponse {
  if (!isRecord(data)) throw new InvalidAnalysisResponseError(['body'])
  const checks: Record<string, boolean> = {
    trip: isTrip(data.trip),
    origin: isLocation(data.origin),
    destination: isLocation(data.destination),
    routes: Array.isArray(data.routes) && data.routes.every(isRoute),
    recommendation: isRecommendation(data.recommendation),
    provider_warnings: isStringList(data.provider_warnings),
  }
  const invalid = Object.keys(checks).filter((field) => !checks[field])
  if (invalid.length) throw new InvalidAnalysisResponseError(invalid)
  return data as unknown as TripAnalysisResponse
}
