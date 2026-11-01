import ExpandMoreIcon from '@mui/icons-material/ExpandMore'
import Box from '@mui/material/Box'
import Button from '@mui/material/Button'
import Collapse from '@mui/material/Collapse'
import { useState } from 'react'

import type { AnalyzedRoute } from '../../features/analysis/types/api'
import { RouteStrip } from '../../features/checkpoints/components/RouteStrip'
import { MapKey } from '../../features/map/components/MapKey'
import { RiskScale } from '../../features/risk/components/RiskScale'
import { ForecastSlider } from '../../features/weather/components/ForecastSlider'
import { countUnavailableAtHour } from '../../features/weather/services/hourlyForecast'
import { tokens } from '../../shared/theme/theme'

interface ForecastPanelProps {
  route: AnalyzedRoute
  hour: number
  hourTime: string
  onHourChange: (hour: number) => void
  selectedCheckpointId: string | null
  onSelectCheckpoint: (checkpointId: string) => void
}

/** Under the map: the forecast hour (time) beside the strip map of the selected route
 * (distance), then the risk colours and a full key to the map. */
export function ForecastPanel({
  route,
  hour,
  hourTime,
  onHourChange,
  selectedCheckpointId,
  onSelectCheckpoint,
}: ForecastPanelProps) {
  const [keyOpen, setKeyOpen] = useState(false)

  return (
    // Floats over the bottom of the map on wide screens, just above the map credits; sits under
    // the map on narrow screens.
    <Box
      sx={{
        position: { md: 'absolute' },
        left: { md: 16 },
        right: { md: 16 },
        bottom: { md: 30 },
        zIndex: 1000,
        maxHeight: { md: '62%' },
        overflowY: { md: 'auto' },
        m: { xs: 1.5, md: 0 },
        bgcolor: tokens.paper,
        borderRadius: `${tokens.radius}px`,
        boxShadow: '0 2px 6px rgba(13, 40, 71, 0.12), 0 12px 32px rgba(13, 40, 71, 0.18)',
        px: { xs: 2, sm: 2.5 },
        pt: 2,
        pb: 1.5,
      }}
    >
      <Box
        sx={{
          display: 'grid',
          gap: { xs: 2.5, lg: 4 },
          gridTemplateColumns: { xs: 'minmax(0, 1fr)', lg: 'minmax(0, 1fr) minmax(0, 1fr)' },
          alignItems: 'start',
        }}
      >
        <ForecastSlider
          hour={hour}
          time={hourTime}
          onChange={onHourChange}
          unavailableCount={countUnavailableAtHour(route.checkpoints, hour)}
          checkpointCount={route.checkpoints.length}
        />
        <RouteStrip
          routeLabel={route.label}
          checkpoints={route.checkpoints}
          distanceMiles={route.distance_miles}
          hour={hour}
          selectedCheckpointId={selectedCheckpointId}
          onSelectCheckpoint={onSelectCheckpoint}
        />
      </Box>

      <Box
        sx={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          flexWrap: 'wrap',
          gap: 1,
          mt: 1.5,
          pt: 1.5,
          borderTop: 1,
          borderColor: 'divider',
        }}
      >
        <RiskScale />
        <Button
          size="small"
          onClick={() => setKeyOpen((open) => !open)}
          aria-expanded={keyOpen}
          aria-controls="map-key"
          endIcon={
            <ExpandMoreIcon
              sx={{ transform: keyOpen ? 'rotate(180deg)' : 'none', transition: 'transform 150ms' }}
            />
          }
        >
          How to read the map
        </Button>
      </Box>
      <Collapse in={keyOpen} id="map-key">
        <Box sx={{ pt: 1.5 }}>
          <MapKey hour={hour} />
        </Box>
      </Collapse>
    </Box>
  )
}
