import AccessTimeIcon from '@mui/icons-material/AccessTime'
import CheckCircleIcon from '@mui/icons-material/CheckCircle'
import FlagOutlinedIcon from '@mui/icons-material/FlagOutlined'
import StraightenIcon from '@mui/icons-material/Straighten'
import WarningAmberIcon from '@mui/icons-material/WarningAmber'
import Box from '@mui/material/Box'
import Button from '@mui/material/Button'
import Typography from '@mui/material/Typography'
import type { ReactNode } from 'react'

import type { AnalyzedRoute, Recommendation } from '../../analysis/types/api'
import { RISK_DISPLAY } from '../../risk/services/riskDisplay'
import { tokens } from '../../../shared/theme/theme'
import {
  formatDuration,
  formatMiles,
  formatPercent,
  formatShortDateTime,
} from '../../../shared/utils/format'
import { rankedRoutes, type RankedRoute } from '../services/rankedRoutes'
import { RouteRiskBar } from './RouteRiskBar'

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

/** Every route side by side, in the backend's ranked order. Selecting a route shows it on the
 * map; it never changes the ranking. */
export function RouteComparison({
  routes,
  recommendation,
  selectedRouteId,
  onSelectRoute,
}: RouteComparisonProps) {
  const ranked = rankedRoutes(routes, recommendation)
  const total = recommendation?.ranked_route_ids.length ?? 0

  return (
    <Box component="section" aria-labelledby="route-comparison-title">
      <Typography variant="h2" id="route-comparison-title">
        Compare routes
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5, mb: 2 }}>
        Safest first: ranked by severe-risk miles, then high-risk miles, average risk, and travel
        time, using the forecast at each checkpoint’s estimated arrival.
      </Typography>
      <Box sx={{ display: 'grid', gap: 1.5 }}>
        {ranked.map((item) => (
          <RouteCard
            key={item.route.id}
            item={item}
            status={statusLabel(item, total)}
            selected={item.route.id === selectedRouteId}
            onSelect={() => onSelectRoute(item.route.id)}
          />
        ))}
      </Box>
    </Box>
  )
}

function Fact({ icon, label, value, wide = false }: { icon: ReactNode; label: string; value: string; wide?: boolean }) {
  return (
    <Box
      sx={{
        display: 'flex',
        gap: 0.75,
        alignItems: 'flex-start',
        minWidth: 0,
        // On phones the arrival time gets a row of its own.
        gridColumn: wide ? { xs: '1 / -1', sm: 'auto' } : undefined,
      }}
    >
      <Box
        component="span"
        aria-hidden
        sx={{ display: 'flex', pt: 0.25, color: tokens.steel, '& svg': { fontSize: 18 } }}
      >
        {icon}
      </Box>
      <Box sx={{ minWidth: 0 }}>
        <Box
          component="span"
          sx={{ display: 'block', typography: 'caption', color: 'text.secondary', lineHeight: 1.2 }}
        >
          {label}
        </Box>
        <Box component="span" sx={{ display: 'block', fontWeight: 700, fontSize: '0.9375rem' }}>
          {value}
        </Box>
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
  const { route, isRecommended, reason, rank } = item
  const { metrics } = route
  const titleId = `route-card-${route.id}`
  const noTravel = metrics.no_travel_miles > 0

  const stats: { term: string; value: ReactNode }[] = [
    { term: 'Severe-risk miles', value: formatMiles(metrics.severe_miles) },
    { term: 'High-risk miles', value: formatMiles(metrics.high_miles) },
    {
      term: 'No-travel miles',
      value: noTravel ? (
        <Box
          component="span"
          sx={{ color: RISK_DISPLAY.NO_TRAVEL.color, display: 'inline-flex', gap: 0.5, alignItems: 'center' }}
        >
          <WarningAmberIcon sx={{ fontSize: 16 }} aria-hidden />
          {formatMiles(metrics.no_travel_miles)}
        </Box>
      ) : (
        formatMiles(0)
      ),
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
    stats.push({ term: 'Unknown-risk miles', value: formatMiles(metrics.unknown_miles) })
  }

  return (
    // The whole card is a mouse target; the button is the keyboard and screen-reader control.
    <Box
      component="article"
      aria-labelledby={titleId}
      onClick={onSelect}
      sx={{
        cursor: 'pointer',
        p: 2,
        borderRadius: '10px',
        border: 2,
        borderColor: selected ? tokens.shieldBlue : tokens.rule,
        bgcolor: selected ? tokens.selectedTint : tokens.paper,
        transition: 'border-color 150ms, background-color 150ms',
        '&:hover': selected ? undefined : { borderColor: '#b4c4d8' },
      }}
    >
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, flexWrap: 'wrap', mb: 1.5 }}>
        <Typography variant="h3" component="h3" id={titleId} sx={{ fontSize: '1.0625rem', fontWeight: 800 }}>
          {route.label}
        </Typography>
        <Box
          component="span"
          sx={{
            px: 1,
            py: 0.25,
            borderRadius: 999,
            typography: 'caption',
            fontWeight: 700,
            bgcolor: isRecommended ? tokens.shieldBlue : '#e8edf3',
            color: isRecommended ? '#fff' : 'text.secondary',
          }}
        >
          {status}
        </Box>
        <Button
          size="small"
          variant={selected ? 'text' : 'outlined'}
          aria-pressed={selected}
          aria-label={`Show ${route.label} on the map`}
          startIcon={selected ? <CheckCircleIcon /> : undefined}
          onClick={(event) => {
            event.stopPropagation()
            onSelect()
          }}
          sx={{ ml: 'auto' }}
        >
          {selected ? 'On the map' : 'Show on map'}
        </Button>
      </Box>

      {/* Distance and time are short; the arrival time gets the rest of the row. */}
      <Box
        sx={{
          display: 'grid',
          gridTemplateColumns: { xs: 'repeat(2, minmax(0, 1fr))', sm: 'auto auto minmax(0, 1fr)' },
          columnGap: 2,
          rowGap: 1,
          mb: 1.5,
        }}
      >
        <Fact icon={<StraightenIcon />} label="Distance" value={formatMiles(route.distance_miles)} />
        <Fact icon={<AccessTimeIcon />} label="Travel time" value={formatDuration(route.duration_seconds)} />
        <Fact
          icon={<FlagOutlinedIcon />}
          label="Estimated arrival"
          value={formatShortDateTime(route.estimated_arrival_time)}
          wide
        />
      </Box>

      <RouteRiskBar metrics={metrics} />

      <Box
        component="dl"
        sx={{
          display: 'grid',
          gridTemplateColumns: 'repeat(3, minmax(0, 1fr))',
          columnGap: 1,
          rowGap: 1,
          m: 0,
          mt: 1.5,
          fontVariantNumeric: 'tabular-nums',
          '& dt': { typography: 'caption', color: 'text.secondary', lineHeight: 1.2 },
          '& dd': { m: 0, typography: 'body2', fontWeight: 700 },
        }}
      >
        {stats.map((stat) => (
          <div key={stat.term}>
            <dt>{stat.term}</dt>
            <dd>{stat.value}</dd>
          </div>
        ))}
      </Box>

      {/* The recommended route's reason is already in the verdict. */}
      {selected && reason && !isRecommended && (
        <Box sx={{ mt: 1.5, pt: 1.5, borderTop: 1, borderColor: tokens.rule }}>
          <Typography variant="subtitle2" component="h4">
            Why {route.label} is rank {rank}
          </Typography>
          <Typography variant="body2" color="text.secondary">
            {reason}
          </Typography>
        </Box>
      )}
    </Box>
  )
}
