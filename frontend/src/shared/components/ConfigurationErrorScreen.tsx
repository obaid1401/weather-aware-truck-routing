import Alert from '@mui/material/Alert'
import AlertTitle from '@mui/material/AlertTitle'
import Container from '@mui/material/Container'
import CssBaseline from '@mui/material/CssBaseline'
import { ThemeProvider } from '@mui/material/styles'

import { theme } from '../theme/theme'

/** Shown instead of the app when required configuration is missing. */
export function ConfigurationErrorScreen({ message }: { message: string }) {
  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <Container maxWidth="sm" sx={{ py: 8 }}>
        <Alert severity="error">
          <AlertTitle>The app is not configured</AlertTitle>
          {message}
        </Alert>
      </Container>
    </ThemeProvider>
  )
}
