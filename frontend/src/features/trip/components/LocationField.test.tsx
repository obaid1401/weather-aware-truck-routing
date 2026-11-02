import { ThemeProvider } from '@mui/material/styles'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { useState } from 'react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { theme } from '../../../shared/theme/theme'
import { suggestLocations } from '../api/suggestLocations'
import { LocationField } from './LocationField'

vi.mock('../api/suggestLocations', () => ({ suggestLocations: vi.fn() }))
const mockedSuggest = vi.mocked(suggestLocations)

const DENVER = { label: 'Denver, CO, USA', latitude: 39.741, longitude: -104.986 }
const DENVILLE = { label: 'Denville, NJ, USA', latitude: 40.892, longitude: -74.477 }

/** Places passed to onSelect, in order. */
let selected: (typeof DENVER)[] = []

beforeEach(() => {
  mockedSuggest.mockReset().mockResolvedValue([DENVER, DENVILLE])
  selected = []
})

/** Origin and destination fields with their own state, like the trip form. */
function Fields() {
  const [origin, setOrigin] = useState('')
  const [destination, setDestination] = useState('')
  return (
    <>
      <LocationField
        field="origin"
        label="Origin"
        value={origin}
        onChange={setOrigin}
        onSelect={(place) => {
          selected.push(place)
          setOrigin(place.label)
        }}
        helperText="City, address, or place."
        inputRef={() => {}}
      />
      <LocationField
        field="destination"
        label="Destination"
        value={destination}
        onChange={setDestination}
        onSelect={(place) => {
          selected.push(place)
          setDestination(place.label)
        }}
        helperText="City, address, or place."
        inputRef={() => {}}
      />
    </>
  )
}

function renderFields() {
  render(
    <QueryClientProvider client={new QueryClient()}>
      <ThemeProvider theme={theme}>
        <Fields />
      </ThemeProvider>
    </QueryClientProvider>,
  )
  return userEvent.setup()
}

const origin = () => screen.getByRole('combobox', { name: /origin/i })
const destination = () => screen.getByRole('combobox', { name: /destination/i })
const queries = () => mockedSuggest.mock.calls.map(([query]) => query)

describe('LocationField', () => {
  it('suggests places once typing pauses, with one request for the whole word', async () => {
    const user = renderFields()

    await user.type(origin(), 'Denv')

    const list = await screen.findByRole('listbox')
    expect(within(list).getAllByRole('option').map((o) => o.textContent)).toEqual([
      'DenverCO, USA',
      'DenvilleNJ, USA',
    ])
    expect(queries()).toEqual(['Denv'])
    expect(origin()).toHaveAttribute('aria-expanded', 'true')
  })

  it('does not ask for suggestions before the third character', async () => {
    const user = renderFields()

    await user.type(origin(), 'De')
    await new Promise((resolve) => setTimeout(resolve, 400))

    expect(mockedSuggest).not.toHaveBeenCalled()
    expect(screen.queryByRole('listbox')).not.toBeInTheDocument()
  })

  it('fills the field when a suggestion is clicked', async () => {
    const user = renderFields()
    await user.type(origin(), 'Denv')

    await user.click(await screen.findByRole('option', { name: /Denville/ }))

    expect(origin()).toHaveValue('Denville, NJ, USA')
    // The whole place, with its coordinates, is passed on.
    expect(selected).toEqual([DENVILLE])
    expect(screen.queryByRole('listbox')).not.toBeInTheDocument()
  })

  it('selects a suggestion with the arrow keys and Enter', async () => {
    const user = renderFields()
    await user.type(origin(), 'Denv')
    await screen.findByRole('listbox')

    await user.keyboard('{ArrowDown}{ArrowDown}{Enter}')

    expect(origin()).toHaveValue('Denville, NJ, USA')
  })

  it('closes the list with Escape and keeps the typed text', async () => {
    const user = renderFields()
    await user.type(origin(), 'Denv')
    await screen.findByRole('listbox')

    await user.keyboard('{Escape}')

    expect(screen.queryByRole('listbox')).not.toBeInTheDocument()
    expect(origin()).toHaveValue('Denv')
  })

  it('shows a loading state while suggestions are on their way', async () => {
    mockedSuggest.mockReturnValue(new Promise(() => {}))
    const user = renderFields()

    await user.type(origin(), 'Denv')

    expect(await screen.findByText('Finding places…')).toBeInTheDocument()
  })

  it('says when nothing matches', async () => {
    mockedSuggest.mockResolvedValue([])
    const user = renderFields()

    await user.type(origin(), 'Qzxw')

    expect(
      await screen.findByText('No matching places. Check the spelling, or type the full address.'),
    ).toBeInTheDocument()
  })

  it('says when suggestions are unavailable, and the typed text still stands', async () => {
    mockedSuggest.mockRejectedValue(new Error('Network Error'))
    const user = renderFields()

    await user.type(origin(), 'Denv')

    expect(
      await screen.findByText(
        'Suggestions are unavailable right now. You can still type the full address.',
      ),
    ).toBeInTheDocument()
    expect(origin()).toHaveValue('Denv')
  })

  it('handles origin and destination independently', async () => {
    mockedSuggest.mockImplementation(async (query) =>
      query.startsWith('Salt') ? [{ label: 'Salt Lake City, UT, USA', latitude: 40.76, longitude: -111.89 }] : [DENVER],
    )
    const user = renderFields()

    await user.type(origin(), 'Denv')
    await user.click(await screen.findByRole('option', { name: /Denver/ }))
    await user.type(destination(), 'Salt')
    await user.click(await screen.findByRole('option', { name: /Salt Lake City/ }))

    expect(origin()).toHaveValue('Denver, CO, USA')
    expect(destination()).toHaveValue('Salt Lake City, UT, USA')
    await waitFor(() => expect(queries()).toEqual(['Denv', 'Salt']))
  })
})
