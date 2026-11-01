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
 * forecast already in the analysis response: it never sends a request or changes the ranking.
 * Kept compact because it floats over the map. */
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
    <Box sx={{ minWidth: 0 }}>
      {/* Screen readers hear the hour and time from the slider's aria-valuetext. */}
      <Box sx={{ display: 'flex', alignItems: 'baseline', flexWrap: 'wrap', columnGap: 1 }}>
        <Typography
          variant="caption"
          component="h3"
          id="forecast-slider-label"
          sx={{ fontWeight: 700, color: 'text.secondary' }}
        >
          Forecast hour
        </Typography>
        <Typography
          component="span"
          sx={{ fontSize: '1.125rem', fontWeight: 800, lineHeight: 1.2, fontVariantNumeric: 'tabular-nums' }}
        >
          +{hour} h
        </Typography>
        <Typography component="span" variant="caption" color="text.secondary">
          {timeText}
        </Typography>
      </Box>
      <Box sx={{ px: 1 }}>
        <Slider
          size="small"
          value={hour}
          min={0}
          max={MAX_FORECAST_HOUR}
          step={1}
          marks={MARKS}
          onChange={(_event, value) => onChange(value as number)}
          valueLabelDisplay="off"
          getAriaValueText={() => `${hourText}, ${timeText}`}
          aria-labelledby="forecast-slider-label"
          sx={{
            mt: 0.25,
            mb: 2.25,
            py: 1.25,
            '& .MuiSlider-thumb': { width: 18, height: 18 },
            '& .MuiSlider-markLabel': { fontSize: '0.75rem', top: 24 },
          }}
        />
      </Box>
      <Typography variant="caption" color="text.secondary" component="p">
        Changes the map colours only. Rankings use the forecast at each checkpoint’s arrival.
      </Typography>
      {unavailableCount > 0 && (
        <Typography variant="caption" component="p" sx={{ fontWeight: 700 }}>
          No forecast for {unavailableCount} of {checkpointCount} checkpoints at this hour. They are
          shown as unavailable.
        </Typography>
      )}
    </Box>
  )
}
