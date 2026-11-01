import axios, { type AxiosInstance } from 'axios'

import { readApiBaseUrl } from '../../app/config'

// A full analysis calls several external providers and usually takes 10-20 seconds; allow
// for slow providers before giving up.
export const ANALYSIS_TIMEOUT_MS = 90_000

let client: AxiosInstance | null = null

/** The shared Axios client for the Django backend (created on first use). */
export function getApiClient(): AxiosInstance {
  client ??= axios.create({
    baseURL: readApiBaseUrl(),
    timeout: ANALYSIS_TIMEOUT_MS,
    // Report timeouts as ETIMEDOUT, so they are not confused with aborted requests (ECONNABORTED).
    transitional: { clarifyTimeoutError: true },
    headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
  })
  return client
}
