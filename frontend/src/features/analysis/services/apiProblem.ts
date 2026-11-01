import axios from 'axios'

import type { AmbiguityCandidate, ApiErrorBody } from '../types/api'
import { InvalidAnalysisResponseError, isRecord } from './analysisResponse'

/** Request fields the backend can report validation errors for. */
export const TRIP_FIELDS = [
  'origin',
  'destination',
  'departure_time',
  'load_weight_lbs',
  'checkpoint_interval_miles',
] as const
export type TripField = (typeof TRIP_FIELDS)[number]

/** Any failure of an analysis request, normalised for display. */
export interface ApiProblem {
  /** The backend error code, or NETWORK_ERROR / CLIENT_TIMEOUT / REQUEST_ABORTED /
   * INVALID_RESPONSE / UNEXPECTED_ERROR. */
  code: string
  title: string
  message: string
  status: number | null
  fieldErrors: Partial<Record<TripField, string>>
  ambiguity: { field: 'origin' | 'destination'; candidates: AmbiguityCandidate[] } | null
  retryAfterSeconds: number | null
}

const TITLES: Record<string, string> = {
  VALIDATION_ERROR: 'Please check the highlighted fields',
  GEOCODING_AMBIGUOUS: 'Which location did you mean?',
  GEOCODING_NOT_FOUND: 'Address not found',
  ROUTE_NOT_FOUND: 'No truck route found',
  ROUTE_DISTANCE_LIMIT: 'Trip too long for the routing service',
  RATE_LIMITED: 'Too many requests',
  PROVIDER_RATE_LIMITED: 'A data provider is busy',
  PROVIDER_UNAVAILABLE: 'A data provider is unavailable',
  PROVIDER_TIMEOUT: 'A data provider did not respond',
  PROVIDER_ERROR: 'A data provider returned an error',
  NETWORK_ERROR: 'Cannot reach the server',
  CLIENT_TIMEOUT: 'The analysis took too long',
  REQUEST_ABORTED: 'The request was interrupted',
  INVALID_RESPONSE: 'Unexpected response from the server',
}

function problem(fields: Partial<ApiProblem> & { code: string; message: string }): ApiProblem {
  return {
    title: TITLES[fields.code] ?? 'Something went wrong',
    status: null,
    fieldErrors: {},
    ambiguity: null,
    retryAfterSeconds: null,
    ...fields,
  }
}

function isErrorBody(value: unknown): value is ApiErrorBody {
  return (
    isRecord(value) &&
    isRecord(value.error) &&
    typeof value.error.code === 'string' &&
    typeof value.error.message === 'string'
  )
}

const isTripField = (key: string): key is TripField =>
  (TRIP_FIELDS as readonly string[]).includes(key)

/** DRF validation details: {"field": ["message", ...]} -> {field: "message"}. */
function fieldErrorsFrom(details: unknown): Partial<Record<TripField, string>> {
  const errors: Partial<Record<TripField, string>> = {}
  if (!isRecord(details)) return errors
  for (const [key, value] of Object.entries(details)) {
    const first = Array.isArray(value) ? value.find((m) => typeof m === 'string') : value
    if (isTripField(key) && typeof first === 'string') errors[key] = first
  }
  return errors
}

function ambiguityFrom(details: unknown): ApiProblem['ambiguity'] {
  if (!isRecord(details) || !Array.isArray(details.candidates)) return null
  const field = details.field
  if (field !== 'origin' && field !== 'destination') return null
  const candidates = details.candidates.filter(
    (c): c is AmbiguityCandidate =>
      isRecord(c) &&
      typeof c.label === 'string' &&
      typeof c.latitude === 'number' &&
      typeof c.longitude === 'number',
  )
  return candidates.length ? { field, candidates } : null
}

function retryAfterFrom(details: unknown, header: unknown): number | null {
  const fromDetails = isRecord(details) ? details.retry_after_seconds : undefined
  const value = typeof fromDetails === 'number' ? fromDetails : Number(header)
  return Number.isFinite(value) && value > 0 ? Math.ceil(value) : null
}

/** Converts any error thrown by an analysis request into an ApiProblem. */
export function toApiProblem(error: unknown): ApiProblem {
  if (error instanceof InvalidAnalysisResponseError) {
    return problem({
      code: 'INVALID_RESPONSE',
      message:
        'The analysis response was incomplete or malformed, so it cannot be shown. Please try again.',
    })
  }
  if (!axios.isAxiosError(error)) {
    return problem({ code: 'UNEXPECTED_ERROR', message: 'An unexpected error occurred.' })
  }
  // The API client reports timeouts as ETIMEDOUT (clarifyTimeoutError), so ECONNABORTED is
  // only a request the browser aborted.
  if (error.code === 'ETIMEDOUT') {
    return problem({
      code: 'CLIENT_TIMEOUT',
      message: 'The server did not finish the analysis in time. Please try again.',
    })
  }
  if (error.code === 'ECONNABORTED' || axios.isCancel(error)) {
    return problem({
      code: 'REQUEST_ABORTED',
      message: 'The request was stopped before the analysis finished. Please try again.',
    })
  }
  const response = error.response
  if (!response) {
    return problem({
      code: 'NETWORK_ERROR',
      message: 'Could not connect to the analysis service. Check that the backend is running.',
    })
  }
  if (!isErrorBody(response.data)) {
    return problem({
      code: 'UNEXPECTED_ERROR',
      status: response.status,
      message: `The server returned an unexpected response (HTTP ${response.status}).`,
    })
  }

  const { code, message, details } = response.data.error
  return problem({
    code,
    message,
    status: response.status,
    fieldErrors: code === 'VALIDATION_ERROR' ? fieldErrorsFrom(details) : {},
    ambiguity: code === 'GEOCODING_AMBIGUOUS' ? ambiguityFrom(details) : null,
    // This API's limit (429) and a provider's limit (503) can both say when to retry.
    retryAfterSeconds:
      code === 'RATE_LIMITED' || code === 'PROVIDER_RATE_LIMITED'
        ? retryAfterFrom(details, response.headers?.['retry-after'])
        : null,
  })
}
