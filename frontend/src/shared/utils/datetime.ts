// Departure times are entered in the browser's local time (<input type="datetime-local">,
// which has no time zone) and sent to the backend as ISO-8601 with the matching UTC offset.

const LOCAL_INPUT = /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})$/

const pad = (value: number) => String(value).padStart(2, '0')

/** "YYYY-MM-DDTHH:mm" in local time, the format a datetime-local input uses. */
export function toLocalInputValue(date: Date): string {
  return (
    `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}` +
    `T${pad(date.getHours())}:${pad(date.getMinutes())}`
  )
}

function inputFields(value: string): number[] | null {
  const match = LOCAL_INPUT.exec(value)
  return match ? match.slice(1).map(Number) : null
}

/** The local Date for a datetime-local value, or null if it is not a real date and time. */
export function parseLocalInputValue(value: string): Date | null {
  const fields = inputFields(value)
  if (!fields) return null
  const [year, month, day, hours, minutes] = fields
  const date = new Date(year, month - 1, day, hours, minutes)
  // Reject values the Date constructor silently rolls over (for example February 30).
  const sameFields =
    date.getFullYear() === year &&
    date.getMonth() === month - 1 &&
    date.getDate() === day &&
    date.getHours() === hours &&
    date.getMinutes() === minutes
  return sameFields ? date : null
}

/** True for a valid calendar date and time that does not exist in the local time zone, because
 * the clocks skip it when daylight saving time starts (for example 02:30 in America/Denver). */
export function isSkippedLocalTime(value: string): boolean {
  const fields = inputFields(value)
  if (!fields || parseLocalInputValue(value)) return false
  const [year, month, day, hours, minutes] = fields
  // UTC has no daylight saving, so this checks only that the fields form a real date and time.
  const utc = new Date(Date.UTC(year, month - 1, day, hours, minutes))
  return (
    utc.getUTCFullYear() === year &&
    utc.getUTCMonth() === month - 1 &&
    utc.getUTCDate() === day &&
    utc.getUTCHours() === hours &&
    utc.getUTCMinutes() === minutes
  )
}

/** UTC offset of `date` in the local time zone, as "+HH:MM" or "-HH:MM". */
export function utcOffset(date: Date): string {
  // getTimezoneOffset is minutes *behind* UTC, and depends on the date (daylight saving).
  const minutesAhead = -date.getTimezoneOffset()
  const sign = minutesAhead >= 0 ? '+' : '-'
  const absolute = Math.abs(minutesAhead)
  return `${sign}${pad(Math.floor(absolute / 60))}:${pad(absolute % 60)}`
}

/** ISO-8601 local time with its UTC offset, for example 2026-11-05T08:00:00-07:00. */
export function toOffsetIsoString(date: Date): string {
  return `${toLocalInputValue(date)}:${pad(date.getSeconds())}${utcOffset(date)}`
}

/** The start of the next whole hour after `now`, a sensible default departure. */
export function nextWholeHour(now: Date): Date {
  const next = new Date(now)
  next.setMinutes(0, 0, 0)
  next.setHours(next.getHours() + 1)
  return next
}
