import Box from '@mui/material/Box'
import Paper from '@mui/material/Paper'
import Typography from '@mui/material/Typography'

import { AnalysisSummary } from '../../features/recommendation/components/AnalysisSummary'
import { TripForm } from '../../features/trip/components/TripForm'
import { useAnalyzeTrip } from '../../features/analysis/hooks/useAnalyzeTrip'

const panel = {
  p: { xs: 2.5, sm: 3.5 },
  border: 1,
  borderColor: 'divider',
} as const

export function TripAnalysisPage() {
  const analysis = useAnalyzeTrip()

  return (
    <Box
      sx={{
        display: 'grid',
        gap: { xs: 3, md: 4 },
        gridTemplateColumns: { xs: '1fr', md: 'minmax(320px, 420px) 1fr' },
        alignItems: 'start',
      }}
    >
      <Paper sx={panel}>
        <TripForm
          onSubmit={(request) => analysis.mutate(request)}
          isSubmitting={analysis.isPending}
          problem={analysis.error}
        />
      </Paper>

      <Paper sx={{ ...panel, minHeight: { md: 240 } }} aria-live="polite">
        {analysis.isSuccess ? (
          <AnalysisSummary analysis={analysis.data} />
        ) : (
          <Box sx={{ color: 'text.secondary' }}>
            <Typography variant="h2" color="text.primary" gutterBottom>
              Results
            </Typography>
            <Typography variant="body1">
              {analysis.isPending
                ? 'Analyzing your trip…'
                : 'Enter a trip to see the recommended route, its weather risk, and any safety warnings.'}
            </Typography>
          </Box>
        )}
      </Paper>
    </Box>
  )
}
