import type { AxiosAdapter, InternalAxiosRequestConfig } from 'axios'
import { describe, expect, it } from 'vitest'

import { analysisResponse } from '../../../shared/test/fixtures'
import type { TripAnalysisRequest } from '../types/api'
import { InvalidAnalysisResponseError } from '../services/analysisResponse'
import { ANALYZE_PATH, analyzeTrip } from './analyzeTrip'
import { ANALYSIS_TIMEOUT_MS, getApiClient } from '../../../shared/api/apiClient'

const request: TripAnalysisRequest = {
  origin: 'Denver, CO',
  destination: 'Salt Lake City, UT',
  departure_time: '2026-11-05T08:00:00-07:00',
  load_weight_lbs: 36000,
  checkpoint_interval_miles: 25,
}

describe('analyzeTrip', () => {
  it('posts the request as JSON to the analysis endpoint and returns the response body', async () => {
    let sent: InternalAxiosRequestConfig | undefined
    getApiClient().defaults.adapter = async (config) => {
      sent = config
      return { data: analysisResponse, status: 200, statusText: 'OK', headers: {}, config }
    }

    const result = await analyzeTrip(request)

    expect(result).toEqual(analysisResponse)
    expect(sent?.method).toBe('post')
    expect(sent?.baseURL).toBe('http://api.test')
    expect(sent?.url).toBe(ANALYZE_PATH)
    expect(ANALYZE_PATH).toBe('/api/v1/routes/analyze/')
    expect(JSON.parse(sent?.data as string)).toEqual(request)
    expect(sent?.timeout).toBe(ANALYSIS_TIMEOUT_MS)
    expect(sent?.transitional?.clarifyTimeoutError).toBe(true)
  })

  it.each([
    ['an HTML page', '<html>Welcome</html>'],
    ['a body without routes', { ...analysisResponse, routes: undefined }],
    ['a body without provider warnings', { ...analysisResponse, provider_warnings: undefined }],
  ])('rejects %s with InvalidAnalysisResponseError', async (_name, data) => {
    const adapter: AxiosAdapter = async (config) => ({
      data,
      status: 200,
      statusText: 'OK',
      headers: {},
      config,
    })
    getApiClient().defaults.adapter = adapter

    await expect(analyzeTrip(request)).rejects.toBeInstanceOf(InvalidAnalysisResponseError)
  })
})
