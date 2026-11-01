// Open-Meteo proxy for the Weather-Aware Truck Routing backend.
//
// Forwards the backend's hourly-forecast requests to the public Open-Meteo API from Cloudflare's
// network. It is not an open proxy: callers must send the shared secret in X-Proxy-Token, the
// upstream URL is fixed, and only the exact query the backend sends is accepted
// (backend/modules/weather/services/open_meteo.py). Nothing from the caller is forwarded except
// the validated query parameters, and no tokens or request headers are ever logged.

const ROUTE = '/v1/forecast'
const UPSTREAM = 'https://api.open-meteo.com/v1/forecast'
const TOKEN_HEADER = 'X-Proxy-Token'
const USER_AGENT = 'weather-aware-truck-routing-open-meteo-proxy/1.0'

// Slightly shorter than the backend's 15-second read timeout, so the backend gets a clear 504.
const UPSTREAM_TIMEOUT_MS = 14_000

// The query the backend sends, in a fixed order. Every parameter is required.
const PARAMETERS = ['latitude', 'longitude', 'hourly', 'timezone', 'timeformat', 'start_hour', 'end_hour']
const HOURLY = 'wind_speed_10m,precipitation,snowfall'
const TIMEZONE = 'GMT'
const TIME_FORMAT = 'unixtime'
const MAX_LOCATIONS = 100
// Plain decimals such as -104.99030 (the backend sends five decimal places).
const DECIMAL = /^-?\d{1,3}(?:\.\d{1,10})?$/
const HOUR = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}$/

// Upstream response headers passed back to the backend. Everything else is dropped.
const RESPONSE_HEADERS = ['Content-Type', 'Retry-After']

export default {
  /**
   * @param {Request} request
   * @param {{ PROXY_TOKEN?: string }} env
   */
  async fetch(request, env) {
    if (!env.PROXY_TOKEN) {
      return error(500, 'The proxy is not configured.')
    }
    // Authenticate first, so callers without the token learn nothing about the routes.
    if (!(await tokenMatches(request.headers.get(TOKEN_HEADER), env.PROXY_TOKEN))) {
      return error(401, 'Unauthorized.')
    }

    const url = new URL(request.url)
    if (url.pathname !== ROUTE) {
      return error(404, 'Not found.')
    }
    if (request.method !== 'GET') {
      return error(405, 'Only GET is allowed.', { Allow: 'GET' })
    }

    const query = validatedQuery(url.searchParams)
    if (query.error) {
      return error(400, query.error)
    }
    return forward(query.search)
  },
}

/**
 * Compares the caller's token with the secret. Both are hashed first, so the comparison always
 * covers equal-length values and does not reveal the secret's length.
 *
 * @param {string | null} provided
 * @param {string} expected
 */
async function tokenMatches(provided, expected) {
  if (!provided) return false
  const [a, b] = await Promise.all([sha256(provided), sha256(expected)])
  // The Workers runtime provides a constant-time comparison.
  if (typeof crypto.subtle.timingSafeEqual === 'function') {
    return crypto.subtle.timingSafeEqual(a, b)
  }
  // Fallback for runtimes without it (the Node.js tests): compares every byte without stopping
  // early, but JavaScript itself gives no constant-time guarantee.
  const left = new Uint8Array(a)
  const right = new Uint8Array(b)
  let difference = 0
  for (let i = 0; i < left.length; i++) difference |= left[i] ^ right[i]
  return difference === 0
}

/** @param {string} value */
function sha256(value) {
  return crypto.subtle.digest('SHA-256', new TextEncoder().encode(value))
}

/**
 * The query to forward, rebuilt from validated values only, or the reason it was rejected.
 *
 * @param {URLSearchParams} params
 * @returns {{ search: string, error?: undefined } | { error: string }}
 */
function validatedQuery(params) {
  for (const name of new Set(params.keys())) {
    if (!PARAMETERS.includes(name)) {
      return { error: `Unsupported query parameter. Allowed: ${PARAMETERS.join(', ')}.` }
    }
    if (params.getAll(name).length > 1) {
      return { error: 'Each query parameter may appear only once.' }
    }
  }
  const missing = PARAMETERS.filter((name) => !params.has(name))
  if (missing.length) {
    return { error: `Missing query parameters: ${missing.join(', ')}.` }
  }

  const latitudes = coordinates(params.get('latitude'), 90)
  const longitudes = coordinates(params.get('longitude'), 180)
  if (!latitudes || !longitudes) {
    return { error: 'latitude and longitude must be comma-separated decimal coordinates in range.' }
  }
  if (latitudes.length !== longitudes.length) {
    return { error: 'latitude and longitude must list the same number of locations.' }
  }
  if (latitudes.length > MAX_LOCATIONS) {
    return { error: `At most ${MAX_LOCATIONS} locations per request.` }
  }

  if (params.get('hourly') !== HOURLY) {
    return { error: `hourly must be ${HOURLY}.` }
  }
  if (params.get('timezone') !== TIMEZONE) {
    return { error: `timezone must be ${TIMEZONE}.` }
  }
  if (params.get('timeformat') !== TIME_FORMAT) {
    return { error: `timeformat must be ${TIME_FORMAT}.` }
  }

  const start = hour(params.get('start_hour'))
  const end = hour(params.get('end_hour'))
  if (start === null || end === null) {
    return { error: 'start_hour and end_hour must be times such as 2026-11-05T08:00.' }
  }
  if (start > end) {
    return { error: 'start_hour must not be after end_hour.' }
  }

  const search = new URLSearchParams(PARAMETERS.map((name) => [name, params.get(name) ?? '']))
  return { search: search.toString() }
}

/**
 * The numbers in a comma-separated coordinate list, or null if any is malformed or out of range.
 *
 * @param {string | null} value
 * @param {number} limit
 */
function coordinates(value, limit) {
  if (!value) return null
  const numbers = []
  for (const part of value.split(',')) {
    if (!DECIMAL.test(part)) return null
    const number = Number(part)
    if (!Number.isFinite(number) || Math.abs(number) > limit) return null
    numbers.push(number)
  }
  return numbers
}

/**
 * The time in milliseconds for a value such as 2026-11-05T08:00 (UTC), or null if invalid.
 *
 * @param {string | null} value
 */
function hour(value) {
  if (!value || !HOUR.test(value)) return null
  const time = Date.parse(`${value}:00Z`)
  // Reject dates that do not exist, such as 2026-02-30, which Date would roll over.
  if (Number.isNaN(time) || new Date(time).toISOString().slice(0, 16) !== value) return null
  return time
}

/**
 * Sends the validated query to Open-Meteo with fresh headers (nothing from the caller), and
 * returns its status and body with only the safe headers.
 *
 * @param {string} search
 */
async function forward(search) {
  let upstream
  try {
    upstream = await fetch(`${UPSTREAM}?${search}`, {
      method: 'GET',
      headers: { Accept: 'application/json', 'User-Agent': USER_AGENT },
      redirect: 'manual',
      signal: AbortSignal.timeout(UPSTREAM_TIMEOUT_MS),
    })
  } catch (failure) {
    if (failure instanceof Error && failure.name === 'TimeoutError') {
      return error(504, 'Open-Meteo did not respond in time.')
    }
    return error(502, 'Open-Meteo could not be reached.')
  }

  const headers = new Headers({ 'Cache-Control': 'no-store' })
  for (const name of RESPONSE_HEADERS) {
    const value = upstream.headers.get(name)
    if (value !== null) headers.set(name, value)
  }
  return new Response(upstream.body, { status: upstream.status, headers })
}

/**
 * An error in Open-Meteo's own format, so the backend reads it like any provider error.
 *
 * @param {number} status
 * @param {string} reason
 * @param {Record<string, string>} [extraHeaders]
 */
function error(status, reason, extraHeaders = {}) {
  return new Response(JSON.stringify({ error: true, reason }), {
    status,
    headers: {
      'Content-Type': 'application/json',
      'Cache-Control': 'no-store',
      ...extraHeaders,
    },
  })
}
