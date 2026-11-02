import PlaceOutlinedIcon from '@mui/icons-material/PlaceOutlined'
import Autocomplete from '@mui/material/Autocomplete'
import Box from '@mui/material/Box'
import CircularProgress from '@mui/material/CircularProgress'
import TextField from '@mui/material/TextField'
import { useState, type Ref } from 'react'

import type { GeocodedLocation } from '../../analysis/types/api'
import { MIN_SUGGESTION_QUERY_LENGTH, useLocationSuggestions } from '../hooks/useLocationSuggestions'
import { MAX_ADDRESS_LENGTH } from '../schemas/tripFormSchema'

interface LocationFieldProps {
  /** Also the input's id and name. */
  field: 'origin' | 'destination'
  label: string
  value: string
  /** Called as the user types. */
  onChange: (value: string) => void
  /** Called when a suggestion is chosen, with the place (its label fills the field). */
  onSelect: (place: GeocodedLocation) => void
  error?: string
  helperText: string
  inputRef: (element: HTMLInputElement | null) => void
}

/** Sets a React ref, whichever form it takes. */
function assignRef<T>(ref: Ref<T> | undefined, value: T | null) {
  if (typeof ref === 'function') ref(value)
  else if (ref) (ref as { current: T | null }).current = value
}

/**
 * An address input that suggests places while the user types. The user can choose a suggestion
 * (mouse, or arrow keys and Enter; Escape closes the list) or keep their own text: the form sends
 * whatever the field contains, as before. Pressing Enter with no suggestion highlighted submits
 * the form.
 */
export function LocationField({
  field,
  label,
  value,
  onChange,
  onSelect,
  error,
  helperText,
  inputRef,
}: LocationFieldProps) {
  const [listOpen, setListOpen] = useState(false)
  const typedEnough = value.trim().length >= MIN_SUGGESTION_QUERY_LENGTH
  const { places, loading, failed } = useLocationSuggestions(value, listOpen && typedEnough)

  const emptyText = failed
    ? 'Suggestions are unavailable right now. You can still type the full address.'
    : 'No matching places. Check the spelling, or type the full address.'

  return (
    <Autocomplete<GeocodedLocation, false, false, false>
      id={field}
      options={places}
      // The backend already matched the text; show its order unchanged.
      filterOptions={(options) => options}
      getOptionLabel={(place) => place.label}
      getOptionKey={(place) => `${place.label}-${place.latitude}-${place.longitude}`}
      isOptionEqualToValue={(place, other) => place.label === other.label}
      // Nothing stays "selected": the text field is the value, as for any typed address.
      value={null}
      inputValue={value}
      onInputChange={(_event, text, reason) => {
        if (reason === 'input') onChange(text)
      }}
      onChange={(_event, place) => {
        if (place) onSelect(place)
      }}
      open={listOpen && typedEnough}
      onOpen={() => setListOpen(true)}
      onClose={() => setListOpen(false)}
      loading={loading}
      loadingText="Finding places…"
      noOptionsText={emptyText}
      forcePopupIcon={false}
      clearOnBlur={false}
      handleHomeEndKeys={false}
      renderOption={(props, place) => {
        const { key, ...optionProps } = props as typeof props & { key: string }
        const [name, ...rest] = place.label.split(', ')
        return (
          <Box component="li" key={key} {...optionProps} sx={{ display: 'flex', gap: 1.25, alignItems: 'flex-start' }}>
            <PlaceOutlinedIcon fontSize="small" sx={{ mt: 0.25, color: 'text.secondary' }} aria-hidden />
            <Box component="span" sx={{ minWidth: 0 }}>
              <Box component="span" sx={{ display: 'block', fontWeight: 700 }}>
                {name}
              </Box>
              {rest.length > 0 && (
                <Box component="span" sx={{ display: 'block', typography: 'caption', color: 'text.secondary' }}>
                  {rest.join(', ')}
                </Box>
              )}
            </Box>
          </Box>
        )
      }}
      renderInput={(params) => (
        <TextField
          {...params}
          name={field}
          label={label}
          error={Boolean(error)}
          helperText={error ?? helperText}
          required
          fullWidth
          slotProps={{
            ...params.slotProps,
            input: {
              ...params.slotProps.input,
              // Replaces the clear button: the spinner while suggestions load, otherwise nothing.
              endAdornment: loading ? (
                <CircularProgress color="inherit" size={18} aria-hidden sx={{ mr: 1 }} />
              ) : null,
            },
            htmlInput: {
              ...params.slotProps.htmlInput,
              maxLength: MAX_ADDRESS_LENGTH,
              // Keep both the Autocomplete's ref and the form's (used to focus invalid fields).
              ref: (element: HTMLInputElement | null) => {
                assignRef(params.slotProps.htmlInput.ref as Ref<HTMLInputElement>, element)
                inputRef(element)
              },
            },
          }}
        />
      )}
    />
  )
}
