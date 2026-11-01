import Box from '@mui/material/Box'
import Typography from '@mui/material/Typography'

import { RISK_DISPLAY, RISK_LEVELS } from '../services/riskDisplay'
import { RiskBadge } from './RiskBadge'

/** Every risk level with its colour, label, and meaning, including unavailable data. */
export function RiskLegend({ title = 'Risk levels' }: { title?: string }) {
  return (
    <Box component="section" aria-labelledby="risk-legend-title">
      <Typography variant="subtitle2" component="h4" id="risk-legend-title" gutterBottom>
        {title}
      </Typography>
      <Box
        component="ul"
        sx={{
          listStyle: 'none',
          m: 0,
          p: 0,
          display: 'grid',
          gap: 1,
          gridTemplateColumns: { xs: '1fr', sm: '1fr 1fr', lg: '1fr 1fr 1fr' },
        }}
      >
        {RISK_LEVELS.map((level) => (
          <Box component="li" key={level} sx={{ display: 'flex', gap: 1, alignItems: 'flex-start' }}>
            <RiskBadge risk={level} size="small" />
            <Typography variant="caption" color="text.secondary">
              {RISK_DISPLAY[level].description}
            </Typography>
          </Box>
        ))}
      </Box>
    </Box>
  )
}
