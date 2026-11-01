import Box from '@mui/material/Box'

import type { RiskLevel, RouteMetrics } from '../../analysis/types/api'
import { RISK_DISPLAY } from '../../risk/services/riskDisplay'
import { formatMiles } from '../../../shared/utils/format'

/** The backend's mileage for each risk level, in order of severity, then unknown. */
const SEGMENTS: { risk: RiskLevel; miles: (m: RouteMetrics) => number }[] = [
  { risk: 'LOW', miles: (m) => m.low_miles },
  { risk: 'MODERATE', miles: (m) => m.moderate_miles },
  { risk: 'HIGH', miles: (m) => m.high_miles },
  { risk: 'SEVERE', miles: (m) => m.severe_miles },
  { risk: 'NO_TRAVEL', miles: (m) => m.no_travel_miles },
  { risk: 'UNKNOWN', miles: (m) => m.unknown_miles },
]

/** A bar showing how many of the route's miles the backend put at each risk level. A summary of
 * the backend's own route metrics: nothing is calculated here. */
export function RouteRiskBar({ metrics }: { metrics: RouteMetrics }) {
  const parts = SEGMENTS.map(({ risk, miles }) => ({ risk, miles: miles(metrics) })).filter(
    (part) => part.miles > 0,
  )
  const total = parts.reduce((sum, part) => sum + part.miles, 0)
  const label =
    'Route miles by risk: ' +
    (parts.length
      ? parts.map((p) => `${formatMiles(p.miles)} ${RISK_DISPLAY[p.risk].label.toLowerCase()}`).join(', ')
      : 'no data')

  return (
    <Box
      role="img"
      aria-label={label}
      sx={{ display: 'flex', height: 10, borderRadius: 5, overflow: 'hidden', bgcolor: '#e4e9f0', gap: '2px' }}
    >
      {parts.map((part) => (
        <Box
          key={part.risk}
          data-risk={part.risk}
          title={`${RISK_DISPLAY[part.risk].label}: ${formatMiles(part.miles)}`}
          sx={{
            flex: `${part.miles / total} 0 0`,
            minWidth: 4,
            bgcolor: RISK_DISPLAY[part.risk].color,
            // Unknown miles are hatched, never a solid "safe" colour.
            ...(part.risk === 'UNKNOWN' && {
              backgroundImage:
                'repeating-linear-gradient(135deg, transparent 0 3px, rgba(97, 97, 97, 0.55) 3px 5px)',
            }),
          }}
        />
      ))}
    </Box>
  )
}
