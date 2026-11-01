import { useMutation } from '@tanstack/react-query'

import { analyzeTrip } from '../api/analyzeTrip'
import { toApiProblem, type ApiProblem } from '../services/apiProblem'
import type { TripAnalysisRequest, TripAnalysisResponse } from '../types/api'

/** Submits a trip for analysis. Failures arrive as an ApiProblem. Never retried
 * automatically: each attempt uses external provider quotas. */
export function useAnalyzeTrip() {
  return useMutation<TripAnalysisResponse, ApiProblem, TripAnalysisRequest>({
    mutationFn: async (request) => {
      try {
        return await analyzeTrip(request)
      } catch (error) {
        throw toApiProblem(error)
      }
    },
    retry: false,
  })
}
