import Box from '@mui/material/Box'
import Typography from '@mui/material/Typography'
import type { ReactNode } from 'react'

import { RiskLegend } from '../../risk/components/RiskLegend'
import { SELECTED_ROUTE_COLOR } from '../services/mapStyles'

function Swatch({ children }: { children: ReactNode }) {
  return (
    <Box component="span" aria-hidden sx={{ display: 'inline-flex', width: 28, justifyContent: 'center', flexShrink: 0 }}>
      {children}
    </Box>
  )
}

/** Explains the map's symbols and the risk colours they use, with text labels for each. */
export function MapKey({ hour }: { hour: number }) {
  const items = [
    {
      swatch: <Box sx={{ width: 24, height: 5, borderRadius: 1, bgcolor: SELECTED_ROUTE_COLOR }} />,
      text: 'Selected route (blue). Grey lines are the other routes; select one to show it.',
    },
    {
      swatch: <Typography variant="caption" sx={{ fontWeight: 700 }}>A B</Typography>,
      text: 'Origin (A) and destination (B).',
    },
    {
      swatch: (
        <Box sx={{ width: 12, height: 12, borderRadius: '50%', bgcolor: '#c62828', border: '2px solid #fff', boxShadow: 1 }} />
      ),
      text: 'Checkpoint marker: risk at the estimated arrival, used for the ranking. Select one for details.',
    },
    {
      swatch: <Box sx={{ width: 22, height: 22, borderRadius: '50%', bgcolor: 'rgba(198, 40, 40, 0.35)' }} />,
      text: `Shaded circle: forecast risk at +${hour} h at one checkpoint. Circles are not blended or interpolated between checkpoints. This is a forecast, not live radar.`,
    },
    {
      swatch: <Box sx={{ width: 22, height: 22, borderRadius: '50%', bgcolor: 'rgba(189, 189, 189, 0.4)', border: '1px dashed #616161' }} />,
      text: 'Grey dashed: forecast unavailable, so the risk is unknown (never shown as low).',
    },
  ]

  return (
    <Box component="section" aria-labelledby="map-key-title" sx={{ display: 'grid', gap: 2 }}>
      <Box>
        <Typography variant="subtitle2" component="h3" id="map-key-title" gutterBottom>
          Map key
        </Typography>
        <Box component="ul" sx={{ listStyle: 'none', m: 0, p: 0, display: 'grid', gap: 0.75 }}>
          {items.map((item) => (
            <Box component="li" key={item.text} sx={{ display: 'flex', gap: 1, alignItems: 'center' }}>
              <Swatch>{item.swatch}</Swatch>
              <Typography variant="caption" color="text.secondary">
                {item.text}
              </Typography>
            </Box>
          ))}
        </Box>
      </Box>
      <RiskLegend title="Risk colours (markers and shaded circles)" />
    </Box>
  )
}
