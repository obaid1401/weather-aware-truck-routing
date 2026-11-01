import type { Checkpoint } from '../../analysis/types/api'
import { formatMiles } from '../../../shared/utils/format'

/** "Origin", "Destination", or "Checkpoint n", from the checkpoint's position on its route
 * (the backend always includes the origin at mile 0 and the destination). */
export function checkpointName(checkpoints: Checkpoint[], checkpoint: Checkpoint): string {
  const index = checkpoints.indexOf(checkpoint)
  if (index === 0) return 'Origin'
  if (index === checkpoints.length - 1) return 'Destination'
  return `Checkpoint ${index}`
}

export function checkpointTitle(checkpoints: Checkpoint[], checkpoint: Checkpoint): string {
  return `${checkpointName(checkpoints, checkpoint)} · ${formatMiles(checkpoint.distance_from_origin_miles)}`
}
