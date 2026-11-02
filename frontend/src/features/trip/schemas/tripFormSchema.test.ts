import { describe, expect, it } from 'vitest'

import type { CheckpointIntervalMiles } from '../../analysis/types/api'
import {
  initialTripFormValues,
  parseLoadWeight,
  validateTripForm,
  type TripFormValues,
} from './tripFormSchema'

const NOW = new Date(2026, 10, 3, 10, 15) // 2026-11-03 10:15 in America/Denver (MST)

function values(changes: Partial<TripFormValues> = {}): TripFormValues {
  return {
    origin: 'Denver, CO',
    destination: 'Salt Lake City, UT',
    originPlace: null,
    destinationPlace: null,
    departureLocal: '2026-11-05T08:00',
    loadWeightLbs: '36000',
    checkpointIntervalMiles: 25,
    ...changes,
  }
}

describe('initial values', () => {
  it('default to a 25-mile interval and the next whole hour', () => {
    expect(initialTripFormValues(NOW)).toEqual({
      origin: '',
      destination: '',
      originPlace: null,
      destinationPlace: null,
      departureLocal: '2026-11-03T11:00',
      loadWeightLbs: '',
      checkpointIntervalMiles: 25,
    })
  })
})

describe('valid trips', () => {
  it('build the exact API request', () => {
    const { errors, request } = validateTripForm(
      values({ origin: '  Denver, CO ', loadWeightLbs: '36,000.5' }),
      NOW,
    )

    expect(errors).toEqual({})
    expect(request).toEqual({
      origin: 'Denver, CO',
      destination: 'Salt Lake City, UT',
      departure_time: '2026-11-05T08:00:00-07:00',
      load_weight_lbs: 36000.5,
      checkpoint_interval_miles: 25,
    })
  })

  it('accept the same origin and destination text, as the backend does', () => {
    const { errors, request } = validateTripForm(
      values({ origin: 'Denver, CO', destination: ' denver, co ' }),
      NOW,
    )

    expect(errors).toEqual({})
    expect(request).toMatchObject({ origin: 'Denver, CO', destination: 'denver, co' })
  })

  it.each([10, 25, 50] as CheckpointIntervalMiles[])('accept a %i-mile interval', (miles) => {
    expect(validateTripForm(values({ checkpointIntervalMiles: miles }), NOW).request).toMatchObject({
      checkpoint_interval_miles: miles,
    })
  })
})

describe('invalid trips', () => {
  it.each([
    [{ origin: '' }, 'origin', 'Enter the origin.'],
    [{ origin: '   ' }, 'origin', 'Enter the origin.'],
    [{ destination: '' }, 'destination', 'Enter the destination.'],
    [{ origin: 'x'.repeat(201) }, 'origin', 'Use at most 200 characters.'],
    [{ departureLocal: '' }, 'departure_time', 'Choose a departure date and time.'],
    [{ departureLocal: '2026-02-30T08:00' }, 'departure_time', 'Enter a valid date and time.'],
    [
      { departureLocal: '2027-03-14T02:30' },
      'departure_time',
      'This time does not exist in your time zone because clocks move forward for daylight ' +
        'saving time. Choose another time.',
    ],
    [{ departureLocal: '2026-11-03T10:15' }, 'departure_time', 'Choose a departure time in the future.'],
    [{ departureLocal: '2026-11-01T08:00' }, 'departure_time', 'Choose a departure time in the future.'],
    [{ loadWeightLbs: '' }, 'load_weight_lbs', 'Enter the cargo weight in pounds.'],
    [
      { loadWeightLbs: '-5' },
      'load_weight_lbs',
      'Enter 0 or more pounds, for example 36000 or 36,000.',
    ],
    [
      { loadWeightLbs: 'heavy' },
      'load_weight_lbs',
      'Enter 0 or more pounds, for example 36000 or 36,000.',
    ],
    [
      { checkpointIntervalMiles: 30 as CheckpointIntervalMiles },
      'checkpoint_interval_miles',
      'Choose 10, 25, or 50 miles.',
    ],
  ])('%j -> %s', (changes, field, message) => {
    const { errors, request } = validateTripForm(values(changes), NOW)

    expect(request).toBeNull()
    expect(errors).toEqual({ [field]: message })
  })

  it('report every invalid field at once', () => {
    const { errors } = validateTripForm(
      values({ origin: '', destination: '', departureLocal: '', loadWeightLbs: '' }),
      NOW,
    )

    expect(Object.keys(errors).sort()).toEqual([
      'departure_time',
      'destination',
      'load_weight_lbs',
      'origin',
    ])
  })
})

describe('parseLoadWeight', () => {
  it.each([
    ['36000', 36000],
    ['36,000', 36000],
    ['1,234,567.5', 1234567.5],
    ['999', 999],
    ['0.5', 0.5],
    // An empty truck is a valid load.
    ['0', 0],
    ['0.0', 0],
    [' 40000 ', 40000],
  ])('%j -> %d', (value, expected) => {
    expect(parseLoadWeight(value)).toBe(expected)
  })

  it.each([
    ...['', '-1', '-0', '-0.5', '1e5', '12abc', 'NaN', 'Infinity', '.5'],
    // Misplaced thousands separators are rejected, never reinterpreted.
    ...['3,6000', '1,2,3', ',36000', '36000,', '36,00', '36,000,0'],
  ])('rejects %j', (value) => {
    expect(parseLoadWeight(value)).toBeNull()
  })
})

describe('chosen places', () => {
  const DENVER = { label: 'Denver, CO, USA', latitude: 39.741, longitude: -104.986 }
  const SALT_LAKE = { label: 'Salt Lake City, UT, USA', latitude: 40.773, longitude: -111.934 }

  it('sends the coordinates of a chosen place with its address', () => {
    const { request } = validateTripForm(
      values({ origin: DENVER.label, originPlace: DENVER }),
      NOW,
    )

    expect(request).toMatchObject({
      origin: 'Denver, CO, USA',
      origin_coordinates: { latitude: 39.741, longitude: -104.986 },
    })
    // The destination was typed, so it is geocoded by the backend as before.
    expect(request).not.toHaveProperty('destination_coordinates')
  })

  it('handles origin and destination independently', () => {
    const { request } = validateTripForm(
      values({ destination: SALT_LAKE.label, destinationPlace: SALT_LAKE }),
      NOW,
    )

    expect(request).not.toHaveProperty('origin_coordinates')
    expect(request?.destination_coordinates).toEqual({ latitude: 40.773, longitude: -111.934 })
  })

  it('never sends coordinates for text that no longer matches the chosen place', () => {
    const { request } = validateTripForm(
      values({ origin: 'Denver, CO, USA 2', originPlace: DENVER }),
      NOW,
    )

    expect(request).not.toHaveProperty('origin_coordinates')
  })

  it('sends typed addresses exactly as before, without coordinates', () => {
    expect(validateTripForm(values(), NOW).request).toEqual({
      origin: 'Denver, CO',
      destination: 'Salt Lake City, UT',
      departure_time: '2026-11-05T08:00:00-07:00',
      load_weight_lbs: 36000,
      checkpoint_interval_miles: 25,
    })
  })

  it('accepts an empty truck', () => {
    expect(validateTripForm(values({ loadWeightLbs: '0' }), NOW).request?.load_weight_lbs).toBe(0)
  })
})
