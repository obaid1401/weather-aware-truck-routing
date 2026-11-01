import { fireEvent, render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'

import { multiRouteAnalysis } from '../../shared/test/fixtures'
import { AnalysisResults } from './AnalysisResults'

function renderResults() {
  const view = render(<AnalysisResults analysis={multiRouteAnalysis} />)
  return { ...view, user: userEvent.setup() }
}

const heatmapRisks = (container: HTMLElement) =>
  [...container.querySelectorAll('path.heatmap-cell')]
    .map((path) => [...path.classList].find((c) => c.startsWith('risk-')))
    .sort()

/** Strip-map ticks, in mileage order. */
const stripTicks = (container: HTMLElement) => [...container.querySelectorAll<HTMLElement>('button[data-risk]')]

/** Route order and each route's status, as the route cards show them. */
const ranking = () =>
  screen.getAllByRole('article').map((card) => {
    const name = within(card).getByRole('heading', { level: 3 }).textContent
    return `${name}: ${within(card).getByText(/^(Recommended|Rank \d of \d|Not ranked)$/).textContent}`
  })

const openTab = (user: ReturnType<typeof userEvent.setup>, name: RegExp) =>
  user.click(screen.getByRole('tab', { name }))

describe('AnalysisResults', () => {
  it('starts with the recommended route at hour 0, on the routes tab', () => {
    const { container } = renderResults()

    expect(screen.getByRole('heading', { name: 'Map: Route A' })).toBeInTheDocument()
    expect(screen.getByRole('slider')).toHaveValue('0')
    expect(container.querySelectorAll('path.checkpoint-marker')).toHaveLength(3)
    expect(screen.getByRole('tab', { name: 'Routes (2)' })).toHaveAttribute('aria-selected', 'true')
    expect(screen.getByRole('tab', { name: 'Checkpoints (3)' })).toBeInTheDocument()
    expect(ranking()).toEqual(['Route A: Recommended', 'Route B: Rank 2 of 2'])
  })

  it('moving the slider updates the heatmap, the strip, and the selected hour, not the ranking', () => {
    const { container } = renderResults()

    fireEvent.change(screen.getByRole('slider'), { target: { value: 6 } })

    expect(heatmapRisks(container)).toEqual(['risk-moderate', 'risk-severe', 'risk-unknown'])
    expect(stripTicks(container).map((tick) => tick.dataset.risk)).toEqual(['SEVERE', 'MODERATE', 'UNKNOWN'])
    expect(screen.getByRole('slider')).toHaveAttribute(
      'aria-valuetext',
      expect.stringMatching(/^6 hours after departure, /),
    )
    expect(ranking()).toEqual(['Route A: Recommended', 'Route B: Rank 2 of 2'])
    // Checkpoint markers keep the risk at arrival, which the ranking uses.
    expect(container.querySelectorAll('path.checkpoint-marker.risk-severe')).toHaveLength(0)
  })

  it('reports checkpoints without a forecast for the selected hour, on the strip too', () => {
    const { container } = renderResults()

    fireEvent.change(screen.getByRole('slider'), { target: { value: 48 } })

    expect(
      screen.getByText('No forecast for 2 of 3 checkpoints at this hour. They are shown as unavailable.'),
    ).toBeInTheDocument()
    expect(stripTicks(container).map((tick) => tick.dataset.risk)).toEqual(['LOW', 'UNKNOWN', 'UNKNOWN'])
    expect(screen.getByText('Route A at +48 h: 1 low, 2 unavailable.')).toBeInTheDocument()
  })

  it('selecting another route shows its checkpoints and clears the checkpoint selection', async () => {
    const { container, user } = renderResults()
    await openTab(user, /^Checkpoints/)
    await user.click(screen.getByRole('button', { name: /^Checkpoint 1 at 25.0 mi/ }))
    await openTab(user, /^Routes/)

    await user.click(screen.getByRole('button', { name: 'Show Route B on the map' }))

    expect(screen.getByRole('heading', { name: 'Map: Route B' })).toBeInTheDocument()
    expect(container.querySelectorAll('path.checkpoint-marker')).toHaveLength(2)
    expect(container.querySelector('path.checkpoint-marker.risk-no_travel')).toBeInTheDocument()
    expect(stripTicks(container)).toHaveLength(2)
    await openTab(user, /^Checkpoints \(2\)/)
    expect(screen.getByRole('heading', { name: 'Checkpoints on Route B' })).toBeInTheDocument()
    expect(screen.getByText(/select a checkpoint on the map/i)).toBeInTheDocument()
  })

  it('selecting a checkpoint in the list shows its details and highlights its marker', async () => {
    const { container, user } = renderResults()
    await openTab(user, /^Checkpoints/)

    await user.click(screen.getByRole('button', { name: /^Checkpoint 1 at 25.0 mi/ }))

    const details = within(screen.getByRole('complementary', { name: 'Checkpoint details' }))
    expect(details.getByRole('heading', { name: 'Checkpoint 1 at 25.0 mi' })).toBeInTheDocument()
    expect(container.querySelector('path.checkpoint-marker.selected')).toHaveClass('risk-moderate')
  })

  it('selecting a checkpoint marker on the map opens its details', () => {
    const { container } = renderResults()

    fireEvent.click(container.querySelector('path.checkpoint-marker.risk-unknown')!)

    expect(screen.getByRole('tab', { name: /^Checkpoints/ })).toHaveAttribute('aria-selected', 'true')
    expect(screen.getByRole('heading', { name: 'Destination at 50.0 mi' })).toBeInTheDocument()
  })

  it('selecting a tick on the strip map opens that checkpoint', () => {
    const { container } = renderResults()

    fireEvent.click(stripTicks(container)[1])

    expect(screen.getByRole('tab', { name: /^Checkpoints/ })).toHaveAttribute('aria-selected', 'true')
    expect(screen.getByRole('heading', { name: 'Checkpoint 1 at 25.0 mi' })).toBeInTheDocument()
    expect(container.querySelector('path.checkpoint-marker.selected')).toHaveClass('risk-moderate')
  })

  it('opens the map key, which explains markers, circles, and unavailable data', async () => {
    const { user } = renderResults()
    const toggle = screen.getByRole('button', { name: 'How to read the map' })
    expect(toggle).toHaveAttribute('aria-expanded', 'false')

    await user.click(toggle)

    expect(toggle).toHaveAttribute('aria-expanded', 'true')
    const key = within(screen.getByRole('region', { name: 'Map key' }))
    expect(key.getByText(/Checkpoint marker: risk at the estimated arrival/)).toBeInTheDocument()
    expect(key.getByText(/not blended or interpolated between checkpoints/)).toBeInTheDocument()
    expect(key.getByText(/forecast unavailable, so the risk is unknown/i)).toBeInTheDocument()
  })
})
