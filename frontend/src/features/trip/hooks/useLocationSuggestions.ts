import { keepPreviousData, useQuery } from '@tanstack/react-query'

import { suggestLocations } from '../api/suggestLocations'
import { useDebouncedValue } from './useDebouncedValue'

/** Suggestions start from the third character (the backend rejects shorter queries). */
export const MIN_SUGGESTION_QUERY_LENGTH = 3
/** Wait for a pause in typing before asking, to save the shared geocoding quota. */
export const SUGGESTION_DEBOUNCE_MS = 300

/**
 * Place suggestions for what the user has typed, fetched once typing pauses. Results are cached
 * per query, superseded requests are cancelled, and failures are not retried (each request uses
 * the geocoding quota).
 */
export function useLocationSuggestions(text: string, active: boolean) {
  const typed = text.trim()
  const query = useDebouncedValue(typed, SUGGESTION_DEBOUNCE_MS)
  const enabled = active && query.length >= MIN_SUGGESTION_QUERY_LENGTH

  const suggestions = useQuery({
    queryKey: ['location-suggestions', query.toLowerCase()],
    queryFn: ({ signal }) => suggestLocations(query, signal),
    enabled,
    staleTime: 5 * 60_000,
    retry: false,
    // Keep the previous list visible while the next one loads.
    placeholderData: keepPreviousData,
  })

  return {
    places: enabled ? (suggestions.data ?? []) : [],
    // Still typing, or waiting for the provider.
    loading: active && (typed !== query || suggestions.isFetching),
    failed: enabled && suggestions.isError,
  }
}
