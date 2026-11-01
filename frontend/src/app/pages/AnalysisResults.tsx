import Alert from '@mui/material/Alert'
import Box from '@mui/material/Box'
import Divider from '@mui/material/Divider'
import Paper from '@mui/material/Paper'
import Typography from '@mui/material/Typography'
import { useState } from 'react'

import type { TripAnalysisResponse } from '../../features/analysis/types/api'
import { CheckpointDetails } from '../../features/checkpoints/components/CheckpointDetails'
import { CheckpointList } from '../../features/checkpoints/components/CheckpointList'
import { MapKey } from '../../features/map/components/MapKey'
import { RouteMap } from '../../features/map/components/RouteMap'
import { RouteComparison } from '../../features/routing/components/RouteComparison'
import { ForecastSlider } from '../../features/weather/components/ForecastSlider'
import {
  countUnavailableAtHour,
  forecastHourTime,
} from '../../features/weather/services/hourlyForecast'

const panel = { p: { xs: 2, sm: 3 }, border: 1, borderColor: 'divider' } as const

/** Route comparison, map, forecast slider, and checkpoint details for one analysis. Selecting a
 * route, checkpoint, or forecast hour only changes what is displayed: the analysis response is
 * never re-requested, and the backend's ranking is never changed. */
export function AnalysisResults({ analysis }: { analysis: TripAnalysisResponse }) {
  const { routes, recommendation, trip } = analysis
  const [selectedRouteId, setSelectedRouteId] = useState(
    () => recommendation?.recommended_route_id ?? routes[0]?.id ?? '',
  )
  const [selectedCheckpointId, setSelectedCheckpointId] = useState<string | null>(null)
  const [hour, setHour] = useState(0)

  const route = routes.find((r) => r.id === selectedRouteId) ?? routes[0]
  if (!route) {
    return <Alert severity="info">The analysis returned no routes to display.</Alert>
  }

  const checkpoint = route.checkpoints.find((c) => c.id === selectedCheckpointId) ?? null
  const hourTime = forecastHourTime(route.checkpoints, trip.departure_time, hour)

  const selectRoute = (routeId: string) => {
    if (routeId === route.id) return
    setSelectedRouteId(routeId)
    // Checkpoints belong to one route.
    setSelectedCheckpointId(null)
  }

  return (
    <Box sx={{ display: 'grid', gap: { xs: 3, md: 4 } }}>
      <Paper sx={panel}>
        <RouteComparison
          routes={routes}
          recommendation={recommendation}
          selectedRouteId={route.id}
          onSelectRoute={selectRoute}
        />
      </Paper>

      <Box
        sx={{
          display: 'grid',
          gap: { xs: 3, md: 4 },
          gridTemplateColumns: { xs: 'minmax(0, 1fr)', md: 'minmax(0, 1fr) 360px' },
          alignItems: 'start',
        }}
      >
        <Paper sx={panel} component="section" aria-labelledby="route-map-title">
          <Typography variant="h2" id="route-map-title" gutterBottom>
            Map: {route.label}
          </Typography>
          <ForecastSlider
            hour={hour}
            time={hourTime}
            onChange={setHour}
            unavailableCount={countUnavailableAtHour(route.checkpoints, hour)}
            checkpointCount={route.checkpoints.length}
          />
          <Box
            sx={{
              height: { xs: 360, sm: 440, md: 520 },
              my: 2,
              borderRadius: 1,
              overflow: 'hidden',
              border: 1,
              borderColor: 'divider',
            }}
          >
            <RouteMap
              routes={routes}
              origin={analysis.origin}
              destination={analysis.destination}
              selectedRouteId={route.id}
              selectedCheckpointId={checkpoint?.id ?? null}
              hour={hour}
              checkpointIntervalMiles={trip.checkpoint_interval_miles}
              onSelectRoute={selectRoute}
              onSelectCheckpoint={setSelectedCheckpointId}
            />
          </Box>
          <MapKey hour={hour} />
        </Paper>

        <Paper sx={panel} component="aside" aria-label="Checkpoint details">
          <CheckpointDetails
            checkpoints={route.checkpoints}
            checkpoint={checkpoint}
            hour={hour}
            hourTime={hourTime}
          />
          <Divider sx={{ my: 2 }} />
          <CheckpointList
            checkpoints={route.checkpoints}
            selectedCheckpointId={checkpoint?.id ?? null}
            onSelectCheckpoint={setSelectedCheckpointId}
          />
        </Paper>
      </Box>
    </Box>
  )
}
