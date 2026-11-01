import Alert from '@mui/material/Alert'
import Box from '@mui/material/Box'
import Divider from '@mui/material/Divider'
import Typography from '@mui/material/Typography'

import type { Checkpoint } from '../../analysis/types/api'
import { WeatherReadings } from '../../weather/components/WeatherReadings'
import { forecastAtHour } from '../../weather/services/hourlyForecast'
import { formatDateTime } from '../../../shared/utils/format'
import { checkpointTitle } from '../services/checkpointLabel'

interface CheckpointDetailsProps {
  checkpoints: Checkpoint[]
  checkpoint: Checkpoint | null
  hour: number
  /** ISO-8601 time of the selected forecast hour. */
  hourTime: string
}

/** One checkpoint's forecast at its estimated arrival (used for ranking) and at the hour
 * selected on the forecast slider. */
export function CheckpointDetails({ checkpoints, checkpoint, hour, hourTime }: CheckpointDetailsProps) {
  if (!checkpoint) {
    return (
      <Typography variant="body2" color="text.secondary">
        Select a checkpoint on the map or in the list to see its forecast.
      </Typography>
    )
  }

  const hourly = forecastAtHour(checkpoint, hour)

  return (
    <Box component="section" aria-labelledby="checkpoint-details-title">
      <Typography variant="h3" id="checkpoint-details-title">
        {checkpointTitle(checkpoints, checkpoint)}
      </Typography>
      <Typography variant="caption" color="text.secondary" component="p" sx={{ mb: 2 }}>
        {checkpoint.latitude.toFixed(4)}, {checkpoint.longitude.toFixed(4)}
      </Typography>

      <Typography variant="subtitle2" component="h4">
        At estimated arrival: {formatDateTime(checkpoint.estimated_arrival_time)}
      </Typography>
      <Typography variant="caption" color="text.secondary" component="p" sx={{ mb: 1 }}>
        Used for the route metrics and ranking.
      </Typography>
      <WeatherReadings forecast={checkpoint} caption="Forecast at estimated arrival" />
      {checkpoint.warnings.length > 0 && (
        <Alert severity="warning" sx={{ mt: 1.5 }}>
          <Box component="ul" sx={{ m: 0, pl: 2 }}>
            {checkpoint.warnings.map((warning, index) => (
              // The list is fixed for one response, and a message may repeat.
              <li key={index}>{warning}</li>
            ))}
          </Box>
        </Alert>
      )}

      <Divider sx={{ my: 2 }} />

      <Typography variant="subtitle2" component="h4">
        At +{hour} h: {formatDateTime(hourTime)}
      </Typography>
      <Typography variant="caption" color="text.secondary" component="p" sx={{ mb: 1 }}>
        Conditions at this location at the selected hour, whenever the truck reaches it.
      </Typography>
      {hourly ? (
        <WeatherReadings forecast={hourly} caption={`Forecast at +${hour} hours`} />
      ) : (
        <Alert severity="info">Forecast unavailable for this hour. The risk is unknown.</Alert>
      )}
    </Box>
  )
}
