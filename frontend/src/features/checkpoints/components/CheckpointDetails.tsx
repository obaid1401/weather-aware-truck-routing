import AcUnitOutlinedIcon from '@mui/icons-material/AcUnitOutlined'
import AirOutlinedIcon from '@mui/icons-material/AirOutlined'
import TouchAppOutlinedIcon from '@mui/icons-material/TouchAppOutlined'
import WaterDropOutlinedIcon from '@mui/icons-material/WaterDropOutlined'
import Alert from '@mui/material/Alert'
import Box from '@mui/material/Box'
import Typography from '@mui/material/Typography'
import type { ReactNode } from 'react'

import type { Checkpoint, RiskFields, RiskLevel, WeatherFields } from '../../analysis/types/api'
import { RiskBadge } from '../../risk/components/RiskBadge'
import { DATA_STATUS_LABELS } from '../../risk/services/riskDisplay'
import { forecastAtHour } from '../../weather/services/hourlyForecast'
import { tokens } from '../../../shared/theme/theme'
import { formatDateTime, formatShortDateTime } from '../../../shared/utils/format'
import { checkpointTitle } from '../services/checkpointLabel'

interface CheckpointDetailsProps {
  checkpoints: Checkpoint[]
  checkpoint: Checkpoint | null
  hour: number
  /** ISO-8601 time of the selected forecast hour. */
  hourTime: string
}

type Forecast = WeatherFields & RiskFields

const UNAVAILABLE = 'Unavailable'

function reading(value: number | null, digits: number, unit: string): string {
  return value === null ? UNAVAILABLE : `${value.toFixed(digits)} ${unit}`
}

interface Row {
  label: string
  icon?: ReactNode
  /** The cell for one forecast (at arrival, or at the selected hour). */
  cell: (forecast: Forecast) => ReactNode
}

function valueWithRisk(value: string, risk: RiskLevel) {
  return (
    <Box sx={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: 0.75 }}>
      <span>{value}</span>
      <RiskBadge risk={risk} size="small" />
    </Box>
  )
}

const ROWS: Row[] = [
  { label: 'Overall risk', cell: (f) => <RiskBadge risk={f.final_risk} /> },
  {
    label: 'Wind',
    icon: <AirOutlinedIcon />,
    cell: (f) => valueWithRisk(reading(f.wind_speed_mph, 1, 'mph'), f.wind_risk),
  },
  {
    label: 'Rain',
    icon: <WaterDropOutlinedIcon />,
    cell: (f) => valueWithRisk(reading(f.precipitation_inches_per_hour, 2, 'in/hr'), f.rain_risk),
  },
  {
    label: 'Snowfall',
    icon: <AcUnitOutlinedIcon />,
    cell: (f) => valueWithRisk(reading(f.snowfall_inches_per_hour, 2, 'in/hr'), f.snow_risk),
  },
  {
    label: 'Forecast for',
    cell: (f) => (f.forecast_timestamp ? formatShortDateTime(f.forecast_timestamp) : UNAVAILABLE),
  },
  { label: 'Data', cell: (f) => DATA_STATUS_LABELS[f.data_status] },
]

/** One checkpoint's forecast at its estimated arrival (used for ranking) beside its forecast at
 * the hour selected on the forecast slider. Missing values are shown as unavailable, never 0. */
export function CheckpointDetails({ checkpoints, checkpoint, hour, hourTime }: CheckpointDetailsProps) {
  if (!checkpoint) {
    return (
      <Box sx={{ display: 'flex', gap: 1.5, alignItems: 'center', p: 2, borderRadius: '10px', bgcolor: tokens.canvas }}>
        <TouchAppOutlinedIcon sx={{ color: tokens.shieldBlue }} aria-hidden />
        <Typography variant="body2" color="text.secondary">
          Select a checkpoint on the map, on the strip below the map, or in the list to see its
          forecast.
        </Typography>
      </Box>
    )
  }

  const hourly = forecastAtHour(checkpoint, hour)

  return (
    <Box component="section" aria-labelledby="checkpoint-details-title">
      <Typography variant="h3" id="checkpoint-details-title" sx={{ fontSize: '1.0625rem', fontWeight: 800 }}>
        {checkpointTitle(checkpoints, checkpoint)}
      </Typography>
      <Typography variant="caption" color="text.secondary" component="p" sx={{ mb: 1.5 }}>
        Arrives {formatDateTime(checkpoint.estimated_arrival_time)}. Location{' '}
        {checkpoint.latitude.toFixed(4)}, {checkpoint.longitude.toFixed(4)}.
      </Typography>

      {checkpoint.warnings.length > 0 && (
        <Alert severity="warning" sx={{ mb: 1.5 }}>
          <Box component="ul" sx={{ m: 0, pl: 2 }}>
            {checkpoint.warnings.map((warning, index) => (
              // The list is fixed for one response, and a message may repeat.
              <li key={index}>{warning}</li>
            ))}
          </Box>
        </Alert>
      )}

      <Box
        component="table"
        aria-label="Forecast at this checkpoint"
        sx={{
          width: '100%',
          borderCollapse: 'separate',
          borderSpacing: 0,
          tableLayout: 'fixed',
          fontVariantNumeric: 'tabular-nums',
          '& th, & td': { textAlign: 'left', verticalAlign: 'middle', px: 1, py: 0.875, typography: 'body2' },
          '& tbody tr:not(:last-of-type) > *': { borderBottom: 1, borderColor: tokens.rule },
          '& tbody th': { color: 'text.secondary', fontWeight: 600, width: 104, pl: 0 },
          '& td': { fontWeight: 600 },
        }}
      >
        <thead>
          <tr>
            <Box component="th" scope="col" sx={{ width: 104, pl: '0 !important' }}>
              <Box component="span" sx={{ typography: 'caption', color: 'text.secondary' }}>
                Forecast
              </Box>
            </Box>
            <Box component="th" scope="col" sx={{ bgcolor: tokens.canvas, borderRadius: '8px 0 0 8px' }}>
              <Box component="span" sx={{ display: 'block', fontWeight: 800 }}>
                At arrival
              </Box>
              <Box component="span" sx={{ display: 'block', typography: 'caption', color: 'text.secondary' }}>
                Used for ranking
              </Box>
            </Box>
            <Box component="th" scope="col" sx={{ bgcolor: tokens.selectedTint, borderRadius: '0 8px 8px 0' }}>
              <Box component="span" sx={{ display: 'block', fontWeight: 800 }}>
                At +{hour} h
              </Box>
              <Box component="span" sx={{ display: 'block', typography: 'caption', color: 'text.secondary' }}>
                {formatShortDateTime(hourTime)}
              </Box>
            </Box>
          </tr>
        </thead>
        <tbody>
          {ROWS.map((row) => (
            <tr key={row.label}>
              <th scope="row">
                <Box component="span" sx={{ display: 'inline-flex', alignItems: 'center', gap: 0.5 }}>
                  {row.icon && (
                    <Box component="span" aria-hidden sx={{ display: 'flex', '& svg': { fontSize: 16 } }}>
                      {row.icon}
                    </Box>
                  )}
                  {row.label}
                </Box>
              </th>
              <td>{row.cell(checkpoint)}</td>
              <td>{hourly ? row.cell(hourly) : UNAVAILABLE}</td>
            </tr>
          ))}
        </tbody>
      </Box>
      {!hourly && (
        <Typography variant="caption" component="p" sx={{ mt: 1, fontWeight: 700 }}>
          No forecast for +{hour} h at this checkpoint, so its risk at that hour is unknown.
        </Typography>
      )}
    </Box>
  )
}
