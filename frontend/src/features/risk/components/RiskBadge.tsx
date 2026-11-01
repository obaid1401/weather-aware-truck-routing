import Box from '@mui/material/Box'

import type { RiskLevel } from '../../analysis/types/api'
import { RISK_DISPLAY } from '../services/riskDisplay'

interface RiskBadgeProps {
  risk: RiskLevel
  size?: 'small' | 'medium'
}

/** A risk level as a coloured label. The text always names the level, so colour is never the
 * only cue. */
export function RiskBadge({ risk, size = 'medium' }: RiskBadgeProps) {
  const display = RISK_DISPLAY[risk]
  return (
    <Box
      component="span"
      data-risk={risk}
      sx={{
        display: 'inline-block',
        px: size === 'small' ? 0.75 : 1,
        py: size === 'small' ? 0 : 0.25,
        borderRadius: 1,
        bgcolor: display.color,
        color: display.textColor,
        typography: size === 'small' ? 'caption' : 'body2',
        fontWeight: 600,
        whiteSpace: 'nowrap',
        // Unknown risk is drawn with a dashed outline everywhere, never as a solid "safe" colour.
        border: risk === 'UNKNOWN' ? '1px dashed #616161' : '1px solid transparent',
      }}
    >
      {display.label}
    </Box>
  )
}
