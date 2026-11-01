import Box from '@mui/material/Box'
import type { ReactNode } from 'react'

import { tokens } from '../../shared/theme/theme'

// Page layout. On wide screens a column of panels sits on the left and the map fills the rest
// of the window below the header, staying in view while the panels scroll. On narrow screens
// everything stacks: header, trip, map, then results.

export const HEADER_HEIGHT = 64

/** The grid. Its children place themselves with `gridArea`. */
export function Workspace({ children }: { children: ReactNode }) {
  return (
    <Box
      sx={{
        display: 'grid',
        minHeight: '100dvh',
        gridTemplateColumns: {
          xs: 'minmax(0, 1fr)',
          md: '400px minmax(0, 1fr)',
          lg: '460px minmax(0, 1fr)',
        },
        gridTemplateRows: { md: `${HEADER_HEIGHT}px auto 1fr auto` },
        gridTemplateAreas: {
          xs: '"header" "trip" "stage" "results" "notes"',
          md: '"header header" "trip stage" "results stage" "notes stage"',
        },
        bgcolor: tokens.canvas,
      }}
    >
      {children}
    </Box>
  )
}

/** The navy bar across the top. Stays in place on wide screens so the map always fits below. */
export function Header({ children }: { children: ReactNode }) {
  return (
    <Box
      component="header"
      sx={{
        gridArea: 'header',
        position: { md: 'sticky' },
        top: 0,
        zIndex: 1100,
        height: HEADER_HEIGHT,
        display: 'flex',
        alignItems: 'center',
        gap: 1.5,
        px: { xs: 2, sm: 3 },
        bgcolor: tokens.navy,
        color: '#fff',
      }}
    >
      {children}
    </Box>
  )
}

/** A white, rounded panel. */
export function Panel({
  children,
  labelledBy,
  label,
  padding = true,
}: {
  children: ReactNode
  labelledBy?: string
  label?: string
  padding?: boolean
}) {
  return (
    <Box
      component="section"
      aria-labelledby={labelledBy}
      aria-label={label}
      sx={{
        bgcolor: tokens.paper,
        borderRadius: `${tokens.radius}px`,
        boxShadow: tokens.shadow,
        p: padding ? { xs: 2, sm: 2.5 } : 0,
        minWidth: 0,
      }}
    >
      {children}
    </Box>
  )
}

/** One area of the left column: holds panels with even spacing. */
export function Column({ area, children }: { area: 'trip' | 'results' | 'notes'; children: ReactNode }) {
  return (
    <Box
      sx={{
        gridArea: area,
        minWidth: 0,
        display: 'grid',
        gap: 2,
        alignContent: 'start',
        px: { xs: 1.5, sm: 2 },
        pt: area === 'results' ? { xs: 2, md: 0 } : area === 'notes' ? 0 : 2,
        pb: area === 'notes' ? 3 : 2,
      }}
    >
      {children}
    </Box>
  )
}

/** The map area: the window height below the header and in view on wide screens; a block of
 * fixed height when stacked. */
export function Stage({ children, label }: { children: ReactNode; label: string }) {
  return (
    <Box
      component="section"
      aria-label={label}
      sx={{
        gridArea: 'stage',
        minWidth: 0,
        position: { xs: 'relative', md: 'sticky' },
        top: { md: HEADER_HEIGHT },
        height: { md: `calc(100dvh - ${HEADER_HEIGHT}px)` },
        display: 'flex',
        flexDirection: 'column',
      }}
    >
      {children}
    </Box>
  )
}

/** The map itself inside a Stage. */
export function MapFrame({ children }: { children: ReactNode }) {
  return (
    <Box
      sx={{
        position: 'relative',
        flex: { md: 1 },
        height: { xs: '60vh', md: 'auto' },
        minHeight: { xs: 340, md: 0 },
        maxHeight: { xs: 560, md: 'none' },
        minWidth: 0,
        '& .leaflet-container': { fontFamily: 'inherit' },
      }}
    >
      {children}
    </Box>
  )
}

/** A short message card floating over the map. */
export function MapNotice({ children }: { children: ReactNode }) {
  return (
    <Box
      sx={{
        position: 'absolute',
        left: 16,
        right: 16,
        bottom: 32,
        mx: 'auto',
        maxWidth: 420,
        zIndex: 1000,
        display: 'flex',
        gap: 1.5,
        alignItems: 'center',
        px: 2,
        py: 1.5,
        bgcolor: tokens.paper,
        borderRadius: `${tokens.radius}px`,
        boxShadow: tokens.shadow,
        typography: 'body2',
      }}
    >
      {children}
    </Box>
  )
}
