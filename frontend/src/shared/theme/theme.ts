import { createTheme } from '@mui/material/styles'

// System fonts: fast, and no request to an external font service.
const FONT_FAMILY = [
  'system-ui',
  '-apple-system',
  '"Segoe UI"',
  'Roboto',
  '"Helvetica Neue"',
  'Arial',
  'sans-serif',
].join(',')

export const theme = createTheme({
  palette: {
    mode: 'light',
    // Deep blue and amber: high contrast on white (primary text 8:1+), calm, and distinct
    // from the risk colours used for weather data.
    primary: { main: '#1d4f7a', dark: '#143a5a', light: '#4a7aa6', contrastText: '#ffffff' },
    secondary: { main: '#b45309', contrastText: '#ffffff' },
    background: { default: '#f4f6f9', paper: '#ffffff' },
    text: { primary: '#1a2230', secondary: '#4a5568' },
  },
  shape: { borderRadius: 8 },
  typography: {
    fontFamily: FONT_FAMILY,
    h1: { fontSize: '1.25rem', fontWeight: 700, letterSpacing: '-0.01em' },
    h2: { fontSize: '1.375rem', fontWeight: 700, letterSpacing: '-0.01em', lineHeight: 1.3 },
    h3: { fontSize: '1.125rem', fontWeight: 600, lineHeight: 1.4 },
    button: { textTransform: 'none', fontWeight: 600 },
    overline: { fontWeight: 600, letterSpacing: '0.06em' },
  },
  components: {
    MuiButton: { defaultProps: { disableElevation: true } },
    MuiPaper: { defaultProps: { elevation: 0 } },
    MuiAlert: { styleOverrides: { root: { alignItems: 'flex-start' } } },
  },
})
