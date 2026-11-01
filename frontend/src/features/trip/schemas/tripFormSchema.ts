import type { TripField } from '../../analysis/services/apiProblem'
import {
  CHECKPOINT_INTERVALS_MILES,
  DEFAULT_CHECKPOINT_INTERVAL_MILES,
  type CheckpointIntervalMiles,
  type TripAnalysisRequest,
} from '../../analysis/types/api'
import {
  isSkippedLocalTime,
  nextWholeHour,
  parseLocalInputValue,
  toLocalInputValue,
  toOffsetIsoString,
} from '../../../shared/utils/datetime'

/** Matches the backend limit (TripAnalysisRequestSerializer). */
export const MAX_ADDRESS_LENGTH = 200

export interface TripFormValues {
  origin: string
  destination: string
  /** datetime-local value, in the browser's time zone. */
  departureLocal: string
  /** As typed; parsed on submit. */
  loadWeightLbs: string
  checkpointIntervalMiles: CheckpointIntervalMiles
}

export type TripFormErrors = Partial<Record<TripField, string>>

export function initialTripFormValues(now: Date): TripFormValues {
  return {
    origin: '',
    destination: '',
    departureLocal: toLocalInputValue(nextWholeHour(now)),
    loadWeightLbs: '',
    checkpointIntervalMiles: DEFAULT_CHECKPOINT_INTERVAL_MILES,
  }
}

function addressError(value: string, name: string): string | undefined {
  const trimmed = value.trim()
  if (!trimmed) return `Enter the ${name}.`
  if (trimmed.length > MAX_ADDRESS_LENGTH) {
    return `Use at most ${MAX_ADDRESS_LENGTH} characters.`
  }
  return undefined
}

/** Digits, or digits grouped in threes with commas (36,000), with an optional decimal part. */
const LOAD_WEIGHT = /^(\d+|\d{1,3}(,\d{3})+)(\.\d+)?$/

/** A positive number of pounds. Commas are allowed only as correctly placed thousands
 * separators, so a mistyped value such as "3,6000" is rejected rather than reinterpreted. */
export function parseLoadWeight(value: string): number | null {
  const trimmed = value.trim()
  if (!LOAD_WEIGHT.test(trimmed)) return null
  const pounds = Number(trimmed.replace(/,/g, ''))
  return Number.isFinite(pounds) && pounds > 0 ? pounds : null
}

/** Validates the form the same way the backend does, and builds the request if valid. */
export function validateTripForm(
  values: TripFormValues,
  now: Date,
): { errors: TripFormErrors; request: TripAnalysisRequest | null } {
  const errors: TripFormErrors = {}

  const originError = addressError(values.origin, 'origin')
  if (originError) errors.origin = originError
  const destinationError = addressError(values.destination, 'destination')
  if (destinationError) errors.destination = destinationError

  const departure = parseLocalInputValue(values.departureLocal)
  if (!values.departureLocal) {
    errors.departure_time = 'Choose a departure date and time.'
  } else if (!departure && isSkippedLocalTime(values.departureLocal)) {
    errors.departure_time =
      'This time does not exist in your time zone because clocks move forward for daylight ' +
      'saving time. Choose another time.'
  } else if (!departure) {
    errors.departure_time = 'Enter a valid date and time.'
  } else if (departure.getTime() <= now.getTime()) {
    errors.departure_time = 'Choose a departure time in the future.'
  }

  const loadWeight = parseLoadWeight(values.loadWeightLbs)
  if (!values.loadWeightLbs.trim()) {
    errors.load_weight_lbs = 'Enter the cargo weight in pounds.'
  } else if (loadWeight === null) {
    errors.load_weight_lbs = 'Enter a positive number of pounds, for example 36000 or 36,000.'
  }

  if (!CHECKPOINT_INTERVALS_MILES.includes(values.checkpointIntervalMiles)) {
    errors.checkpoint_interval_miles = 'Choose 10, 25, or 50 miles.'
  }

  if (Object.keys(errors).length || !departure || loadWeight === null) {
    return { errors, request: null }
  }
  return {
    errors,
    request: {
      origin: values.origin.trim(),
      destination: values.destination.trim(),
      departure_time: toOffsetIsoString(departure),
      load_weight_lbs: loadWeight,
      checkpoint_interval_miles: values.checkpointIntervalMiles,
    },
  }
}
