import { describe, expect, it } from 'vitest'

import { ConfigurationError, readApiBaseUrl } from './config'

const env = (value?: string) => ({ VITE_API_BASE_URL: value }) as unknown as ImportMetaEnv

describe('readApiBaseUrl', () => {
  it('returns the configured URL without a trailing slash', () => {
    expect(readApiBaseUrl(env('http://127.0.0.1:8000/'))).toBe('http://127.0.0.1:8000')
    expect(readApiBaseUrl(env(' https://api.example.com '))).toBe('https://api.example.com')
  })

  it.each([undefined, '', '   '])('fails clearly when the URL is missing (%j)', (value) => {
    expect(() => readApiBaseUrl(env(value))).toThrow(ConfigurationError)
    expect(() => readApiBaseUrl(env(value))).toThrow(
      'VITE_API_BASE_URL is not set. Add it to frontend/.env (see .env.example).',
    )
  })
})
