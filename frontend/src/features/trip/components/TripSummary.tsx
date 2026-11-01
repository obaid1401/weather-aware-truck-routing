import EditOutlinedIcon from '@mui/icons-material/EditOutlined'
import EventOutlinedIcon from '@mui/icons-material/EventOutlined'
import PlaceOutlinedIcon from '@mui/icons-material/PlaceOutlined'
import ScaleOutlinedIcon from '@mui/icons-material/ScaleOutlined'
import Box from '@mui/material/Box'
import Button from '@mui/material/Button'
import Typography from '@mui/material/Typography'
import type { ReactNode } from 'react'

import type { GeocodedLocation, TripEcho } from '../../analysis/types/api'
import { tokens } from '../../../shared/theme/theme'
import { formatDateTime, formatPounds } from '../../../shared/utils/format'
import { visuallyHidden } from '../../../shared/utils/visuallyHidden'

interface TripSummaryProps {
  trip: TripEcho
  origin: GeocodedLocation
  destination: GeocodedLocation
  onEdit: () => void
  /** The id of the trip form this button reveals. */
  formId: string
}

function Stop({ letter, term, place }: { letter: string; term: string; place: string }) {
  return (
    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.25, position: 'relative', zIndex: 1 }}>
      <Box
        component="span"
        aria-hidden
        sx={{
          display: 'grid',
          placeItems: 'center',
          flexShrink: 0,
          width: 24,
          height: 24,
          borderRadius: '6px',
          bgcolor: tokens.navy,
          color: '#fff',
          fontSize: '0.75rem',
          fontWeight: 800,
        }}
      >
        {letter}
      </Box>
      <Box component="span" sx={{ fontWeight: 700, overflowWrap: 'anywhere' }}>
        <Box component="span" sx={visuallyHidden}>
          {term}:{' '}
        </Box>
        {place}
      </Box>
    </Box>
  )
}

function Pill({ icon, term, value }: { icon: ReactNode; term: string; value: string }) {
  return (
    <Box
      sx={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: 0.75,
        px: 1.25,
        py: 0.5,
        borderRadius: 999,
        bgcolor: tokens.canvas,
        typography: 'body2',
        fontWeight: 600,
      }}
    >
      <Box component="span" aria-hidden sx={{ display: 'flex', color: tokens.steel, '& svg': { fontSize: 16 } }}>
        {icon}
      </Box>
      <span>
        <Box component="span" sx={visuallyHidden}>
          {term}:{' '}
        </Box>
        {value}
      </span>
    </Box>
  )
}

/** The analyzed trip as the backend echoed it, shown in place of the form once results are in. */
export function TripSummary({ trip, origin, destination, onEdit, formId }: TripSummaryProps) {
  return (
    <Box>
      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 2, mb: 2 }}>
        <Typography variant="h2">Your trip</Typography>
        <Button
          variant="outlined"
          size="small"
          startIcon={<EditOutlinedIcon />}
          onClick={onEdit}
          aria-expanded={false}
          aria-controls={formId}
        >
          Edit trip
        </Button>
      </Box>
      <Box>
        {/* The origin-to-destination line. */}
        <Box sx={{ position: 'relative', display: 'grid', gap: 1.5, mb: 2 }}>
          <Box
            aria-hidden
            sx={{ position: 'absolute', left: 11, top: 20, bottom: 20, width: 2, bgcolor: tokens.rule }}
          />
          <Stop letter="A" term="From" place={origin.label} />
          <Stop letter="B" term="To" place={destination.label} />
        </Box>
        <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.75 }}>
          <Pill icon={<EventOutlinedIcon />} term="Departure" value={formatDateTime(trip.departure_time)} />
          <Pill icon={<ScaleOutlinedIcon />} term="Cargo" value={formatPounds(trip.load_weight_lbs)} />
          <Pill
            icon={<PlaceOutlinedIcon />}
            term="Checkpoints"
            value={`Every ${trip.checkpoint_interval_miles} miles`}
          />
        </Box>
      </Box>
    </Box>
  )
}
