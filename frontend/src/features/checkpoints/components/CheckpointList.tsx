import Box from '@mui/material/Box'
import List from '@mui/material/List'
import ListItemButton from '@mui/material/ListItemButton'
import Typography from '@mui/material/Typography'

import type { Checkpoint } from '../../analysis/types/api'
import { RiskBadge } from '../../risk/components/RiskBadge'
import { RISK_DISPLAY } from '../../risk/services/riskDisplay'
import { tokens } from '../../../shared/theme/theme'
import { formatDateTime, formatMiles } from '../../../shared/utils/format'
import { checkpointName, checkpointTitle } from '../services/checkpointLabel'

interface CheckpointListProps {
  checkpoints: Checkpoint[]
  selectedCheckpointId: string | null
  onSelectCheckpoint: (checkpointId: string) => void
}

/** The selected route's checkpoints as a mileage log, with their risk at estimated arrival.
 * The keyboard path for choosing a checkpoint (the map and strip are pointer shortcuts). */
export function CheckpointList({
  checkpoints,
  selectedCheckpointId,
  onSelectCheckpoint,
}: CheckpointListProps) {
  return (
    <Box component="section" aria-labelledby="checkpoint-list-title">
      <Typography variant="subtitle2" component="h3" id="checkpoint-list-title">
        All checkpoints ({checkpoints.length})
      </Typography>
      <Typography variant="caption" color="text.secondary" component="p" sx={{ mb: 1 }}>
        Risk at each checkpoint’s estimated arrival.
      </Typography>
      <List
        dense
        disablePadding
        aria-labelledby="checkpoint-list-title"
        sx={{ maxHeight: 420, overflowY: 'auto', display: 'grid', gap: 0.5 }}
      >
        {checkpoints.map((checkpoint) => {
          const selected = checkpoint.id === selectedCheckpointId
          return (
            <ListItemButton
              key={checkpoint.id}
              selected={selected}
              aria-current={selected ? 'true' : undefined}
              aria-label={`${checkpointTitle(checkpoints, checkpoint)}, arrives ${formatDateTime(checkpoint.estimated_arrival_time)}, ${RISK_DISPLAY[checkpoint.final_risk].label} risk`}
              onClick={() => onSelectCheckpoint(checkpoint.id)}
              sx={{
                gap: 1.5,
                px: 1.5,
                minHeight: 52,
                borderRadius: '8px',
                // Long trips at 10-mile intervals can list 90+ checkpoints: skip off-screen work.
                contentVisibility: 'auto',
                containIntrinsicSize: 'auto 52px',
                boxShadow: selected ? `inset 0 0 0 2px ${tokens.shieldBlue}` : 'none',
                '&:hover': { bgcolor: tokens.canvas },
                '&.Mui-selected, &.Mui-selected:hover': { bgcolor: tokens.selectedTint },
              }}
            >
              <Box
                component="span"
                aria-hidden
                sx={{
                  width: 10,
                  height: 10,
                  flexShrink: 0,
                  borderRadius: '50%',
                  bgcolor: RISK_DISPLAY[checkpoint.final_risk].color,
                  border: checkpoint.final_risk === 'UNKNOWN' ? '1px dashed #616161' : 0,
                }}
              />
              <Box
                component="span"
                sx={{ width: 80, flexShrink: 0, fontWeight: 800, fontVariantNumeric: 'tabular-nums', whiteSpace: 'nowrap' }}
              >
                {formatMiles(checkpoint.distance_from_origin_miles)}
              </Box>
              <Box component="span" sx={{ flex: 1, minWidth: 0 }}>
                <Box component="span" sx={{ display: 'block', typography: 'body2', fontWeight: 600 }}>
                  {checkpointName(checkpoints, checkpoint)}
                </Box>
                <Box component="span" sx={{ display: 'block', typography: 'caption', color: 'text.secondary' }}>
                  {formatDateTime(checkpoint.estimated_arrival_time)}
                </Box>
              </Box>
              <RiskBadge risk={checkpoint.final_risk} size="small" />
            </ListItemButton>
          )
        })}
      </List>
    </Box>
  )
}
