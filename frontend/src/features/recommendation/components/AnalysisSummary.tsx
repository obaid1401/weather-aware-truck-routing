import Alert from '@mui/material/Alert'
import AlertTitle from '@mui/material/AlertTitle'
import Box from '@mui/material/Box'
import Divider from '@mui/material/Divider'
import Stack from '@mui/material/Stack'
import Typography from '@mui/material/Typography'

import type { TripAnalysisResponse } from '../../analysis/types/api'
import { formatDateTime, formatDuration, formatMiles, formatPercent } from '../../../shared/utils/format'

interface AnalysisSummaryProps {
  analysis: TripAnalysisResponse
}

/** The recommendation and every warning from a completed analysis. Detailed route comparison
 * and the map are added in the results view. */
export function AnalysisSummary({ analysis }: AnalysisSummaryProps) {
  const { recommendation, routes, origin, destination, provider_warnings } = analysis
  const recommended = routes.find((route) => route.id === recommendation?.recommended_route_id)
  const routeCount = `${routes.length} ${routes.length === 1 ? 'route' : 'routes'}`
  const safetyWarnings = recommendation?.warnings ?? []
  const hasWarnings = safetyWarnings.length > 0 || provider_warnings.length > 0

  return (
    <Stack spacing={3} component="section" aria-labelledby="analysis-summary-title">
      <Box>
        <Typography variant="overline" color="text.secondary">
          {routeCount} analyzed
        </Typography>
        <Typography variant="h2" id="analysis-summary-title">
          {origin.label} to {destination.label}
        </Typography>
      </Box>

      {recommendation && recommended ? (
        <Box>
          <Typography variant="h3" gutterBottom>
            Recommended: {recommended.label}
          </Typography>
          <Box
            component="dl"
            sx={{
              display: 'grid',
              gridTemplateColumns: { xs: '1fr 1fr', sm: 'repeat(4, auto)' },
              gap: 2,
              m: 0,
              mb: 2,
              '& dt': { color: 'text.secondary', typography: 'body2' },
              '& dd': { m: 0, typography: 'subtitle1', fontWeight: 600 },
            }}
          >
            <div>
              <dt>Distance</dt>
              <dd>{formatMiles(recommended.distance_miles)}</dd>
            </div>
            <div>
              <dt>Travel time</dt>
              <dd>{formatDuration(recommended.duration_seconds)}</dd>
            </div>
            <div>
              <dt>Estimated arrival</dt>
              <dd>{formatDateTime(recommended.estimated_arrival_time)}</dd>
            </div>
            <div>
              <dt>Weather coverage</dt>
              <dd>{formatPercent(recommended.metrics.weather_coverage_percent)}</dd>
            </div>
          </Box>
          <Typography variant="body1">{recommendation.ranking_reasons[0]}</Typography>
        </Box>
      ) : (
        <Alert severity="info">No route could be recommended for this trip.</Alert>
      )}

      {hasWarnings && <Divider />}

      {safetyWarnings.length > 0 && (
        <Alert severity="warning">
          <AlertTitle>Safety warnings</AlertTitle>
          <Box component="ul" sx={{ m: 0, pl: 2.5 }}>
            {safetyWarnings.map((warning, index) => (
              // The backend may repeat a message; the list is fixed for one response.
              <li key={index}>{warning}</li>
            ))}
          </Box>
        </Alert>
      )}

      {provider_warnings.length > 0 && (
        <Alert severity="info">
          <AlertTitle>Data limitations</AlertTitle>
          <Box component="ul" sx={{ m: 0, pl: 2.5 }}>
            {provider_warnings.map((warning, index) => (
              // The backend may repeat a message; the list is fixed for one response.
              <li key={index}>{warning}</li>
            ))}
          </Box>
        </Alert>
      )}
    </Stack>
  )
}
