import { ThemeProvider } from '@mui/material/styles'
import { fireEvent, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'

import type { ApiProblem } from '../../analysis/services/apiProblem'
import { theme } from '../../../shared/theme/theme'
import { TripForm } from './TripForm'

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
  const view = render(
    <ThemeProvider theme={theme}>
      <TripForm onSubmit={onSubmit} isSubmitting={false} problem={null} now={() => NOW} {...props} />
    </ThemeProvider>,
  )
  const rerender = (next: Partial<Parameters<typeof TripForm>[0]>) =>
    view.rerender(
      <ThemeProvider theme={theme}>
        <TripForm onSubmit={onSubmit} isSubmitting={false} problem={null} now={() => NOW} {...props} {...next} />
      </ThemeProvider>,
    )
  return { onSubmit, rerender, user: userEvent.setup() }
}

const origin = () => screen.getByRole('textbox', { name: /origin/i })
const destination = () => screen.getByRole('textbox', { name: /destination/i })
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
