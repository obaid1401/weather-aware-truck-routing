import { ThemeProvider } from '@mui/material/styles'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import type { ReactNode } from 'react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import type { ApiProblem } from '../../analysis/services/apiProblem'
import { theme } from '../../../shared/theme/theme'
import { suggestLocations } from '../api/suggestLocations'
import { TripForm } from './TripForm'

// Suggestions are covered in LocationField.test.tsx; here they just return nothing.
vi.mock('../api/suggestLocations', () => ({ suggestLocations: vi.fn() }))
beforeEach(() => {
  vi.mocked(suggestLocations).mockReset().mockResolvedValue([])
})

const NOW = new Date(2026, 10, 3, 10, 15) // 2026-11-03 10:15 America/Denver (MST, -07:00)

function problem(changes: Partial<ApiProblem>): ApiProblem {
  return {
    code: 'X',
    title: 'Title',
    message: 'Message.',
    status: 400,
    fieldErrors: {},
    ambiguity: null,
    retryAfterSeconds: null,
    ...changes,
  }
}

function renderForm(props: Partial<Parameters<typeof TripForm>[0]> = {}) {
  const onSubmit = vi.fn()
  const queryClient = new QueryClient()
  const wrap = (children: ReactNode) => (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider theme={theme}>{children}</ThemeProvider>
    </QueryClientProvider>
  )
  const view = render(
    wrap(<TripForm onSubmit={onSubmit} isSubmitting={false} problem={null} now={() => NOW} {...props} />),
  )
  const rerender = (next: Partial<Parameters<typeof TripForm>[0]>) =>
    view.rerender(
      wrap(
        <TripForm onSubmit={onSubmit} isSubmitting={false} problem={null} now={() => NOW} {...props} {...next} />,
      ),
    )
  return { onSubmit, rerender, user: userEvent.setup() }
}

// The address inputs suggest places, so they are comboboxes.
const origin = () => screen.getByRole('combobox', { name: /origin/i })
const destination = () => screen.getByRole('combobox', { name: /destination/i })
const departure = () => screen.getByLabelText(/departure date and time/i)
const weight = () => screen.getByRole('textbox', { name: /cargo weight/i })
const submit = () => screen.getByRole('button', { name: /analyze routes/i })

async function fillValidTrip(user: ReturnType<typeof userEvent.setup>) {
  await user.type(origin(), 'Denver, CO')
  await user.type(destination(), 'Salt Lake City, UT')
  await user.type(weight(), '36000')
}

describe('fields and defaults', () => {
  it('labels every field and starts with sensible defaults', () => {
    renderForm()

    expect(origin()).toHaveValue('')
    expect(origin()).toBeRequired()
    expect(destination()).toBeRequired()
    expect(departure()).toHaveValue('2026-11-03T11:00') // the next whole hour
    expect(departure()).toHaveAttribute('min', '2026-11-03T10:15')
    expect(weight()).toBeRequired()
    expect(screen.getByRole('radio', { name: '25 miles' })).toBeChecked()
    expect(screen.getByRole('radio', { name: '10 miles' })).not.toBeChecked()
    expect(screen.getByRole('radio', { name: '50 miles' })).not.toBeChecked()
    expect(screen.getByText('Your local time (UTC-07:00).')).toBeInTheDocument()
  })
})

describe('submitting', () => {
  it('sends the exact API request for a valid trip', async () => {
    const { onSubmit, user } = renderForm()
    await fillValidTrip(user)
    fireEvent.change(departure(), { target: { value: '2026-11-05T08:00' } })
    await user.click(screen.getByRole('radio', { name: '10 miles' }))

    await user.click(submit())

    expect(onSubmit).toHaveBeenCalledExactlyOnceWith({
      origin: 'Denver, CO',
      destination: 'Salt Lake City, UT',
      departure_time: '2026-11-05T08:00:00-07:00',
      load_weight_lbs: 36000,
      checkpoint_interval_miles: 10,
    })
  })

  it('sends a chosen place suggestion as the address', async () => {
    vi.mocked(suggestLocations).mockImplementation(async (query) =>
      query.startsWith('Salt')
        ? [{ label: 'Salt Lake City, UT, USA', latitude: 40.76, longitude: -111.89 }]
        : [{ label: 'Denver, CO, USA', latitude: 39.74, longitude: -104.99 }],
    )
    const { onSubmit, user } = renderForm()
    await user.type(origin(), 'Denv')
    await user.click(await screen.findByRole('option', { name: /Denver/ }))
    await user.type(destination(), 'Salt')
    await screen.findByRole('option', { name: /Salt Lake City/ })
    await user.keyboard('{ArrowDown}{Enter}')
    await user.type(weight(), '36000')

    await user.click(submit())

    expect(onSubmit).toHaveBeenCalledExactlyOnceWith(
      expect.objectContaining({
        origin: 'Denver, CO, USA',
        origin_coordinates: { latitude: 39.74, longitude: -104.99 },
        destination: 'Salt Lake City, UT, USA',
        destination_coordinates: { latitude: 40.76, longitude: -111.89 },
      }),
    )
  })

  it('forgets a chosen place once its address is edited', async () => {
    vi.mocked(suggestLocations).mockResolvedValue([
      { label: 'Denver, CO, USA', latitude: 39.74, longitude: -104.99 },
    ])
    const { onSubmit, user } = renderForm()
    await user.type(origin(), 'Denv')
    await user.click(await screen.findByRole('option', { name: /Denver/ }))
    // Edit the chosen address, then type it back exactly: it is typed text now.
    await user.type(origin(), '{Backspace}A')
    await user.keyboard('{Escape}')
    await user.type(destination(), 'Salt Lake City, UT')
    await user.keyboard('{Escape}')
    await user.type(weight(), '36000')

    await user.click(submit())

    const [request] = onSubmit.mock.calls[0]
    expect(request.origin).toBe('Denver, CO, USA')
    expect(request).not.toHaveProperty('origin_coordinates')
    expect(request).not.toHaveProperty('destination_coordinates')
  })

  it('accepts an empty truck (0 lb)', async () => {
    const { onSubmit, user } = renderForm()
    await user.type(origin(), 'Denver, CO')
    await user.type(destination(), 'Salt Lake City, UT')
    await user.type(weight(), '0')

    await user.click(submit())

    expect(onSubmit).toHaveBeenCalledExactlyOnceWith(expect.objectContaining({ load_weight_lbs: 0 }))
  })

  it('rejects a negative weight', async () => {
    const { onSubmit, user } = renderForm()
    await fillValidTrip(user)
    await user.clear(weight())
    await user.type(weight(), '-1')

    await user.click(submit())

    expect(onSubmit).not.toHaveBeenCalled()
    expect(screen.getByText('Enter 0 or more pounds, for example 36000 or 36,000.')).toBeInTheDocument()
  })

  it('still submits with Enter when no suggestion is highlighted', async () => {
    const { onSubmit, user } = renderForm()
    await fillValidTrip(user)

    await user.type(origin(), '{Enter}')

    expect(onSubmit).toHaveBeenCalledOnce()
  })

  it('shows every validation error inline and focuses the first invalid field', async () => {
    const { onSubmit, user } = renderForm()
    fireEvent.change(departure(), { target: { value: '2026-11-03T09:00' } })

    await user.click(submit())

    expect(onSubmit).not.toHaveBeenCalled()
    expect(screen.getByText('Enter the origin.')).toBeInTheDocument()
    expect(screen.getByText('Enter the destination.')).toBeInTheDocument()
    expect(screen.getByText('Choose a departure time in the future.')).toBeInTheDocument()
    expect(screen.getByText('Enter the cargo weight in pounds.')).toBeInTheDocument()
    expect(origin()).toHaveAttribute('aria-invalid', 'true')
    expect(origin()).toHaveFocus()
  })

  it('clears a field error as soon as that field is edited', async () => {
    const { user } = renderForm()
    await user.click(submit())

    await user.type(origin(), 'D')

    expect(screen.queryByText('Enter the origin.')).not.toBeInTheDocument()
    expect(screen.getByText('Enter the destination.')).toBeInTheDocument()
  })

  it('does not submit again while an analysis is running', async () => {
    const { onSubmit, user } = renderForm({ isSubmitting: true })
    await fillValidTrip(user)

    const busy = screen.getByRole('button', { name: /analyzing routes/i })
    expect(busy).toBeDisabled()
    fireEvent.submit(busy.closest('form')!)

    expect(onSubmit).not.toHaveBeenCalled()
    expect(screen.getByRole('status')).toHaveTextContent(/usually takes 10 to 20 seconds/i)
  })
})

describe('backend problems', () => {
  it('shows backend field errors inline and hides them once the field is edited', async () => {
    const { user } = renderForm({
      problem: problem({
        code: 'VALIDATION_ERROR',
        title: 'Please check the highlighted fields',
        message: 'The request is invalid.',
        fieldErrors: { departure_time: 'Departure time must not be in the past.' },
      }),
    })

    expect(screen.getByText('Departure time must not be in the past.')).toBeInTheDocument()
    expect(screen.getByRole('alert')).toHaveTextContent('Please check the highlighted fields')

    fireEvent.change(departure(), { target: { value: '2026-11-06T08:00' } })
    await user.click(document.body)

    expect(screen.queryByText('Departure time must not be in the past.')).not.toBeInTheDocument()
  })

  it('offers ambiguous candidates that fill the field when chosen', async () => {
    const { user } = renderForm({
      problem: problem({
        code: 'GEOCODING_AMBIGUOUS',
        title: 'Which location did you mean?',
        message: 'The origin address matches multiple locations.',
        ambiguity: {
          field: 'origin',
          candidates: [
            { label: 'Springfield, MO, USA', latitude: 37.2, longitude: -93.3 },
            { label: 'Springfield, MA, USA', latitude: 42.1, longitude: -72.5 },
          ],
        },
      }),
    })
    await user.type(origin(), 'Springfield')
    // Typing hides the candidates; a fresh problem would show them again.
    expect(screen.queryByText('Did you mean:')).not.toBeInTheDocument()
  })

  it('fills the field from a chosen candidate', async () => {
    const { user } = renderForm({
      problem: problem({
        code: 'GEOCODING_AMBIGUOUS',
        title: 'Which location did you mean?',
        message: 'The origin address matches multiple locations.',
        ambiguity: {
          field: 'origin',
          candidates: [{ label: 'Springfield, MO, USA', latitude: 37.2, longitude: -93.3 }],
        },
      }),
    })

    expect(screen.getByRole('alert')).toHaveTextContent('Which location did you mean?')
    await user.click(screen.getByRole('button', { name: 'Use Springfield, MO, USA as the origin' }))

    expect(origin()).toHaveValue('Springfield, MO, USA')
    expect(origin()).toHaveFocus()
    expect(screen.queryByText('Did you mean:')).not.toBeInTheDocument()
  })

  it('sends a chosen candidate with its coordinates, so it cannot be ambiguous again', async () => {
    const { onSubmit, user } = renderForm({
      problem: problem({
        code: 'GEOCODING_AMBIGUOUS',
        ambiguity: {
          field: 'origin',
          candidates: [{ label: 'Springfield, MO, USA', latitude: 37.2, longitude: -93.3 }],
        },
      }),
    })
    await user.click(screen.getByRole('button', { name: 'Use Springfield, MO, USA as the origin' }))
    await user.type(destination(), 'Salt Lake City, UT')
    await user.keyboard('{Escape}')
    await user.type(weight(), '36000')

    await user.click(submit())

    expect(onSubmit).toHaveBeenCalledExactlyOnceWith(
      expect.objectContaining({
        origin: 'Springfield, MO, USA',
        origin_coordinates: { latitude: 37.2, longitude: -93.3 },
      }),
    )
  })

  it('tells the user when they can retry after a rate limit', () => {
    renderForm({
      problem: problem({
        code: 'RATE_LIMITED',
        title: 'Too many requests',
        message: 'Too many analysis requests. Try again later.',
        status: 429,
        retryAfterSeconds: 42,
      }),
    })

    expect(screen.getByRole('alert')).toHaveTextContent(
      'Too many requestsToo many analysis requests. Try again later. You can try again in 42 seconds.',
    )
  })

  it('hides the previous problem while a new analysis is running', () => {
    renderForm({ isSubmitting: true, problem: problem({ title: 'Old problem' }) })

    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
  })
})
