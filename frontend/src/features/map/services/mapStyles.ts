import type { PathOptions } from 'leaflet'

import type { RiskLevel } from '../../analysis/types/api'
import { RISK_DISPLAY } from '../../risk/services/riskDisplay'
import { tokens } from '../../../shared/theme/theme'

const METERS_PER_MILE = 1609.344
const UNKNOWN_OUTLINE = '#616161'

export const SELECTED_ROUTE_COLOR = tokens.shieldBlue
export const ALTERNATE_ROUTE_COLOR = '#6b7783'

/** Heatmap circles are about half the checkpoint interval in radius, so neighbouring circles
 * touch and form a band along the corridor without implying data between checkpoints. */
export function heatmapRadiusMeters(checkpointIntervalMiles: number): number {
  return (checkpointIntervalMiles / 2) * METERS_PER_MILE
}

/** One heatmap circle, coloured by the backend's risk for the selected hour. Unknown risk is a
 * grey circle with a dashed outline, never a "low risk" colour. */
export function heatmapCellStyle(risk: RiskLevel): PathOptions {
  const unknown = risk === 'UNKNOWN'
  return {
    fillColor: RISK_DISPLAY[risk].color,
    fillOpacity: unknown ? 0.25 : 0.35,
    stroke: unknown,
    color: UNKNOWN_OUTLINE,
    weight: 1,
    dashArray: unknown ? '4 4' : undefined,
    className: `heatmap-cell risk-${risk.toLowerCase()}`,
  }
}

/** A checkpoint marker, coloured by the backend's risk at the estimated arrival. */
export function checkpointMarkerStyle(risk: RiskLevel, selected: boolean): PathOptions {
  const unknown = risk === 'UNKNOWN'
  return {
    fillColor: RISK_DISPLAY[risk].color,
    fillOpacity: 1,
    color: selected ? tokens.ink : unknown ? UNKNOWN_OUTLINE : '#ffffff',
    weight: selected ? 3 : 2,
    dashArray: unknown && !selected ? '3 2' : undefined,
    className: `checkpoint-marker risk-${risk.toLowerCase()}${selected ? ' selected' : ''}`,
  }
}
