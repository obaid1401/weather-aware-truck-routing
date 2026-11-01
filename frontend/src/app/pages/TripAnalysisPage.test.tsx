import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { analyzeTrip } from '../../features/analysis/api/analyzeTrip'
import { InvalidAnalysisResponseError } from '../../features/analysis/services/analysisResponse'
import { analysisResponse, apiError, errorBody, multiRouteAnalysis } from '../../shared/test/fixtures'
import { AppProviders } from '../AppProviders'
import { TripAnalysisPage } from './TripAnalysisPage'

vi.mock('../../features/analysis/api/analyzeTrip', () => ({ analyzeTrip: vi.fn() }))
const mockedAnalyzeTrip = vi.mocked(analyzeTrip)

function renderPage() {
  render(
    <AppProviders>
      <TripAnalysisPage />
    </AppProviders>,
  )
  return userEvent.setup()
}

async function submitTrip(user: ReturnType<typeof userEvent.setup>) {
  await user.type(screen.getByRole('textbox', { name: /origin/i }), 'Denver, CO')
  await user.type(screen.getByRole('textbox', { name: /destination/i }), 'Salt Lake City, UT')
  await user.type(screen.getByRole('textbox', { name: /cargo weight/i }), '36000')
  await user.click(screen.getByRole('button', { name: /analyze routes/i }))
}

beforeEach(() => {
  mockedAnalyzeTrip.mockReset()
})

describe('trip analysis page', () => {
  it('starts with the trip form and an empty base map', () => {
    renderPage()

    expect(screen.getByRole('heading', { level: 1, name: 'Weather-Aware Truck Routing' })).toBeInTheDocument()
    expect(screen.getByRole('textbox', { name: /origin/i })).toBeInTheDocument()
    const map = within(screen.getByRole('region', { name: 'Route map' }))
    expect(map.getByText(/your routes, checkpoints, and the weather along them will appear here/i)).toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: /recommended/i })).not.toBeInTheDocument()
  })

  it('submits the trip and shows the backend analysis', async () => {
    mockedAnalyzeTrip.mockResolvedValue(analysisResponse)
    const user = renderPage()

    await submitTrip(user)

    expect(await screen.findByRole('heading', { name: 'Recommended route: Route A' })).toBeInTheDocument()
    expect(mockedAnalyzeTrip).toHaveBeenCalledTimes(1)
    expect(mockedAnalyzeTrip.mock.calls[0][0]).toMatchObject({
      origin: 'Denver, CO',
      destination: 'Salt Lake City, UT',
      load_weight_lbs: 36000,
      checkpoint_interval_miles: 25,
    })
    expect(mockedAnalyzeTrip.mock.calls[0][0].departure_time).toMatch(
      /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:00[+-]\d{2}:\d{2}$/,
    )
    const summary = within(
      screen.getByRole('region', {
        name: '1 route analyzed from Denver, CO, USA to Salt Lake City, UT, USA',
      }),
    )
    expect(summary.getByText('536.2 mi')).toBeInTheDocument()
    expect(summary.getByText('7 h 56 min')).toBeInTheDocument()
    expect(summary.getByText('100%')).toBeInTheDocument()
    expect(summary.getByText(analysisResponse.recommendation!.ranking_reasons[0])).toBeInTheDocument()
    // Every safety and provider warning is shown.
    expect(summary.getByText(analysisResponse.recommendation!.warnings[0])).toBeInTheDocument()
    expect(summary.getByText(analysisResponse.provider_warnings[0])).toBeInTheDocument()
    // The route comparison and map follow the summary.
    expect(screen.getByRole('heading', { name: 'Compare routes' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Map: Route A' })).toBeInTheDocument()
    // Announced to screen readers when the results arrive.
    expect(screen.getByText('Analysis ready: 1 route compared.')).toHaveAttribute('role', 'status')
  })

  it('folds the form into a trip summary, and Edit trip reopens it with the entered values', async () => {
    mockedAnalyzeTrip.mockResolvedValue(analysisResponse)
    const user = renderPage()
    await submitTrip(user)

    const trip = within(await screen.findByRole('region', { name: 'Trip' }))
    expect(await trip.findByRole('heading', { name: 'Your trip' })).toBeInTheDocument()
    expect(trip.getByText('Denver, CO, USA')).toBeInTheDocument()
    expect(trip.getByText('36,000 lb')).toBeInTheDocument()
    await waitFor(() => expect(screen.queryByRole('textbox', { name: /origin/i })).not.toBeInTheDocument())

    await user.click(trip.getByRole('button', { name: 'Edit trip' }))

    const origin = await screen.findByRole('textbox', { name: /origin/i })
    expect(origin).toHaveValue('Denver, CO')
    expect(screen.getByRole('textbox', { name: /cargo weight/i })).toHaveValue('36000')
    await waitFor(() => expect(origin).toHaveFocus())
    // The results stay until a new analysis replaces them.
    expect(screen.getByRole('heading', { name: 'Recommended route: Route A' })).toBeInTheDocument()
  })

  it('never re-requests the analysis when the route, checkpoint, or forecast hour changes', async () => {
    mockedAnalyzeTrip.mockResolvedValue(multiRouteAnalysis)
    const user = renderPage()
    await submitTrip(user)
    await screen.findByRole('heading', { name: 'Map: Route A' })
    const recommendation = screen.getByRole('heading', { name: 'Recommended route: Route A' })
    // Route order and each route's status, as shown on the route cards.
    const ranking = () =>
      screen.getAllByRole('article').map((card) => [
        within(card).getByRole('heading', { level: 3 }).textContent,
        within(card).getByText(/^(Recommended|Rank \d of \d)$/).textContent,
      ])
    const rankingBefore = ranking()

    await user.click(screen.getByRole('button', { name: 'Show Route B on the map' }))
    await user.click(screen.getByRole('tab', { name: /^Checkpoints/ }))
    await user.click(screen.getByRole('button', { name: /^Destination at 62.0 mi/ }))
    fireEvent.change(screen.getByRole('slider'), { target: { value: 30 } })

    expect(screen.getByRole('heading', { name: 'Map: Route B' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Destination at 62.0 mi' })).toBeInTheDocument()
    expect(mockedAnalyzeTrip).toHaveBeenCalledTimes(1)
    expect(recommendation).toBeInTheDocument()
    await user.click(screen.getByRole('tab', { name: /^Routes/ }))
    expect(ranking()).toEqual(rankingBefore)
    expect(rankingBefore).toEqual([
      ['Route A', 'Recommended'],
      ['Route B', 'Rank 2 of 2'],
    ])
  })

  it('shows a loading state and blocks duplicate submissions', async () => {
    mockedAnalyzeTrip.mockReturnValue(new Promise(() => {}))
    const user = renderPage()

    await submitTrip(user)

    const busy = await screen.findByRole('button', { name: /analyzing routes/i })
    expect(busy).toBeDisabled()
    // The disabled button cannot be clicked; pressing Enter in a field must not resubmit either.
    await user.type(screen.getByRole('textbox', { name: /origin/i }), '{Enter}')
    expect(mockedAnalyzeTrip).toHaveBeenCalledTimes(1)
    expect(
      screen.getByText('Finding truck routes and checking the forecast along each one…'),
    ).toBeInTheDocument()
  })

  it('shows the error and keeps the entered values when the analysis fails', async () => {
    mockedAnalyzeTrip.mockRejectedValue(
      apiError(
        422,
        errorBody('ROUTE_DISTANCE_LIMIT', "The trip exceeds the routing server's maximum truck route distance."),
      ),
    )
    const user = renderPage()

    await submitTrip(user)

    const alert = await screen.findByRole('alert')
    expect(alert).toHaveTextContent('Trip too long for the routing service')
    expect(alert).toHaveTextContent("The trip exceeds the routing server's maximum truck route distance.")
    expect(screen.getByRole('textbox', { name: /origin/i })).toHaveValue('Denver, CO')
    expect(screen.getByRole('textbox', { name: /destination/i })).toHaveValue('Salt Lake City, UT')
    expect(screen.getByRole('textbox', { name: /cargo weight/i })).toHaveValue('36000')
    expect(screen.getByRole('button', { name: /analyze routes/i })).toBeEnabled()
  })

  it('shows an error state instead of results when the response is malformed', async () => {
    mockedAnalyzeTrip.mockRejectedValue(new InvalidAnalysisResponseError(['routes']))
    const user = renderPage()

    await submitTrip(user)

    expect(await screen.findByRole('alert')).toHaveTextContent('Unexpected response from the server')
    expect(screen.queryByRole('heading', { name: /recommended/i })).not.toBeInTheDocument()
  })

  it('lets the user retry after a failure', async () => {
    mockedAnalyzeTrip
      .mockRejectedValueOnce(apiError(503, errorBody('PROVIDER_UNAVAILABLE', 'Try again later.')))
      .mockResolvedValueOnce(analysisResponse)
    const user = renderPage()

    await submitTrip(user)
    await screen.findByRole('alert')
    await user.click(screen.getByRole('button', { name: /analyze routes/i }))

    await waitFor(() => expect(mockedAnalyzeTrip).toHaveBeenCalledTimes(2))
    expect(await screen.findByRole('heading', { name: 'Recommended route: Route A' })).toBeInTheDocument()
    // The earlier failure is gone (the summary's own warnings remain).
    expect(screen.queryByText('A data provider is unavailable')).not.toBeInTheDocument()
  })
})
