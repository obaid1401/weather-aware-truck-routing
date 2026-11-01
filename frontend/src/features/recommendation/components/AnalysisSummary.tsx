import AccessTimeIcon from '@mui/icons-material/AccessTime'
import CheckCircleOutlinedIcon from '@mui/icons-material/CheckCircleOutlined'
import CloudDoneOutlinedIcon from '@mui/icons-material/CloudDoneOutlined'
import FlagOutlinedIcon from '@mui/icons-material/FlagOutlined'
import InfoOutlinedIcon from '@mui/icons-material/InfoOutlined'
import StraightenIcon from '@mui/icons-material/Straighten'
import Alert from '@mui/material/Alert'
import AlertTitle from '@mui/material/AlertTitle'
import Box from '@mui/material/Box'
import Typography from '@mui/material/Typography'
import type { ReactNode } from 'react'

import type { TripAnalysisResponse } from '../../analysis/types/api'
import { tokens } from '../../../shared/theme/theme'
import {
  formatDateTime,
  formatDuration,
  formatMiles,
  formatPercent,
} from '../../../shared/utils/format'
import { visuallyHidden } from '../../../shared/utils/visuallyHidden'

interface AnalysisSummaryProps {
  analysis: TripAnalysisResponse
}

/** One fact in the verdict's description list. The icon sits inside the <dt>, so the list keeps
 * valid dt/dd markup. */
function StatTile({ icon, label, value }: { icon: ReactNode; label: string; value: string }) {
  return (
    <Box
      sx={{ position: 'relative', minWidth: 0, p: 1.5, pl: 7, borderRadius: '10px', bgcolor: tokens.canvas }}
    >
      <Box component="dt" sx={{ typography: 'caption', color: 'text.secondary', lineHeight: 1.2 }}>
        <Box
          component="span"
          aria-hidden
          sx={{
            position: 'absolute',
            left: 12,
            top: 12,
            display: 'grid',
            placeItems: 'center',
            width: 32,
            height: 32,
            borderRadius: '8px',
            bgcolor: tokens.paper,
            color: tokens.shieldBlue,
            '& svg': { fontSize: 18 },
          }}
        >
          {icon}
        </Box>
        {label}
      </Box>
      <Box component="dd" sx={{ m: 0, fontWeight: 800, fontVariantNumeric: 'tabular-nums' }}>
        {value}
      </Box>
    </Box>
  )
}

/** The verdict: the recommended route, why it was chosen, and every safety warning and data
 * limitation from the analysis. */
export function AnalysisSummary({ analysis }: AnalysisSummaryProps) {
  const { recommendation, routes, origin, destination, provider_warnings } = analysis
  const recommended = routes.find((route) => route.id === recommendation?.recommended_route_id)
  const safetyWarnings = recommendation?.warnings ?? []
  const routeCount = `${routes.length} ${routes.length === 1 ? 'route' : 'routes'}`

  return (
    <Box component="section" aria-labelledby="analysis-summary-title">
      {recommendation && recommended ? (
        <>
          <Typography component="h2" sx={{ mb: 0.5 }}>
            <Box
              component="span"
              sx={{ display: 'block', typography: 'body2', fontWeight: 700, color: tokens.shieldBlue }}
            >
              Recommended route
              <Box component="span" sx={visuallyHidden}>
                :
              </Box>
            </Box>{' '}
            <Box
              component="span"
              sx={{ display: 'block', fontSize: '2rem', fontWeight: 800, lineHeight: 1.1, letterSpacing: '-0.02em' }}
            >
              {recommended.label}
            </Box>
          </Typography>
          <Typography variant="body2" color="text.secondary" id="analysis-summary-title" sx={{ mb: 2 }}>
            {routeCount} analyzed from {origin.label} to {destination.label}
          </Typography>

          <Box
            component="dl"
            sx={{ display: 'grid', gridTemplateColumns: 'repeat(2, minmax(0, 1fr))', gap: 1, m: 0, mb: 2 }}
          >
            <StatTile icon={<StraightenIcon />} label="Distance" value={formatMiles(recommended.distance_miles)} />
            <StatTile icon={<AccessTimeIcon />} label="Travel time" value={formatDuration(recommended.duration_seconds)} />
            <StatTile
              icon={<FlagOutlinedIcon />}
              label="Estimated arrival"
              value={formatDateTime(recommended.estimated_arrival_time)}
            />
            <StatTile
              icon={<CloudDoneOutlinedIcon />}
              label="Weather coverage"
              value={formatPercent(recommended.metrics.weather_coverage_percent)}
            />
          </Box>
        </>
      ) : (
        <>
          <Typography variant="h2" component="h2" gutterBottom>
            No route recommended
          </Typography>
          <Typography variant="body2" color="text.secondary" id="analysis-summary-title" sx={{ mb: 2 }}>
            {routeCount} analyzed from {origin.label} to {destination.label}
          </Typography>
          <Alert severity="info">No route could be recommended for this trip.</Alert>
        </>
      )}

      {safetyWarnings.length > 0 ? (
        <Alert severity="warning" variant="filled" sx={{ mb: 2, color: '#3d2600', bgcolor: '#ffcf66' }}>
          <AlertTitle sx={{ fontWeight: 800 }}>Safety warnings</AlertTitle>
          <Box component="ul" sx={{ m: 0, pl: 2.5 }}>
            {safetyWarnings.map((warning, index) => (
              // The backend may repeat a message; the list is fixed for one response.
              <li key={index}>{warning}</li>
            ))}
          </Box>
        </Alert>
      ) : (
        recommendation && (
          <Box sx={{ display: 'flex', gap: 1, alignItems: 'center', mb: 2, typography: 'body2', fontWeight: 600 }}>
            <CheckCircleOutlinedIcon sx={{ fontSize: 20, color: tokens.shieldBlue }} aria-hidden />
            No safety warnings from this analysis.
          </Box>
        )
      )}

      {recommendation && recommended && (
        <Box>
          <Typography variant="subtitle2" component="h3">
            Why this route
          </Typography>
          <Typography variant="body2" color="text.secondary">
            {recommendation.ranking_reasons[0]}
          </Typography>
        </Box>
      )}

      {provider_warnings.length > 0 && (
        <Box
          component="aside"
          aria-labelledby="data-limitations-title"
          sx={{ display: 'flex', gap: 1, mt: 2, p: 1.5, borderRadius: '10px', bgcolor: tokens.canvas }}
        >
          <InfoOutlinedIcon sx={{ fontSize: 20, color: tokens.steel, mt: 0.25 }} aria-hidden />
          <Box>
            <Typography variant="subtitle2" component="h3" id="data-limitations-title">
              Data limitations
            </Typography>
            <Box component="ul" sx={{ m: 0, pl: 2.5, typography: 'body2', color: 'text.secondary' }}>
              {provider_warnings.map((warning, index) => (
                // The backend may repeat a message; the list is fixed for one response.
                <li key={index}>{warning}</li>
              ))}
            </Box>
          </Box>
        </Box>
      )}
    </Box>
  )
}
