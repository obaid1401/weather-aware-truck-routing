import type { TripAnalysisRequest, TripAnalysisResponse } from '../types/api'
import { parseAnalysisResponse } from '../services/analysisResponse'
import { getApiClient } from '../../../shared/api/apiClient'

export const ANALYZE_PATH = '/api/v1/routes/analyze/'

/** Runs a full trip analysis. Rejects with the Axios error, or InvalidAnalysisResponseError for
 * a malformed body (see toApiProblem). */
export async function analyzeTrip(request: TripAnalysisRequest): Promise<TripAnalysisResponse> {
  const response = await getApiClient().post<unknown>(ANALYZE_PATH, request)
  return parseAnalysisResponse(response.data)
}
