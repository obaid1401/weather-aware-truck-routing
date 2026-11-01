import Alert from '@mui/material/Alert'
import AlertTitle from '@mui/material/AlertTitle'
import Box from '@mui/material/Box'
import Button from '@mui/material/Button'
import Chip from '@mui/material/Chip'
import CircularProgress from '@mui/material/CircularProgress'
import FormControl from '@mui/material/FormControl'
import FormControlLabel from '@mui/material/FormControlLabel'
import FormHelperText from '@mui/material/FormHelperText'
import FormLabel from '@mui/material/FormLabel'
import InputAdornment from '@mui/material/InputAdornment'
import LinearProgress from '@mui/material/LinearProgress'
import Radio from '@mui/material/Radio'
import RadioGroup from '@mui/material/RadioGroup'
import Stack from '@mui/material/Stack'
import TextField from '@mui/material/TextField'
import Typography from '@mui/material/Typography'
import { useRef, useState, type FormEvent } from 'react'

import type { ApiProblem, TripField } from '../../analysis/services/apiProblem'
import {
  CHECKPOINT_INTERVALS_MILES,
  type CheckpointIntervalMiles,
  type TripAnalysisRequest,
} from '../../analysis/types/api'
import { parseLocalInputValue, toLocalInputValue, utcOffset } from '../../../shared/utils/datetime'
import {
  MAX_ADDRESS_LENGTH,
  initialTripFormValues,
  validateTripForm,
  type TripFormErrors,
  type TripFormValues,
} from '../schemas/tripFormSchema'

interface TripFormProps {
  onSubmit: (request: TripAnalysisRequest) => void
  isSubmitting: boolean
  /** The last failed submission, if any. Field errors and candidates are shown inline. */
  problem: ApiProblem | null
  /** Injectable clock, for tests. */
  now?: () => Date
}

/** Field order, used to focus the first invalid field. */
const FIELD_ORDER: TripField[] = [
  'origin',
  'destination',
  'departure_time',
  'load_weight_lbs',
  'checkpoint_interval_miles',
]

const VALUE_FOR_FIELD: Record<TripField, keyof TripFormValues> = {
  origin: 'origin',
  destination: 'destination',
  departure_time: 'departureLocal',
  load_weight_lbs: 'loadWeightLbs',
  checkpoint_interval_miles: 'checkpointIntervalMiles',
}

export function TripForm({ onSubmit, isSubmitting, problem, now = () => new Date() }: TripFormProps) {
  const [values, setValues] = useState<TripFormValues>(() => initialTripFormValues(now()))
  const [clientErrors, setClientErrors] = useState<TripFormErrors>({})
  // Server errors for a field are hidden once the user edits that field. Tracked per problem,
  // so a new response shows its errors again.
  const [edited, setEdited] = useState<{ problem: ApiProblem | null; fields: Set<TripField> }>({
    problem: null,
    fields: new Set(),
  })
  const fieldRefs = useRef<Partial<Record<TripField, HTMLElement | null>>>({})

  const editedFields = edited.problem === problem ? edited.fields : new Set<TripField>()

  const errorFor = (field: TripField): string | undefined =>
    clientErrors[field] ?? (editedFields.has(field) ? undefined : problem?.fieldErrors[field])

  const update = <K extends keyof TripFormValues>(key: K, value: TripFormValues[K]) => {
    setValues((current) => ({ ...current, [key]: value }))
    const field = FIELD_ORDER.find((f) => VALUE_FOR_FIELD[f] === key)
    if (!field) return
    setClientErrors((current) => {
      const next = { ...current }
      delete next[field]
      return next
    })
    setEdited((current) => ({
      problem,
      fields: new Set([...(current.problem === problem ? current.fields : []), field]),
    }))
  }

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (isSubmitting) return
    const { errors, request } = validateTripForm(values, now())
    setClientErrors(errors)
    if (!request) {
      const first = FIELD_ORDER.find((field) => errors[field])
      if (first) fieldRefs.current[first]?.focus()
      return
    }
    onSubmit(request)
  }

  const chooseCandidate = (field: 'origin' | 'destination', label: string) => {
    update(field, label)
    fieldRefs.current[field]?.focus()
  }

  const departureDate = parseLocalInputValue(values.departureLocal)
  const offsetHint = `Your local time (UTC${utcOffset(departureDate ?? now())}).`

  const candidatesFor = (field: 'origin' | 'destination') =>
    problem?.ambiguity?.field === field && !editedFields.has(field) ? (
      <Box sx={{ mt: 1 }}>
        <Typography variant="body2" id={`${field}-candidates-label`} sx={{ mb: 0.5 }}>
          Did you mean:
        </Typography>
        <Stack
          direction="row"
          useFlexGap
          sx={{ flexWrap: 'wrap', gap: 1 }}
          role="group"
          aria-labelledby={`${field}-candidates-label`}
        >
          {problem.ambiguity.candidates.map((candidate) => (
            <Chip
              key={`${candidate.label}-${candidate.latitude}-${candidate.longitude}`}
              label={candidate.label}
              onClick={() => chooseCandidate(field, candidate.label)}
              aria-label={`Use ${candidate.label} as the ${field}`}
              variant="outlined"
              color="primary"
            />
          ))}
        </Stack>
      </Box>
    ) : null

  const addressField = (field: 'origin' | 'destination', label: string, example: string) => (
    <Box>
      <TextField
        id={field}
        name={field}
        label={label}
        value={values[field]}
        onChange={(event) => update(field, event.target.value)}
        error={Boolean(errorFor(field))}
        helperText={errorFor(field) ?? `City, address, or place. For example: ${example}.`}
        required
        fullWidth
        autoComplete="off"
        inputRef={(element: HTMLInputElement | null) => {
          fieldRefs.current[field] = element
        }}
        slotProps={{ htmlInput: { maxLength: MAX_ADDRESS_LENGTH } }}
      />
      {candidatesFor(field)}
    </Box>
  )

  const showProblemAlert = problem && !isSubmitting

  return (
    <Box
      component="form"
      noValidate
      onSubmit={handleSubmit}
      aria-busy={isSubmitting}
      aria-labelledby="trip-form-title"
    >
      <Typography variant="h2" id="trip-form-title" gutterBottom>
        Plan a trip
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
        Compare truck routes by distance, travel time, and the weather forecast along each one.
      </Typography>

      <Stack spacing={2.5}>
        {addressField('origin', 'Origin', 'Denver, CO')}
        {addressField('destination', 'Destination', 'Salt Lake City, UT')}

        <TextField
          id="departure_time"
          name="departure_time"
          label="Departure date and time"
          type="datetime-local"
          value={values.departureLocal}
          onChange={(event) => update('departureLocal', event.target.value)}
          error={Boolean(errorFor('departure_time'))}
          helperText={errorFor('departure_time') ?? offsetHint}
          required
          fullWidth
          inputRef={(element: HTMLInputElement | null) => {
            fieldRefs.current.departure_time = element
          }}
          slotProps={{
            inputLabel: { shrink: true },
            htmlInput: { min: toLocalInputValue(now()), step: 60 },
          }}
        />

        <TextField
          id="load_weight_lbs"
          name="load_weight_lbs"
          label="Cargo weight"
          value={values.loadWeightLbs}
          onChange={(event) => update('loadWeightLbs', event.target.value)}
          error={Boolean(errorFor('load_weight_lbs'))}
          helperText={
            errorFor('load_weight_lbs') ?? 'Cargo only, in pounds. Heavy loads tighten wind limits.'
          }
          required
          fullWidth
          autoComplete="off"
          inputRef={(element: HTMLInputElement | null) => {
            fieldRefs.current.load_weight_lbs = element
          }}
          slotProps={{
            htmlInput: { inputMode: 'decimal' },
            input: { endAdornment: <InputAdornment position="end">lb</InputAdornment> },
          }}
        />

        <FormControl error={Boolean(errorFor('checkpoint_interval_miles'))}>
          <FormLabel id="checkpoint-interval-label">Weather checkpoint interval</FormLabel>
          <RadioGroup
            row
            name="checkpoint_interval_miles"
            aria-labelledby="checkpoint-interval-label"
            aria-describedby="checkpoint-interval-help"
            value={String(values.checkpointIntervalMiles)}
            onChange={(event) =>
              update(
                'checkpointIntervalMiles',
                Number(event.target.value) as CheckpointIntervalMiles,
              )
            }
          >
            {CHECKPOINT_INTERVALS_MILES.map((miles) => (
              <FormControlLabel
                key={miles}
                value={String(miles)}
                control={<Radio />}
                label={`${miles} miles`}
              />
            ))}
          </RadioGroup>
          <FormHelperText id="checkpoint-interval-help">
            {errorFor('checkpoint_interval_miles') ??
              'Weather is checked at the origin, at every interval, and at the destination.'}
          </FormHelperText>
        </FormControl>

        {showProblemAlert && (
          <Alert severity="error">
            <AlertTitle>{problem.title}</AlertTitle>
            {problem.message}
            {problem.retryAfterSeconds !== null &&
              ` You can try again in ${problem.retryAfterSeconds} seconds.`}
          </Alert>
        )}

        <Button
          type="submit"
          variant="contained"
          size="large"
          fullWidth
          disabled={isSubmitting}
          startIcon={isSubmitting ? <CircularProgress size={18} color="inherit" aria-hidden /> : null}
        >
          {isSubmitting ? 'Analyzing routes…' : 'Analyze routes'}
        </Button>

        <Box role="status" aria-live="polite">
          {isSubmitting && (
            <Box>
              <LinearProgress aria-label="Analysis in progress" />
              <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                Finding truck routes and checking the weather along each one. This usually
                takes 10 to 20 seconds.
              </Typography>
            </Box>
          )}
        </Box>
      </Stack>
    </Box>
  )
}
