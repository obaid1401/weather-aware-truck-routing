import Box from '@mui/material/Box'
import type { ReactNode } from 'react'

import { tokens } from '../theme/theme'

/** The page frame: a skip link and the main landmark. The page lays out its own header so the
 * map can use the full height of the window. */
export function AppShell({ children }: { children: ReactNode }) {
  return (
    <>
      <Box
        component="a"
        href="#main"
        sx={{
          position: 'absolute',
          left: 8,
          top: -48,
          zIndex: 2000,
          px: 2,
          py: 1,
          bgcolor: tokens.shieldBlue,
          color: '#fff',
          fontWeight: 700,
          borderRadius: 1,
          textDecoration: 'none',
          '&:focus': { top: 8 },
        }}
      >
        Skip to trip planner
      </Box>
      <Box component="main" id="main" tabIndex={-1} sx={{ outline: 'none' }}>
        {children}
      </Box>
    </>
  )
}
