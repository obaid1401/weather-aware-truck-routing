import type { DataStatus, RiskLevel } from '../../analysis/types/api'

// How each backend risk level is shown. The frontend never calculates risk: it only displays the
// level the backend returned. UNKNOWN has its own neutral style and is never shown as low risk.

export interface RiskDisplay {
  label: string
  /** Fill colour for badges, markers, and heatmap circles. */
  color: string
  /** Text colour on `color` (contrast of at least 4.5:1). */
  textColor: string
  description: string
}

const DARK_TEXT = '#1a2230'
const LIGHT_TEXT = '#ffffff'

export const RISK_DISPLAY: Record<RiskLevel, RiskDisplay> = {
  LOW: {
    label: 'Low',
    color: '#2e7d32',
    textColor: LIGHT_TEXT,
    description: 'Wind, rain, and snow below the moderate thresholds.',
  },
  MODERATE: {
    label: 'Moderate',
    color: '#fbc02d',
    textColor: DARK_TEXT,
    description: 'At least one factor at the moderate threshold.',
  },
  HIGH: {
    label: 'High',
    color: '#f57c00',
    textColor: DARK_TEXT,
    description: 'At least one factor at the high threshold.',
  },
  SEVERE: {
    label: 'Severe',
    color: '#c62828',
    textColor: LIGHT_TEXT,
    description: 'At least one factor at the severe threshold, or heavy cargo in high wind.',
  },
  NO_TRAVEL: {
    label: 'No travel',
    color: '#4a148c',
    textColor: LIGHT_TEXT,
    description: 'Conditions where travel is not advised for this load.',
  },
  UNKNOWN: {
    label: 'Unavailable',
    color: '#bdbdbd',
    textColor: DARK_TEXT,
    description: 'No forecast data, so the risk is unknown. Never treated as low risk.',
  },
}

/** Legend order: increasing severity, then unknown. */
export const RISK_LEVELS: RiskLevel[] = ['LOW', 'MODERATE', 'HIGH', 'SEVERE', 'NO_TRAVEL', 'UNKNOWN']

export const DATA_STATUS_LABELS: Record<DataStatus, string> = {
  AVAILABLE: 'Complete',
  PARTIAL: 'Partial: some values unavailable',
  UNAVAILABLE: 'Unavailable',
}
