import { describe, expect, it } from 'vitest'

import { multiRouteAnalysis } from '../../../shared/test/fixtures'
import { countUnavailableAtHour, forecastAtHour, forecastHourTime } from './hourlyForecast'

const [origin, middle, end] = multiRouteAnalysis.routes[0].checkpoints
const DEPARTURE = multiRouteAnalysis.trip.departure_time

describe('forecastAtHour', () => {
  it("returns the backend's entry for that hour", () => {
    expect(forecastAtHour(origin, 6)).toMatchObject({ hour_offset: 6, final_risk: 'SEVERE' })
    expect(forecastAtHour(origin, 7)).toMatchObject({ hour_offset: 7, final_risk: 'LOW' })
  })

  it('returns null for a missing hour instead of using a neighbouring hour', () => {
    expect(forecastAtHour(middle, 48)).toBeNull()
    expect(forecastAtHour(middle, 47)).not.toBeNull()
  })
})

describe('forecastHourTime', () => {
  it("uses the backend's target time", () => {
    expect(forecastHourTime([origin], DEPARTURE, 6)).toBe('2026-11-05T21:00:00Z')
  })

  it('falls back to departure plus the hour when no checkpoint has the entry', () => {
    expect(forecastHourTime([middle], DEPARTURE, 48)).toBe('2026-11-07T15:00:00.000Z')
  })
})

describe('countUnavailableAtHour', () => {
  it('counts UNKNOWN and missing entries, never known risks', () => {
    expect(countUnavailableAtHour([origin, middle, end], 0)).toBe(1)
    expect(countUnavailableAtHour([origin, middle, end], 48)).toBe(2)
  })
})
