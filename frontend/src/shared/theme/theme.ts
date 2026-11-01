import { createTheme } from '@mui/material/styles'

// Overpass is an open-source typeface derived from Highway Gothic, the lettering on US road
// signs. Self-hosted (SIL Open Font License, see fonts/OFL.txt): no request to a font service.
import overpassUrl from './fonts/overpass-latin-wght.woff2'

const FONT_FAMILY = [
  'Overpass',
  'system-ui',
  '-apple-system',
  '"Segoe UI"',
  'Roboto',
  'sans-serif',
].join(',')

/** Interface colours. Risk colours are kept separately (features/risk) and used only for risk,
 * so no interface colour can be mistaken for a risk level. */
export const tokens = {
  ink: '#172b3d',
  steel: '#5a6b7d',
  /** The interaction colour: buttons, focus, selection, and the selected route line. */
  shieldBlue: '#1662c4',
  shieldBlueDark: '#0f4a96',
  /** The header bar. */
  navy: '#0d2847',
  /** The page behind the panels and the map. */
  canvas: '#eef2f7',
  paper: '#ffffff',
  rule: '#dfe5ec',
  /** Light tint of shieldBlue for selected items. */
  selectedTint: '#eaf2fd',
  /** Panel shadow: soft and low, so panels lift off the canvas without looking heavy. */
  shadow: '0 1px 2px rgba(13, 40, 71, 0.06), 0 6px 20px rgba(13, 40, 71, 0.08)',
  radius: 12,
} as const

export const theme = createTheme({
  palette: {
    mode: 'light',
    primary: {
      main: tokens.shieldBlue,
      dark: tokens.shieldBlueDark,
      light: '#4b8be0',
      contrastText: '#ffffff',
    },
    background: { default: tokens.canvas, paper: tokens.paper },
    text: { primary: tokens.ink, secondary: tokens.steel },
    divider: tokens.rule,
  },
  shape: { borderRadius: 8 },
  typography: {
    fontFamily: FONT_FAMILY,
    h1: { fontSize: '1.125rem', fontWeight: 800, letterSpacing: '-0.01em', lineHeight: 1.2 },
    h2: { fontSize: '1.25rem', fontWeight: 800, letterSpacing: '-0.01em', lineHeight: 1.25 },
    h3: { fontSize: '1rem', fontWeight: 700, lineHeight: 1.3 },
    subtitle2: { fontSize: '0.875rem', fontWeight: 700, lineHeight: 1.35 },
    body1: { fontSize: '1rem', lineHeight: 1.5 },
    body2: { fontSize: '0.875rem', lineHeight: 1.45 },
    caption: { fontSize: '0.8125rem', lineHeight: 1.4 },
    button: { textTransform: 'none', fontWeight: 700, letterSpacing: 0 },
  },
  components: {
    MuiCssBaseline: {
      styleOverrides: `
        @font-face {
          font-family: 'Overpass';
          font-style: normal;
          font-weight: 400 800;
          font-display: swap;
          src: url(${overpassUrl}) format('woff2');
        }
        html { -webkit-text-size-adjust: 100%; }
        body { background: ${tokens.canvas}; }
        h1, h2, h3 { text-wrap: balance; }
        button, a, [role='button'] { touch-action: manipulation; }
        :focus-visible { outline: 2px solid ${tokens.shieldBlue}; outline-offset: 2px; }
        @media (prefers-reduced-motion: reduce) {
          *, *::before, *::after {
            animation-duration: 0.01ms !important;
            animation-iteration-count: 1 !important;
            transition-duration: 0.01ms !important;
            scroll-behavior: auto !important;
          }
        }
      `,
    },
    MuiButtonBase: { defaultProps: { disableRipple: true } },
    MuiButton: {
      defaultProps: { disableElevation: true },
      styleOverrides: {
        root: { minHeight: 40, borderRadius: 8, paddingInline: 16 },
        sizeLarge: { minHeight: 48, fontSize: '1rem' },
        sizeSmall: { minHeight: 32, paddingInline: 12 },
      },
    },
    MuiPaper: { defaultProps: { elevation: 0 } },
    MuiOutlinedInput: {
      styleOverrides: {
        root: { borderRadius: 8, backgroundColor: tokens.paper },
        notchedOutline: { borderColor: '#c9d3de' },
      },
    },
    MuiAlert: { styleOverrides: { root: { alignItems: 'flex-start', borderRadius: 10 } } },
    MuiChip: { styleOverrides: { root: { fontWeight: 700 } } },
    MuiTabs: {
      styleOverrides: {
        root: { minHeight: 44 },
        indicator: { height: 3, borderRadius: 3 },
      },
    },
    MuiTab: {
      styleOverrides: {
        root: { minHeight: 44, textTransform: 'none', fontWeight: 700, fontSize: '0.9375rem' },
      },
    },
    MuiSlider: {
      styleOverrides: {
        root: { height: 6 },
        rail: { opacity: 1, backgroundColor: '#d5deea' },
        track: { border: 0 },
        thumb: {
          width: 22,
          height: 22,
          border: `3px solid ${tokens.paper}`,
          boxShadow: '0 1px 4px rgba(13, 40, 71, 0.35)',
        },
        mark: { height: 6, width: 2, backgroundColor: 'rgba(255, 255, 255, 0.8)' },
        markLabel: { fontSize: '0.8125rem', color: tokens.steel },
      },
    },
  },
})
