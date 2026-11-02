import type { GeocodedLocation } from '../../analysis/types/api'
import { isRecord } from '../../analysis/services/analysisResponse'
import { getApiClient } from '../../../shared/api/apiClient'

export const SUGGESTIONS_PATH = '/api/v1/locations/suggestions/'

// Suggestions are only useful while the user is typing; give up quickly.
const SUGGESTIONS_TIMEOUT_MS = 10_000

/** The suggestions response did not have the expected shape. */
export class InvalidSuggestionsResponseError extends Error {
  constructor() {
    super('Invalid location suggestions response')
    this.name = 'InvalidSuggestionsResponseError'
  }
}

const isLocation = (value: unknown): value is GeocodedLocation =>
  isRecord(value) &&
  typeof value.label === 'string' &&
  typeof value.latitude === 'number' &&
  Number.isFinite(value.latitude) &&
  typeof value.longitude === 'number' &&
  Number.isFinite(value.longitude)

/** Places matching a partly typed address, from the backend's geocoding integration. */
export async function suggestLocations(
  query: string,
  signal?: AbortSignal,
): Promise<GeocodedLocation[]> {
  const response = await getApiClient().get<unknown>(SUGGESTIONS_PATH, {
    params: { q: query },
    signal,
    timeout: SUGGESTIONS_TIMEOUT_MS,
  })
  const data = response.data
  if (!isRecord(data) || !Array.isArray(data.suggestions) || !data.suggestions.every(isLocation)) {
    throw new InvalidSuggestionsResponseError()
  }
  return data.suggestions
}
