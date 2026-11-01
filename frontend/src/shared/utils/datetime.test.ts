import { describe, expect, it } from 'vitest'

import {
  isSkippedLocalTime,
  nextWholeHour,
  parseLocalInputValue,
  toLocalInputValue,
  toOffsetIsoString,
  utcOffset,
} from './datetime'

// Tests run in America/Denver (see vite.config.ts): MDT (-06:00) until 2026-11-01 02:00,
// then MST (-07:00).

describe('local input values', () => {
  it('formats a date as a datetime-local value', () => {
    expect(toLocalInputValue(new Date(2026, 10, 5, 8, 7))).toBe('2026-11-05T08:07')
  })

  it('parses a datetime-local value as local time', () => {
    expect(parseLocalInputValue('2026-11-05T08:00')).toEqual(new Date(2026, 10, 5, 8, 0))
  })

  it.each(['', '2026-11-05', '2026-11-05 08:00', '2026-02-30T08:00', '2026-11-05T25:00', 'soon'])(
    'rejects %j',
    (value) => {
      expect(parseLocalInputValue(value)).toBeNull()
    },
  )
})

describe('skipped local times', () => {
  it('detects a time skipped when daylight saving time starts', () => {
    // Clocks in America/Denver jump from 02:00 to 03:00 on 2027-03-14.
    expect(parseLocalInputValue('2027-03-14T02:30')).toBeNull()
    expect(isSkippedLocalTime('2027-03-14T02:30')).toBe(true)
  })

  it.each(['2027-03-14T03:30', '2027-03-14T01:30', '2026-02-30T08:00', '2026-11-05T25:00', 'soon'])(
    'is false for %j (a valid time, or not a real date and time)',
    (value) => {
      expect(isSkippedLocalTime(value)).toBe(false)
    },
  )
})

describe('UTC offsets', () => {
  it('uses the offset in effect on the date itself, across daylight saving', () => {
    expect(utcOffset(new Date(2026, 9, 31, 20, 0))).toBe('-06:00') // MDT
    expect(utcOffset(new Date(2026, 10, 2, 8, 0))).toBe('-07:00') // MST
  })

  it('builds the ISO-8601 string the backend expects', () => {
    expect(toOffsetIsoString(new Date(2026, 10, 5, 8, 0))).toBe('2026-11-05T08:00:00-07:00')
    expect(toOffsetIsoString(new Date(2026, 6, 4, 23, 30))).toBe('2026-07-04T23:30:00-06:00')
  })

  it('round-trips to the same instant', () => {
    const local = new Date(2026, 10, 5, 8, 0)

    expect(new Date(toOffsetIsoString(local)).getTime()).toBe(local.getTime())
  })
})

describe('nextWholeHour', () => {
  it('returns the start of the following hour', () => {
    expect(nextWholeHour(new Date(2026, 10, 5, 8, 20, 30))).toEqual(new Date(2026, 10, 5, 9, 0))
    expect(nextWholeHour(new Date(2026, 10, 5, 23, 59))).toEqual(new Date(2026, 10, 6, 0, 0))
  })
})
