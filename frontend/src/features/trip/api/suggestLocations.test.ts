import type { AxiosAdapter, InternalAxiosRequestConfig } from 'axios'
import { afterEach, describe, expect, it } from 'vitest'

import { getApiClient } from '../../../shared/api/apiClient'
import { InvalidSuggestionsResponseError, SUGGESTIONS_PATH, suggestLocations } from './suggestLocations'

const DENVER = { label: 'Denver, CO, USA', latitude: 39.741, longitude: -104.986 }
const originalAdapter = getApiClient().defaults.adapter

function respondWith(data: unknown, sent: InternalAxiosRequestConfig[] = []): AxiosAdapter {
  return async (config) => {
    sent.push(config)
    return { data, status: 200, statusText: 'OK', headers: {}, config }
  }
}

afterEach(() => {
  getApiClient().defaults.adapter = originalAdapter
})

describe('suggestLocations', () => {
  it('asks the backend for places matching the typed text', async () => {
    const sent: InternalAxiosRequestConfig[] = []
    getApiClient().defaults.adapter = respondWith({ suggestions: [DENVER] }, sent)
    const controller = new AbortController()

    const places = await suggestLocations('Denv', controller.signal)

    expect(places).toEqual([DENVER])
    expect(SUGGESTIONS_PATH).toBe('/api/v1/locations/suggestions/')
    const [config] = sent
    expect(config.method).toBe('get')
    expect(config.url).toBe(SUGGESTIONS_PATH)
    expect(config.params).toEqual({ q: 'Denv' })
    // Superseded requests can be cancelled.
    expect(config.signal).toBe(controller.signal)
  })

  it('returns an empty list when nothing matches', async () => {
    getApiClient().defaults.adapter = respondWith({ suggestions: [] })

    await expect(suggestLocations('Qzxw')).resolves.toEqual([])
  })

  it.each([
    ['an HTML page', '<html></html>'],
    ['a body without suggestions', {}],
    ['a place without a label', { suggestions: [{ latitude: 1, longitude: 2 }] }],
    ['a place with a text coordinate', { suggestions: [{ ...DENVER, latitude: '39.7' }] }],
  ])('rejects %s', async (_name, data) => {
    getApiClient().defaults.adapter = respondWith(data)

    await expect(suggestLocations('Denv')).rejects.toBeInstanceOf(InvalidSuggestionsResponseError)
  })
})
