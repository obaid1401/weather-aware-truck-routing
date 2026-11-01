import AppBar from '@mui/material/AppBar'
import Box from '@mui/material/Box'
import Container from '@mui/material/Container'
import Toolbar from '@mui/material/Toolbar'
import Typography from '@mui/material/Typography'
import type { ReactNode } from 'react'

export function AppShell({ children }: { children: ReactNode }) {
  return (
    <Box sx={{ minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
      <AppBar position="static" color="primary">
        <Toolbar>
          <Typography variant="h1" component="h1">
            Weather-Aware Truck Routing
          </Typography>
        </Toolbar>
      </AppBar>
      <Container component="main" maxWidth="lg" sx={{ flex: 1, py: { xs: 3, md: 5 } }}>
        {children}
      </Container>
      <Box component="footer" sx={{ py: 2, textAlign: 'center' }}>
        <Typography variant="caption" color="text.secondary">
          Forecast-based estimates for planning, not live conditions. Routing by Valhalla,
          geocoding by OpenRouteService, weather by Open-Meteo.
        </Typography>
      </Box>
    </Box>
  )
}
