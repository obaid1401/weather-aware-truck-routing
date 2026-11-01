import Box from '@mui/material/Box'
import Slider from '@mui/material/Slider'
import Typography from '@mui/material/Typography'

import { formatDateTime } from '../../../shared/utils/format'
import { MAX_FORECAST_HOUR } from '../services/hourlyForecast'

interface ForecastSliderProps {
  hour: number
  /** ISO-8601 time of the selected hour. */
  time: string
  onChange: (hour: number) => void
  /** Checkpoints of the selected route without a forecast at this hour. */
  unavailableCount: number
  checkpointCount: number
}

const MARKS = [0, 12, 24, 36, 48].map((value) => ({ value, label: `${value} h` }))

/** Picks an hour after departure for the weather heatmap and checkpoint details. Uses the
 * forecast already in the analysis response: it never sends a request or changes the ranking. */
export function ForecastSlider({
  hour,
  time,
  onChange,
  unavailableCount,
  checkpointCount,
}: ForecastSliderProps) {
  const hourText = `${hour} ${hour === 1 ? 'hour' : 'hours'} after departure`
  const timeText = formatDateTime(time)

  return (
    <Box>
      <Typography variant="subtitle2" component="h3" id="forecast-slider-label">
        Forecast hour
      </Typography>
      {/* Screen readers hear the hour and time from the slider's aria-valuetext. */}
      <Box sx={{ display: 'flex', alignItems: 'baseline', flexWrap: 'wrap', columnGap: 1.5 }}>
        <Typography
          component="span"
          sx={{ fontSize: '1.75rem', fontWeight: 800, lineHeight: 1.1, fontVariantNumeric: 'tabular-nums' }}
        >
          +{hour} h
        </Typography>
        <Typography component="span" variant="body2" color="text.secondary">
          {timeText}
        </Typography>
      </Box>
      <Box sx={{ px: 1.25, pt: 0.5 }}>
        <Slider
          value={hour}
          min={0}
          max={MAX_FORECAST_HOUR}
          step={1}
          marks={MARKS}
          onChange={(_event, value) => onChange(value as number)}
          valueLabelDisplay="off"
          getAriaValueText={() => `${hourText}, ${timeText}`}
          aria-labelledby="forecast-slider-label"
        />
      </Box>
      <Typography variant="caption" color="text.secondary" component="p">
        Conditions at each checkpoint at this hour, whenever the truck reaches it. Rankings always
        use the forecast at each checkpoint’s estimated arrival.
      </Typography>
      {unavailableCount > 0 && (
        <Typography variant="caption" component="p" sx={{ mt: 0.5, fontWeight: 700 }}>
          No forecast for {unavailableCount} of {checkpointCount} checkpoints at this hour. They are
          shown as unavailable.
        </Typography>
      )}
    </Box>
  )
}
