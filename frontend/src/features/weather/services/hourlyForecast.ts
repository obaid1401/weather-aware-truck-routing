import type { Checkpoint, HourlyForecast } from '../../analysis/types/api'

/** The slider covers 0 to 48 hours after departure (FR-12). */
export const MAX_FORECAST_HOUR = 48

/** The backend's hourly entry for `hour`, or null if the response has none. A missing entry is
 * shown as unavailable; neighbouring hours or checkpoints are never substituted. */
export function forecastAtHour(checkpoint: Checkpoint, hour: number): HourlyForecast | null {
  return checkpoint.hourly_forecasts.find((entry) => entry.hour_offset === hour) ?? null
}

/** The time the slider hour refers to: the backend's target_time for that hour, or departure
 * plus the hour if no checkpoint has an entry for it. */
export function forecastHourTime(
  checkpoints: Checkpoint[],
  departureTime: string,
  hour: number,
): string {
  for (const checkpoint of checkpoints) {
    const entry = forecastAtHour(checkpoint, hour)
    if (entry) return entry.target_time
  }
  return new Date(Date.parse(departureTime) + hour * 3_600_000).toISOString()
}

/** How many checkpoints have no known risk at `hour` (missing entry or UNKNOWN). */
export function countUnavailableAtHour(checkpoints: Checkpoint[], hour: number): number {
  return checkpoints.filter((checkpoint) => {
    const entry = forecastAtHour(checkpoint, hour)
    return !entry || entry.final_risk === 'UNKNOWN'
  }).length
}
