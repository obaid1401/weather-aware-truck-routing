import Box from '@mui/material/Box'
import Typography from '@mui/material/Typography'

import { RISK_LEVELS } from '../services/riskDisplay'
import { RiskBadge } from './RiskBadge'

/** A compact legend: every risk level as a labelled colour, in order of severity, then
 * unavailable. The full explanation of each level is in RiskLegend. */
export function RiskScale() {
  return (
    <Box sx={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap', gap: 0.75 }}>
      <Typography variant="caption" component="h3" id="risk-scale-title" sx={{ fontWeight: 700, mr: 0.5 }}>
        Risk
      </Typography>
      <Box
        component="ul"
        aria-labelledby="risk-scale-title"
        sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5, listStyle: 'none', m: 0, p: 0 }}
      >
        {RISK_LEVELS.map((level) => (
          <li key={level}>
            <RiskBadge risk={level} size="small" />
          </li>
        ))}
      </Box>
    </Box>
  )
}
