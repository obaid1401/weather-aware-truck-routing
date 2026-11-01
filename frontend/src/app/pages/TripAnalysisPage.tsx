import LocalShippingOutlinedIcon from '@mui/icons-material/LocalShippingOutlined'
import MapOutlinedIcon from '@mui/icons-material/MapOutlined'
import Box from '@mui/material/Box'
import CircularProgress from '@mui/material/CircularProgress'
import Collapse from '@mui/material/Collapse'
import Typography from '@mui/material/Typography'
import { useState } from 'react'

import { useAnalyzeTrip } from '../../features/analysis/hooks/useAnalyzeTrip'
import { BaseMap } from '../../features/map/components/BaseMap'
import { TripForm } from '../../features/trip/components/TripForm'
import { TripSummary } from '../../features/trip/components/TripSummary'
import { tokens } from '../../shared/theme/theme'
import { visuallyHidden } from '../../shared/utils/visuallyHidden'
import { AnalysisResults } from './AnalysisResults'
import { Column, Header, MapFrame, MapNotice, Panel, Stage, Workspace } from './workspace'

const TRIP_FORM_ID = 'trip-form'

export function TripAnalysisPage() {
  const analysis = useAnalyzeTrip()
  const result = analysis.isSuccess ? analysis.data : null
  // After an analysis the form folds into a summary; "Edit trip" opens it for that analysis.
  const [editingAnalysisAt, setEditingAnalysisAt] = useState<number | null>(null)
  const formOpen = !result || editingAnalysisAt === analysis.submittedAt

  return (
    <Workspace>
      <Header>
        <Box
          aria-hidden
          sx={{
            display: 'grid',
            placeItems: 'center',
            width: 36,
            height: 36,
            borderRadius: '10px',
            bgcolor: tokens.shieldBlue,
          }}
        >
          <LocalShippingOutlinedIcon sx={{ fontSize: 22 }} />
        </Box>
        <Box sx={{ minWidth: 0 }}>
          <Typography variant="h1">Weather-Aware Truck Routing</Typography>
          <Typography
            variant="caption"
            sx={{ display: { xs: 'none', sm: 'block' }, color: 'rgba(255, 255, 255, 0.72)' }}
          >
            Pick the safest route from the forecast along the way
          </Typography>
        </Box>
      </Header>

      <Column area="trip">
        <Panel label="Trip">
          {result && !formOpen && (
            <TripSummary
              trip={result.trip}
              origin={result.origin}
              destination={result.destination}
              formId={TRIP_FORM_ID}
              onEdit={() => setEditingAnalysisAt(analysis.submittedAt)}
            />
          )}
          {/* Kept mounted while folded, so the entered values are never lost. */}
          <Collapse
            in={formOpen}
            id={TRIP_FORM_ID}
            onEntered={() => {
              if (result) document.getElementById('origin')?.focus()
            }}
          >
            <TripForm
              onSubmit={(request) => analysis.mutate(request)}
              isSubmitting={analysis.isPending}
              problem={analysis.error}
            />
          </Collapse>
        </Panel>
      </Column>

      {result ? (
        // A new analysis starts with fresh selections.
        <AnalysisResults key={analysis.submittedAt} analysis={result} />
      ) : (
        <Stage label="Route map">
          <MapFrame>
            <BaseMap />
            <MapNotice>
              {analysis.isPending ? (
                <CircularProgress size={22} aria-hidden />
              ) : (
                <MapOutlinedIcon sx={{ color: tokens.shieldBlue }} aria-hidden />
              )}
              <span>
                {analysis.isPending
                  ? 'Finding truck routes and checking the forecast along each one…'
                  : 'Your routes, checkpoints, and the weather along them will appear here.'}
              </span>
            </MapNotice>
          </MapFrame>
        </Stage>
      )}

      <Column area="notes">
        <Typography variant="caption" color="text.secondary" component="p" sx={{ px: 1 }}>
          Forecast-based estimates for planning, not live conditions. Routing by Valhalla,
          geocoding by OpenRouteService, weather by Open-Meteo, map data by OpenStreetMap.
        </Typography>
      </Column>

      <Box role="status" sx={visuallyHidden}>
        {result &&
          `Analysis ready: ${result.routes.length} ${result.routes.length === 1 ? 'route' : 'routes'} compared.`}
      </Box>
    </Workspace>
  )
}
