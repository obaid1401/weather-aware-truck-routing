import Box from '@mui/material/Box'
import List from '@mui/material/List'
import ListItemButton from '@mui/material/ListItemButton'
import ListItemText from '@mui/material/ListItemText'
import Typography from '@mui/material/Typography'

import type { Checkpoint } from '../../analysis/types/api'
import { RiskBadge } from '../../risk/components/RiskBadge'
import { formatDateTime } from '../../../shared/utils/format'
import { checkpointTitle } from '../services/checkpointLabel'

interface CheckpointListProps {
  checkpoints: Checkpoint[]
  selectedCheckpointId: string | null
  onSelectCheckpoint: (checkpointId: string) => void
}

/** The selected route's checkpoints with their risk at estimated arrival. A keyboard-friendly
 * alternative to clicking markers on the map. */
export function CheckpointList({
  checkpoints,
  selectedCheckpointId,
  onSelectCheckpoint,
}: CheckpointListProps) {
  return (
    <Box component="section" aria-labelledby="checkpoint-list-title">
      <Typography variant="subtitle1" component="h3" id="checkpoint-list-title" sx={{ fontWeight: 600 }}>
        Checkpoints ({checkpoints.length})
      </Typography>
      <Typography variant="caption" color="text.secondary" component="p">
        Risk at each checkpoint&apos;s estimated arrival.
      </Typography>
      <List
        dense
        aria-labelledby="checkpoint-list-title"
        sx={{ maxHeight: 320, overflowY: 'auto', border: 1, borderColor: 'divider', borderRadius: 1, mt: 1 }}
      >
        {checkpoints.map((checkpoint) => (
          <ListItemButton
            key={checkpoint.id}
            selected={checkpoint.id === selectedCheckpointId}
            aria-current={checkpoint.id === selectedCheckpointId ? 'true' : undefined}
            onClick={() => onSelectCheckpoint(checkpoint.id)}
          >
            <ListItemText
              primary={checkpointTitle(checkpoints, checkpoint)}
              secondary={formatDateTime(checkpoint.estimated_arrival_time)}
            />
            <RiskBadge risk={checkpoint.final_risk} size="small" />
          </ListItemButton>
        ))}
      </List>
    </Box>
  )
}
