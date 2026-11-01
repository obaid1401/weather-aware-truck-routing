import Box from '@mui/material/Box'
import Typography from '@mui/material/Typography'

import type { Checkpoint, RiskLevel } from '../../analysis/types/api'
import { RISK_DISPLAY, RISK_LEVELS } from '../../risk/services/riskDisplay'
import { forecastAtHour } from '../../weather/services/hourlyForecast'
import { tokens } from '../../../shared/theme/theme'
import { formatMiles } from '../../../shared/utils/format'
import { visuallyHidden } from '../../../shared/utils/visuallyHidden'
import { checkpointTitle } from '../services/checkpointLabel'

interface RouteStripProps {
  routeLabel: string
  checkpoints: Checkpoint[]
  distanceMiles: number
  hour: number
  selectedCheckpointId: string | null
  onSelectCheckpoint: (checkpointId: string) => void
}

const TICK_WIDTH = 6

/** A strip map of the selected route: one tick per checkpoint, placed by its distance from the
 * origin and coloured by the backend's risk at the selected hour. Nothing is drawn between
 * checkpoints. The checkpoint list is the keyboard path; this is a visual overview. */
export function RouteStrip({
  routeLabel,
  checkpoints,
  distanceMiles,
  hour,
  selectedCheckpointId,
  onSelectCheckpoint,
}: RouteStripProps) {
  const ticks = checkpoints.map((checkpoint) => ({
    checkpoint,
    risk: (forecastAtHour(checkpoint, hour)?.final_risk ?? 'UNKNOWN') as RiskLevel,
    position: distanceMiles > 0 ? Math.min(1, checkpoint.distance_from_origin_miles / distanceMiles) : 0,
  }))
  const counts = RISK_LEVELS.map((level) => ({
    level,
    count: ticks.filter((tick) => tick.risk === level).length,
  })).filter(({ count }) => count > 0)
  const summary =
    `${routeLabel} at +${hour} h: ` +
    counts.map(({ level, count }) => `${count} ${RISK_DISPLAY[level].label.toLowerCase()}`).join(', ') +
    '.'

  return (
    <Box>
      <Typography variant="subtitle2" component="h3" sx={{ mb: 0.75 }}>
        Along {routeLabel} at +{hour} h
      </Typography>
      <Typography sx={visuallyHidden}>{summary}</Typography>
      <Box aria-hidden sx={{ position: 'relative', height: 30, mx: `${TICK_WIDTH / 2}px` }}>
        {/* The road. */}
        <Box
          sx={{
            position: 'absolute',
            left: 0,
            right: 0,
            top: '50%',
            height: 2,
            mt: '-1px',
            bgcolor: tokens.ink,
          }}
        />
        {ticks.map(({ checkpoint, risk, position }) => {
          const selected = checkpoint.id === selectedCheckpointId
          const unknown = risk === 'UNKNOWN'
          return (
            <Box
              key={checkpoint.id}
              component="button"
              type="button"
              tabIndex={-1}
              data-risk={risk}
              title={`${checkpointTitle(checkpoints, checkpoint)}: ${RISK_DISPLAY[risk].label}`}
              onClick={() => onSelectCheckpoint(checkpoint.id)}
              sx={{
                position: 'absolute',
                left: `calc(${position * 100}% - ${TICK_WIDTH / 2}px)`,
                top: selected ? 0 : 5,
                width: TICK_WIDTH,
                height: selected ? 30 : 20,
                p: 0,
                cursor: 'pointer',
                borderRadius: '2px',
                bgcolor: unknown ? tokens.paper : RISK_DISPLAY[risk].color,
                border: unknown ? '1px dashed #616161' : `1px solid ${tokens.paper}`,
                outline: selected ? `2px solid ${tokens.ink}` : 'none',
                outlineOffset: 1,
                '&:hover': selected ? undefined : { outline: `2px solid ${tokens.steel}` },
              }}
            />
          )
        })}
      </Box>
      <Box
        aria-hidden
        sx={{
          display: 'flex',
          justifyContent: 'space-between',
          mt: 0.5,
          typography: 'caption',
          color: 'text.secondary',
          fontVariantNumeric: 'tabular-nums',
        }}
      >
        <span>A, 0 mi</span>
        <span>B, {formatMiles(distanceMiles)}</span>
      </Box>
    </Box>
  )
}
