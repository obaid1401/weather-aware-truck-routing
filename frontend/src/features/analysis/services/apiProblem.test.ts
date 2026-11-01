import { AxiosError, CanceledError } from 'axios'
import { describe, expect, it } from 'vitest'

import { apiError, errorBody } from '../../../shared/test/fixtures'
import { InvalidAnalysisResponseError } from './analysisResponse'
import { toApiProblem } from './apiProblem'

describe('backend errors', () => {
  it('maps validation details to form fields', () => {
    const problem = toApiProblem(
      apiError(
        400,
        errorBody('VALIDATION_ERROR', 'The request is invalid.', {
          departure_time: ['Departure time must not be in the past.'],
          checkpoint_interval_miles: ['"30" is not a valid choice.'],
          unknown_field: ['ignored'],
        }),
      ),
    )

    expect(problem).toMatchObject({
      code: 'VALIDATION_ERROR',
      status: 400,
      title: 'Please check the highlighted fields',
      fieldErrors: {
        departure_time: 'Departure time must not be in the past.',
        checkpoint_interval_miles: '"30" is not a valid choice.',
      },
    })
  })

  it('keeps ambiguous geocoding candidates', () => {
    const problem = toApiProblem(
      apiError(
        422,
        errorBody('GEOCODING_AMBIGUOUS', 'The origin address matches multiple locations.', {
          field: 'origin',
          candidates: [
            { label: 'Springfield, MO, USA', latitude: 37.197, longitude: -93.281 },
            { label: 'bad candidate' },
          ],
        }),
      ),
    )

    expect(problem.ambiguity).toEqual({
      field: 'origin',
      candidates: [{ label: 'Springfield, MO, USA', latitude: 37.197, longitude: -93.281 }],
    })
    expect(problem.message).toBe('The origin address matches multiple locations.')
  })

  it.each([
    ['GEOCODING_NOT_FOUND', 422, 'Address not found'],
    ['ROUTE_NOT_FOUND', 422, 'No truck route found'],
    ['ROUTE_DISTANCE_LIMIT', 422, 'Trip too long for the routing service'],
    ['PROVIDER_ERROR', 502, 'A data provider returned an error'],
    ['PROVIDER_RATE_LIMITED', 503, 'A data provider is busy'],
    ['PROVIDER_UNAVAILABLE', 503, 'A data provider is unavailable'],
    ['PROVIDER_TIMEOUT', 504, 'A data provider did not respond'],
    ['INTERNAL_ERROR', 500, 'Something went wrong'],
    ['SOMETHING_NEW', 418, 'Something went wrong'],
  ])('%s keeps the backend message with a title', (code, status, title) => {
    const problem = toApiProblem(apiError(status, errorBody(code, `Message for ${code}.`)))

    expect(problem).toMatchObject({ code, status, title, message: `Message for ${code}.` })
    expect(problem.fieldErrors).toEqual({})
    expect(problem.ambiguity).toBeNull()
  })

  it('reads the retry delay of this API rate limit', () => {
    const fromDetails = toApiProblem(
      apiError(429, errorBody('RATE_LIMITED', 'Too many.', { retry_after_seconds: 42 })),
    )
    const fromHeader = toApiProblem(
      apiError(429, errorBody('RATE_LIMITED', 'Too many.'), { 'retry-after': '17' }),
    )

    expect(fromDetails.retryAfterSeconds).toBe(42)
    expect(fromHeader.retryAfterSeconds).toBe(17)
  })

  it('reads the retry delay of a provider rate limit when the backend gives one', () => {
    const withDelay = toApiProblem(
      apiError(
        503,
        errorBody('PROVIDER_RATE_LIMITED', 'Limit reached.', {
          provider: 'OpenRouteService',
          retry_after_seconds: 30,
        }),
      ),
    )
    const withoutDelay = toApiProblem(
      apiError(503, errorBody('PROVIDER_RATE_LIMITED', 'Limit reached.', { provider: 'Open-Meteo' })),
    )

    expect(withDelay.retryAfterSeconds).toBe(30)
    expect(withoutDelay.retryAfterSeconds).toBeNull()
  })

  it('never reports a retry delay for other errors', () => {
    const problem = toApiProblem(
      apiError(503, errorBody('PROVIDER_UNAVAILABLE', 'Down.', { retry_after_seconds: 30 })),
    )

    expect(problem.retryAfterSeconds).toBeNull()
  })

  it('treats a response without the error format as unexpected', () => {
    const problem = toApiProblem(apiError(502, '<html>Bad gateway</html>'))

    expect(problem).toMatchObject({
      code: 'UNEXPECTED_ERROR',
      status: 502,
      message: 'The server returned an unexpected response (HTTP 502).',
    })
  })
})

describe('client-side failures', () => {
  it('reports a network failure when there is no response', () => {
    const problem = toApiProblem(new AxiosError('Network Error', 'ERR_NETWORK'))

    expect(problem).toMatchObject({ code: 'NETWORK_ERROR', status: null, title: 'Cannot reach the server' })
  })

  it('reports a client timeout', () => {
    const problem = toApiProblem(new AxiosError('timeout of 90000ms exceeded', 'ETIMEDOUT'))

    expect(problem).toMatchObject({ code: 'CLIENT_TIMEOUT', title: 'The analysis took too long' })
  })

  it('reports an aborted request as interrupted, not as a timeout', () => {
    const aborted = toApiProblem(new AxiosError('Request aborted', 'ECONNABORTED'))
    const canceled = toApiProblem(new CanceledError())

    expect(aborted).toMatchObject({ code: 'REQUEST_ABORTED', title: 'The request was interrupted' })
    expect(canceled.code).toBe('REQUEST_ABORTED')
  })

  it('reports a malformed analysis response', () => {
    const problem = toApiProblem(new InvalidAnalysisResponseError(['routes']))

    expect(problem).toMatchObject({
      code: 'INVALID_RESPONSE',
      status: null,
      title: 'Unexpected response from the server',
    })
  })

  it('handles non-Axios errors', () => {
    expect(toApiProblem(new Error('boom')).code).toBe('UNEXPECTED_ERROR')
  })
})
