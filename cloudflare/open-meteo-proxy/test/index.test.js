import assert from 'node:assert/strict'
import { afterEach, beforeEach, describe, it } from 'node:test'

import worker from '../src/index.js'

const TOKEN = 'test-proxy-token-0123456789abcdef'
const ENV = { PROXY_TOKEN: TOKEN }
const ORIGIN = 'https://open-meteo-proxy.example.workers.dev'

// The query exactly as the backend builds it (backend/modules/weather/services/open_meteo.py).
const BACKEND_QUERY = {
  latitude: '39.73920,40.76080',
  longitude: '-104.99030,-111.89100',
  hourly: 'wind_speed_10m,precipitation,snowfall',
  timezone: 'GMT',
  timeformat: 'unixtime',
  start_hour: '2026-11-05T08:00',
  end_hour: '2026-11-07T08:00',
}

/** A request to the Worker; `query` entries replace or remove (undefined) backend values.
 * `token: undefined` sends no token at all; leaving `token` out sends the right one. */
function request(options = {}) {
  const { query = {}, method = 'GET', path = '/v1/forecast', headers = {}, search } = options
  const token = 'token' in options ? options.token : TOKEN
  const params = new URLSearchParams()
  for (const [name, value] of Object.entries({ ...BACKEND_QUERY, ...query })) {
    if (value !== undefined) params.append(name, value)
  }
  const allHeaders = { ...headers }
  if (token !== undefined) allHeaders['X-Proxy-Token'] = token
  return new Request(`${ORIGIN}${path}?${search ?? params}`, { method, headers: allHeaders })
}

/** Replaces the global fetch for one test and records what the Worker sends upstream. */
let upstreamCalls
let upstreamResponse
const realFetch = globalThis.fetch

beforeEach(() => {
  upstreamCalls = []
  upstreamResponse = () =>
    new Response(JSON.stringify([{ hourly: {} }]), {
      status: 200,
      headers: { 'Content-Type': 'application/json' },
    })
  globalThis.fetch = async (input, init) => {
    upstreamCalls.push({ url: String(input), init })
    return upstreamResponse()
  }
})

afterEach(() => {
  globalThis.fetch = realFetch
})

async function send(req, env = ENV) {
  const response = await worker.fetch(req, env)
  return { response, body: await response.text() }
}

describe('authentication', () => {
  it('accepts the backend request with the right token and forwards it', async () => {
    const { response } = await send(request())

    assert.equal(response.status, 200)
    assert.equal(upstreamCalls.length, 1)
  })

  for (const [name, token] of [
    ['a missing token', undefined],
    ['an empty token', ''],
    ['a wrong token', 'wrong-token'],
    ['the right token with extra characters', `${TOKEN}x`],
  ]) {
    it(`rejects ${name} with 401 and sends nothing upstream`, async () => {
      const { response, body } = await send(request({ token }))

      assert.equal(response.status, 401)
      assert.deepEqual(JSON.parse(body), { error: true, reason: 'Unauthorized.' })
      assert.equal(upstreamCalls.length, 0)
    })
  }

  it('fails safely when the PROXY_TOKEN secret is missing', async () => {
    for (const env of [{}, { PROXY_TOKEN: '' }]) {
      const { response, body } = await send(request(), env)

      assert.equal(response.status, 500)
      assert.equal(JSON.parse(body).reason, 'The proxy is not configured.')
    }
    assert.equal(upstreamCalls.length, 0)
  })

  it('checks the token before revealing anything about routes or methods', async () => {
    const { response } = await send(request({ token: 'wrong', method: 'POST', path: '/admin' }))

    assert.equal(response.status, 401)
  })
})

describe('method and path', () => {
  for (const path of ['/', '/v1/forecast/', '/v1/archive', '/v1/forecast/../admin', '/V1/FORECAST']) {
    it(`rejects ${path} with 404`, async () => {
      const { response } = await send(request({ path }))

      assert.equal(response.status, 404)
      assert.equal(upstreamCalls.length, 0)
    })
  }

  for (const method of ['POST', 'PUT', 'DELETE', 'PATCH', 'HEAD', 'OPTIONS']) {
    it(`rejects ${method} with 405`, async () => {
      const { response } = await send(request({ method }))

      assert.equal(response.status, 405)
      assert.equal(response.headers.get('Allow'), 'GET')
      assert.equal(upstreamCalls.length, 0)
    })
  }
})

describe('query validation', () => {
  const rejected = [
    ['an unknown parameter', { query: { apikey: 'x' } }],
    ['an upstream URL parameter', { query: { url: 'https://evil.example' } }],
    ['a duplicate parameter', { search: `${new URLSearchParams(BACKEND_QUERY)}&latitude=1` }],
    ['a missing latitude', { query: { latitude: undefined } }],
    ['a missing end_hour', { query: { end_hour: undefined } }],
    ['other hourly variables', { query: { hourly: 'temperature_2m' } }],
    ['reordered hourly variables', { query: { hourly: 'snowfall,precipitation,wind_speed_10m' } }],
    ['another timezone', { query: { timezone: 'auto' } }],
    ['another time format', { query: { timeformat: 'iso8601' } }],
    ['a malformed start_hour', { query: { start_hour: '2026-11-05 08:00' } }],
    ['an impossible date', { query: { start_hour: '2026-02-30T08:00' } }],
    ['start_hour after end_hour', { query: { start_hour: '2026-11-08T08:00' } }],
    ['an empty query', { search: '' }],
  ]
  for (const [name, options] of rejected) {
    it(`rejects ${name} with 400`, async () => {
      const { response, body } = await send(request(options))

      assert.equal(response.status, 400)
      assert.equal(JSON.parse(body).error, true)
      assert.equal(upstreamCalls.length, 0)
    })
  }
})

describe('coordinates', () => {
  const list = (value, count) => Array(count).fill(value).join(',')

  for (const [name, query] of [
    ['a latitude above 90', { latitude: '90.00001,40.76080' }],
    ['a latitude below -90', { latitude: '-91,40.76080' }],
    ['a longitude above 180', { longitude: '180.5,-111.89100' }],
    ['a non-numeric value', { latitude: 'abc,40.76080' }],
    ['scientific notation', { latitude: '1e1,40.76080' }],
    ['NaN', { latitude: 'NaN,40.76080' }],
    ['Infinity', { longitude: 'Infinity,-111.89100' }],
    ['an empty item', { latitude: '39.73920,' }],
    ['spaces', { latitude: '39.73920, 40.76080' }],
    ['unequal counts', { latitude: '39.73920' }],
    ['101 locations', { latitude: list('39.73920', 101), longitude: list('-104.99030', 101) }],
  ]) {
    it(`rejects ${name}`, async () => {
      const { response } = await send(request({ query }))

      assert.equal(response.status, 400)
      assert.equal(upstreamCalls.length, 0)
    })
  }

  it('accepts exactly 100 locations, and the range limits themselves', async () => {
    const { response } = await send(
      request({ query: { latitude: list('-90.00000', 100), longitude: list('180.00000', 100) } }),
    )

    assert.equal(response.status, 200)
  })

  it('accepts a single location', async () => {
    const { response } = await send(request({ query: { latitude: '39.73920', longitude: '-104.99030' } }))

    assert.equal(response.status, 200)
  })
})

describe('forwarding upstream', () => {
  it('sends only the validated query, to the fixed Open-Meteo URL', async () => {
    await send(request())

    const [{ url, init }] = upstreamCalls
    const sent = new URL(url)
    assert.equal(`${sent.origin}${sent.pathname}`, 'https://api.open-meteo.com/v1/forecast')
    assert.deepEqual(Object.fromEntries(sent.searchParams), BACKEND_QUERY)
    assert.deepEqual([...sent.searchParams.keys()], Object.keys(BACKEND_QUERY))
    assert.equal(init.method, 'GET')
    assert.equal(init.redirect, 'manual')
  })

  it('forwards none of the incoming headers, and never the token', async () => {
    await send(
      request({
        headers: { Authorization: 'Bearer secret', Cookie: 'session=1', 'X-Forwarded-For': '1.2.3.4' },
      }),
    )

    const headers = new Headers(upstreamCalls[0].init.headers)
    assert.deepEqual([...headers.keys()].sort(), ['accept', 'user-agent'])
    assert.ok(!JSON.stringify([...headers]).includes(TOKEN))
    assert.ok(!upstreamCalls[0].url.includes(TOKEN))
  })
})

describe('upstream responses', () => {
  it('returns the upstream status and body unchanged', async () => {
    const payload = JSON.stringify({ error: true, reason: 'Daily API request limit exceeded.' })
    upstreamResponse = () =>
      new Response(payload, {
        status: 429,
        headers: { 'Content-Type': 'application/json', 'Retry-After': '3600', 'Set-Cookie': 'a=b' },
      })

    const { response, body } = await send(request())

    assert.equal(response.status, 429)
    assert.equal(body, payload)
    assert.equal(response.headers.get('Content-Type'), 'application/json')
    assert.equal(response.headers.get('Retry-After'), '3600')
    // Only safe headers are passed back.
    assert.equal(response.headers.get('Set-Cookie'), null)
  })

  it('reports an unreachable upstream as 502', async () => {
    globalThis.fetch = async () => {
      throw new TypeError('fetch failed')
    }

    const { response, body } = await send(request())

    assert.equal(response.status, 502)
    assert.equal(JSON.parse(body).reason, 'Open-Meteo could not be reached.')
  })

  it('reports an upstream timeout as 504', async () => {
    globalThis.fetch = async () => {
      throw new DOMException('The operation timed out.', 'TimeoutError')
    }

    const { response } = await send(request())

    assert.equal(response.status, 504)
  })

  it('adds no CORS headers and never returns the token, on success or error', async () => {
    for (const req of [request(), request({ token: 'wrong' }), request({ query: { hourly: 'x' } })]) {
      const { response, body } = await send(req)

      assert.equal(response.headers.get('Access-Control-Allow-Origin'), null)
      assert.ok(!body.includes(TOKEN))
      assert.ok(![...response.headers].some(([, value]) => value.includes(TOKEN)))
    }
  })
})
