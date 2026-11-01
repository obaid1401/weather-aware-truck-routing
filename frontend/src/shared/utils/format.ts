// Display formatting. Values come from the backend; nothing here calculates risk.

export function formatMiles(miles: number): string {
  return `${miles.toLocaleString('en-US', { maximumFractionDigits: 1, minimumFractionDigits: 1 })} mi`
}

export function formatDuration(seconds: number): string {
  const totalMinutes = Math.round(seconds / 60)
  const hours = Math.floor(totalMinutes / 60)
  const minutes = totalMinutes % 60
  return hours ? `${hours} h ${String(minutes).padStart(2, '0')} min` : `${minutes} min`
}

/** Local date and time with the time zone name, for an ISO-8601 timestamp. */
export function formatDateTime(iso: string): string {
  return new Intl.DateTimeFormat('en-US', {
    weekday: 'short',
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
    timeZoneName: 'short',
  }).format(new Date(iso))
}

/** Rounded down, so incomplete coverage is never shown as 100%. */
export function formatPercent(value: number): string {
  const tenths = Math.floor(value * 10 + 1e-9) / 10
  return `${Number.isInteger(tenths) ? tenths.toFixed(0) : tenths.toFixed(1)}%`
}
