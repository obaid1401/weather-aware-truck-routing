import ExpandLessIcon from '@mui/icons-material/ExpandLess'
import InfoOutlinedIcon from '@mui/icons-material/InfoOutlined'
import Box from '@mui/material/Box'
import Button from '@mui/material/Button'
import Popover from '@mui/material/Popover'
import { useEffect, useRef, useState } from 'react'

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
  /** Reports the panel's height in pixels whenever it changes, so the map can keep the routes
   * clear of it. */
  onHeightChange?: (height: number) => void
}

/** Distance from the bottom of the map to the floating panel, leaving the map credits visible. */
export const FLOATING_PANEL_BOTTOM = 30

/** Where the map key opens: above or below its button, whichever has more room, and how tall it
 * may be there. Measured when the key opens, not during render. */
interface KeyPlacement {
  anchor: HTMLElement
  above: boolean
  maxHeight: number
}

const KEY_MARGIN = 16

/** Over the map: the forecast hour (time) beside the strip map of the selected route
 * (distance), with the risk colours and a key to the map that opens as a pop-up. Kept short so
 * the map stays visible. */
export function ForecastPanel({
  route,
  hour,
  hourTime,
  onHourChange,
  selectedCheckpointId,
  onSelectCheckpoint,
  onHeightChange,
}: ForecastPanelProps) {
  const [key, setKey] = useState<KeyPlacement | null>(null)
  const keyOpen = key !== null
  const panel = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const element = panel.current
    if (!element || !onHeightChange || typeof ResizeObserver === 'undefined') return
    const observer = new ResizeObserver(() => onHeightChange(Math.ceil(element.offsetHeight)))
    observer.observe(element)
    return () => observer.disconnect()
  }, [onHeightChange])

  const openKey = (button: HTMLElement) => {
    const rect = button.getBoundingClientRect()
    const spaceAbove = rect.top
    const spaceBelow = window.innerHeight - rect.bottom
    const above = spaceAbove > spaceBelow
    setKey({
      anchor: button,
      above,
      maxHeight: Math.max(160, (above ? spaceAbove : spaceBelow) - 2 * KEY_MARGIN),
    })
  }

  return (
    // Floats over the bottom of the map on wide screens, just above the map credits; sits under
    // the map on narrow screens.
    <Box
      ref={panel}
      sx={{
        position: { md: 'absolute' },
        left: { md: 16 },
        right: { md: 16 },
        bottom: { md: FLOATING_PANEL_BOTTOM },
        zIndex: 1000,
        // On short screens the panel stops at half the map and scrolls, so the map stays usable.
        maxHeight: { md: '50%' },
        overflowY: { md: 'auto' },
        m: { xs: 1.5, md: 0 },
        bgcolor: tokens.paper,
        borderRadius: `${tokens.radius}px`,
        boxShadow: '0 2px 6px rgba(13, 40, 71, 0.12), 0 10px 28px rgba(13, 40, 71, 0.16)',
        px: { xs: 1.5, sm: 2 },
        pt: 1.25,
        pb: 0.75,
      }}
    >
      <Box
        sx={{
          display: 'grid',
          columnGap: { md: 3, lg: 4 },
          rowGap: 1,
          gridTemplateColumns: { xs: 'minmax(0, 1fr)', md: 'minmax(0, 1fr) minmax(0, 1fr)' },
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
          gap: 0.5,
          pt: 0.75,
          borderTop: 1,
          borderColor: 'divider',
        }}
      >
        <RiskScale />
        <Button
          size="small"
          // Opens the key; it closes from the key itself (outside click or Escape).
          onClick={(event) => openKey(event.currentTarget)}
          aria-expanded={keyOpen}
          aria-controls={keyOpen ? 'map-key' : undefined}
          aria-haspopup="dialog"
          startIcon={<InfoOutlinedIcon />}
          endIcon={
            <ExpandLessIcon
              sx={{ transform: keyOpen ? 'rotate(180deg)' : 'none', transition: 'transform 150ms' }}
            />
          }
        >
          How to read the map
        </Button>
      </Box>

      <Popover
        open={keyOpen}
        anchorEl={key?.anchor}
        onClose={() => setKey(null)}
        anchorOrigin={{ vertical: key?.above ? 'top' : 'bottom', horizontal: 'right' }}
        transformOrigin={{ vertical: key?.above ? 'bottom' : 'top', horizontal: 'right' }}
        marginThreshold={KEY_MARGIN}
        slotProps={{
          paper: {
            id: 'map-key',
            role: 'dialog',
            'aria-labelledby': 'map-key-title',
            sx: {
              mt: key?.above ? -1 : 1,
              p: 2,
              width: 560,
              maxWidth: `calc(100vw - ${2 * KEY_MARGIN}px)`,
              maxHeight: key?.maxHeight,
              overflowY: 'auto',
              borderRadius: `${tokens.radius}px`,
              boxShadow: tokens.shadow,
            },
          },
        }}
      >
        <MapKey hour={hour} />
      </Popover>
    </Box>
  )
}
