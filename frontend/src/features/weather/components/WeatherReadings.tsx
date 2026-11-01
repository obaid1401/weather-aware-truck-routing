import Box from '@mui/material/Box'
import Table from '@mui/material/Table'
import TableBody from '@mui/material/TableBody'
import TableCell from '@mui/material/TableCell'
import TableHead from '@mui/material/TableHead'
import TableRow from '@mui/material/TableRow'
import Typography from '@mui/material/Typography'

import type { RiskFields, RiskLevel, WeatherFields } from '../../analysis/types/api'
import { RiskBadge } from '../../risk/components/RiskBadge'
import { DATA_STATUS_LABELS } from '../../risk/services/riskDisplay'
import { formatDateTime } from '../../../shared/utils/format'

const UNAVAILABLE = 'Unavailable'

function reading(value: number | null, digits: number, unit: string): string {
  return value === null ? UNAVAILABLE : `${value.toFixed(digits)} ${unit}`
}

interface WeatherReadingsProps {
  forecast: WeatherFields & RiskFields
  /** Labels the table for screen readers. */
  caption: string
}

/** One forecast as returned by the backend: each value with its factor risk, the final risk,
 * and the forecast time used. Missing values are shown as unavailable, never as zero. */
export function WeatherReadings({ forecast, caption }: WeatherReadingsProps) {
  const rows: { factor: string; value: string; risk: RiskLevel }[] = [
    { factor: 'Wind', value: reading(forecast.wind_speed_mph, 1, 'mph'), risk: forecast.wind_risk },
    {
      factor: 'Rain',
      value: reading(forecast.precipitation_inches_per_hour, 2, 'in/hr'),
      risk: forecast.rain_risk,
    },
    {
      factor: 'Snowfall',
      value: reading(forecast.snowfall_inches_per_hour, 2, 'in/hr'),
      risk: forecast.snow_risk,
    },
  ]

  return (
    <Box>
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
        <Typography variant="body2" sx={{ fontWeight: 600 }}>
          Overall risk
        </Typography>
        <RiskBadge risk={forecast.final_risk} />
      </Box>
      <Table size="small" aria-label={caption} sx={{ '& td, & th': { px: 1 } }}>
        <TableHead>
          <TableRow>
            <TableCell>Factor</TableCell>
            <TableCell>Forecast</TableCell>
            <TableCell>Risk</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {rows.map((row) => (
            <TableRow key={row.factor}>
              <TableCell component="th" scope="row">
                {row.factor}
              </TableCell>
              <TableCell>{row.value}</TableCell>
              <TableCell>
                <RiskBadge risk={row.risk} size="small" />
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
      <Typography variant="caption" color="text.secondary" component="p" sx={{ mt: 1 }}>
        Forecast for{' '}
        {forecast.forecast_timestamp ? formatDateTime(forecast.forecast_timestamp) : UNAVAILABLE} ·
        Data: {DATA_STATUS_LABELS[forecast.data_status]}
      </Typography>
    </Box>
  )
}
