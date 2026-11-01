import Alert from '@mui/material/Alert'
import Box from '@mui/material/Box'
import { useTheme } from '@mui/material/styles'
import Tab from '@mui/material/Tab'
import Tabs from '@mui/material/Tabs'
import Typography from '@mui/material/Typography'
import useMediaQuery from '@mui/material/useMediaQuery'
import { useEffect, useRef, useState } from 'react'

import type { TripAnalysisResponse } from '../../features/analysis/types/api'
import { CheckpointDetails } from '../../features/checkpoints/components/CheckpointDetails'
import { CheckpointList } from '../../features/checkpoints/components/CheckpointList'
import { BaseMap } from '../../features/map/components/BaseMap'
import { RouteMap } from '../../features/map/components/RouteMap'
import { AnalysisSummary } from '../../features/recommendation/components/AnalysisSummary'
import { RouteComparison } from '../../features/routing/components/RouteComparison'
import { forecastHourTime } from '../../features/weather/services/hourlyForecast'
import { visuallyHidden } from '../../shared/utils/visuallyHidden'
import { ForecastPanel } from './ForecastPanel'
import { Column, MapFrame, Panel, Stage } from './workspace'

type ResultsTab = 'routes' | 'checkpoints'

/** One analysis: the map with its forecast panel, and the verdict, route comparison, and
 * checkpoints beside it. Selecting a route, checkpoint, or forecast hour only changes what is
 * displayed: the analysis is never re-requested and its ranking never changes. */
export function AnalysisResults({ analysis }: { analysis: TripAnalysisResponse }) {
  const { routes, recommendation, trip } = analysis
  const [selectedRouteId, setSelectedRouteId] = useState(
    () => recommendation?.recommended_route_id ?? routes[0]?.id ?? '',
  )
  const [selectedCheckpointId, setSelectedCheckpointId] = useState<string | null>(null)
  const [hour, setHour] = useState(0)
  const [tab, setTab] = useState<ResultsTab>('routes')
  const theme = useTheme()
  // The forecast panel floats over the bottom of the map on wide screens: keep routes clear of it.
  const panelOverMap = useMediaQuery(theme.breakpoints.up('md'))
  const panelBesideStrip = useMediaQuery(theme.breakpoints.up('lg'))
  const revealDetails = useRef(false)

  useEffect(() => {
    if (!revealDetails.current || tab !== 'checkpoints') return
    revealDetails.current = false
    const reduceMotion = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches
    document
      .getElementById('checkpoint-details')
      ?.scrollIntoView?.({ block: 'start', behavior: reduceMotion ? 'auto' : 'smooth' })
  }, [selectedCheckpointId, tab])

  const route = routes.find((r) => r.id === selectedRouteId) ?? routes[0]
  if (!route) {
    return (
      <>
        <Stage label="Route map">
          <MapFrame>
            <BaseMap />
          </MapFrame>
        </Stage>
        <Column area="results">
          <Panel>
            <Alert severity="info">The analysis returned no routes to display.</Alert>
          </Panel>
        </Column>
      </>
    )
  }

  const checkpoint = route.checkpoints.find((c) => c.id === selectedCheckpointId) ?? null
  const hourTime = forecastHourTime(route.checkpoints, trip.departure_time, hour)

  const selectRoute = (routeId: string) => {
    if (routeId === route.id) return
    setSelectedRouteId(routeId)
    // Checkpoints belong to one route.
    setSelectedCheckpointId(null)
  }
  // Choosing a checkpoint on the map or the strip opens its details and brings them into view.
  const selectCheckpoint = (checkpointId: string) => {
    setSelectedCheckpointId(checkpointId)
    setTab('checkpoints')
    revealDetails.current = true
  }

  return (
    <>
      {/* First in the document so keyboard order matches the stacked layout on small screens. */}
      <Stage label="Route map">
        <Typography variant="h2" id="route-map-title" sx={visuallyHidden}>
          Map: {route.label}
        </Typography>
        <MapFrame>
          <RouteMap
            routes={routes}
            origin={analysis.origin}
            destination={analysis.destination}
            selectedRouteId={route.id}
            selectedCheckpointId={checkpoint?.id ?? null}
            hour={hour}
            checkpointIntervalMiles={trip.checkpoint_interval_miles}
            bottomInset={panelOverMap ? (panelBesideStrip ? 240 : 340) : 24}
            onSelectRoute={selectRoute}
            onSelectCheckpoint={selectCheckpoint}
          />
        </MapFrame>
        <ForecastPanel
          route={route}
          hour={hour}
          hourTime={hourTime}
          onHourChange={setHour}
          selectedCheckpointId={checkpoint?.id ?? null}
          onSelectCheckpoint={selectCheckpoint}
        />
      </Stage>

      <Column area="results">
        <Panel>
          <AnalysisSummary analysis={analysis} />
        </Panel>

        <Panel padding={false}>
          <Tabs
            value={tab}
            onChange={(_event, value: ResultsTab) => setTab(value)}
            variant="fullWidth"
            aria-label="Result details"
            sx={{ px: 1, borderBottom: 1, borderColor: 'divider' }}
          >
            <Tab
              value="routes"
              label={`Routes (${routes.length})`}
              id="results-tab-routes"
              aria-controls="results-panel-routes"
            />
            <Tab
              value="checkpoints"
              label={`Checkpoints (${route.checkpoints.length})`}
              id="results-tab-checkpoints"
              aria-controls="results-panel-checkpoints"
            />
          </Tabs>

          <Box
            role="tabpanel"
            id={`results-panel-${tab}`}
            aria-labelledby={`results-tab-${tab}`}
            sx={{ p: { xs: 2, sm: 2.5 } }}
          >
            {tab === 'routes' ? (
              <RouteComparison
                routes={routes}
                recommendation={recommendation}
                selectedRouteId={route.id}
                onSelectRoute={selectRoute}
              />
            ) : (
              <Box component="section" aria-labelledby="checkpoints-title">
                <Typography variant="h2" id="checkpoints-title" sx={{ mb: 2 }}>
                  Checkpoints on {route.label}
                </Typography>
                <Box
                  component="aside"
                  id="checkpoint-details"
                  aria-label="Checkpoint details"
                  // Clear of the sticky header when scrolled into view.
                  sx={{ mb: 3, scrollMarginTop: 80 }}
                >
                  <CheckpointDetails
                    checkpoints={route.checkpoints}
                    checkpoint={checkpoint}
                    hour={hour}
                    hourTime={hourTime}
                  />
                </Box>
                <CheckpointList
                  checkpoints={route.checkpoints}
                  selectedCheckpointId={checkpoint?.id ?? null}
                  onSelectCheckpoint={setSelectedCheckpointId}
                />
              </Box>
            )}
          </Box>
        </Panel>
      </Column>
    </>
  )
}
