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

const isLocation = (value: unknown) => isRecord(value) && isString(value.label)

const isRoute = (value: unknown) =>
  isRecord(value) &&
  isString(value.id) &&
  isString(value.label) &&
  isNumber(value.distance_miles) &&
  isNumber(value.duration_seconds) &&
  isTimestamp(value.estimated_arrival_time) &&
  isRecord(value.metrics) &&
  isNumber(value.metrics.weather_coverage_percent)

const isRecommendation = (value: unknown) =>
  value === null ||
  (isRecord(value) &&
    isString(value.recommended_route_id) &&
    isStringList(value.ranking_reasons) &&
    isStringList(value.warnings))

/** Checks, at runtime, the response fields the UI displays, so a malformed response becomes a
 * clear error instead of a crash. The full shape is described by TripAnalysisResponse. */
export function parseAnalysisResponse(data: unknown): TripAnalysisResponse {
  if (!isRecord(data)) throw new InvalidAnalysisResponseError(['body'])
  const checks: Record<string, boolean> = {
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
