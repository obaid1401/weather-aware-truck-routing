import WarningAmberIcon from '@mui/icons-material/WarningAmber'
import Box from '@mui/material/Box'
import Button from '@mui/material/Button'
import Card from '@mui/material/Card'
import CardContent from '@mui/material/CardContent'
import Chip from '@mui/material/Chip'
import Typography from '@mui/material/Typography'

import type { AnalyzedRoute, Recommendation } from '../../analysis/types/api'
import {
  formatDateTime,
  formatDuration,
  formatMiles,
  formatPercent,
} from '../../../shared/utils/format'
import { rankedRoutes, type RankedRoute } from '../services/rankedRoutes'

interface RouteComparisonProps {
  routes: AnalyzedRoute[]
  recommendation: Recommendation | null
  selectedRouteId: string
  onSelectRoute: (routeId: string) => void
}

function statusLabel({ rank, isRecommended }: RankedRoute, total: number): string {
  if (isRecommended) return 'Recommended'
  return rank === null ? 'Not ranked' : `Rank ${rank} of ${total}`
}

/** Every route's metrics side by side, in the backend's ranked order. Selecting a card shows
 * that route on the map; it does not change the ranking. */
export function RouteComparison({
  routes,
  recommendation,
  selectedRouteId,
  onSelectRoute,
}: RouteComparisonProps) {
  const ranked = rankedRoutes(routes, recommendation)

  return (
    <Box component="section" aria-labelledby="route-comparison-title">
      <Typography variant="h2" id="route-comparison-title" gutterBottom>
        Route comparison
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
        Ranked by severe-risk miles, then high-risk miles, average risk, and travel time, using the
        forecast at each checkpoint&apos;s estimated arrival. Select a route to show it on the map.
      </Typography>
      <Box
        sx={{
          display: 'grid',
          gap: 2,
          gridTemplateColumns: { xs: '1fr', sm: 'repeat(2, 1fr)', lg: 'repeat(3, 1fr)' },
        }}
      >
        {ranked.map((item) => (
          <RouteCard
            key={item.route.id}
            item={item}
            status={statusLabel(item, recommendation?.ranked_route_ids.length ?? 0)}
            selected={item.route.id === selectedRouteId}
            onSelect={() => onSelectRoute(item.route.id)}
          />
        ))}
      </Box>
    </Box>
  )
}

interface RouteCardProps {
  item: RankedRoute
  status: string
  selected: boolean
  onSelect: () => void
}

function RouteCard({ item, status, selected, onSelect }: RouteCardProps) {
  const { route, isRecommended, reason } = item
  const { metrics } = route
  const titleId = `route-card-${route.id}`

  const facts: { term: string; value: string; emphasis?: boolean }[] = [
    { term: 'Distance', value: formatMiles(route.distance_miles) },
    { term: 'Travel time', value: formatDuration(route.duration_seconds) },
    { term: 'Estimated arrival', value: formatDateTime(route.estimated_arrival_time) },
    { term: 'Severe-risk miles', value: formatMiles(metrics.severe_miles) },
    { term: 'High-risk miles', value: formatMiles(metrics.high_miles) },
    {
      term: 'No-travel miles',
      value: formatMiles(metrics.no_travel_miles),
      emphasis: metrics.no_travel_miles > 0,
    },
    {
      term: 'Average risk',
      value:
        metrics.average_risk_score === null
          ? 'Unavailable'
          : `${metrics.average_risk_score.toFixed(2)} of 5`,
    },
    { term: 'Weather coverage', value: formatPercent(metrics.weather_coverage_percent) },
  ]
  if (metrics.unknown_miles > 0) {
    facts.push({ term: 'Unknown-risk miles', value: formatMiles(metrics.unknown_miles) })
  }

  return (
    // The whole card is a mouse target; the button is the keyboard and screen-reader control.
    <Card
      variant="outlined"
      component="article"
      aria-labelledby={titleId}
      onClick={onSelect}
      sx={{
        cursor: 'pointer',
        borderWidth: 2,
        borderColor: selected ? 'primary.main' : 'divider',
        bgcolor: selected ? 'rgba(29, 79, 122, 0.04)' : 'background.paper',
      }}
    >
      <CardContent>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, flexWrap: 'wrap', mb: 1.5 }}>
          <Typography variant="h3" component="h3" id={titleId}>
            {route.label}
          </Typography>
          <Chip
            size="small"
            label={status}
            color={isRecommended ? 'primary' : 'default'}
            variant={isRecommended ? 'filled' : 'outlined'}
          />
          <Button
            size="small"
            variant={selected ? 'contained' : 'outlined'}
            aria-pressed={selected}
            aria-label={`Show ${route.label} on the map`}
            onClick={(event) => {
              event.stopPropagation()
              onSelect()
            }}
            sx={{ ml: 'auto' }}
          >
            {selected ? 'Shown on map' : 'Show on map'}
          </Button>
        </Box>

        {metrics.no_travel_miles > 0 && (
          <Box
            role="note"
            sx={{
              display: 'flex',
              gap: 1,
              alignItems: 'center',
              mb: 1.5,
              px: 1,
              py: 0.5,
              borderRadius: 1,
              bgcolor: '#f3e5f5',
              color: '#4a148c',
              typography: 'body2',
              fontWeight: 600,
            }}
          >
            <WarningAmberIcon fontSize="small" aria-hidden />
            No-travel conditions on {formatMiles(metrics.no_travel_miles)}
          </Box>
        )}

        <Box
          component="dl"
          sx={{
            display: 'grid',
            gridTemplateColumns: '1fr 1fr',
            columnGap: 2,
            rowGap: 1,
            m: 0,
            '& dt': { color: 'text.secondary', typography: 'caption' },
            '& dd': { m: 0, typography: 'body2', fontWeight: 600 },
          }}
        >
          {facts.map((fact) => (
            <div key={fact.term}>
              <dt>{fact.term}</dt>
              <Box component="dd" sx={fact.emphasis ? { color: '#4a148c' } : undefined}>
                {fact.value}
              </Box>
            </div>
          ))}
        </Box>

        {reason && (
          <Typography variant="body2" color="text.secondary" sx={{ mt: 1.5 }}>
            {reason}
          </Typography>
        )}
      </CardContent>
    </Card>
  )
}
