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

describe('AnalysisResults', () => {
  it('starts with the recommended route at hour 0', () => {
    const { container } = renderResults()

    expect(screen.getByRole('heading', { name: 'Map: Route A' })).toBeInTheDocument()
    expect(screen.getByRole('slider')).toHaveValue('0')
    expect(container.querySelectorAll('path.checkpoint-marker')).toHaveLength(3)
  })

  it('moving the slider updates the heatmap and the selected hour, not the ranking', () => {
    const { container } = renderResults()
    const rankingBefore = screen.getAllByRole('article').map((card) => card.textContent)

    fireEvent.change(screen.getByRole('slider'), { target: { value: 6 } })

    expect(heatmapRisks(container)).toEqual(['risk-moderate', 'risk-severe', 'risk-unknown'])
    expect(screen.getByRole('slider')).toHaveAttribute(
      'aria-valuetext',
      expect.stringMatching(/^6 hours after departure, /),
    )
    expect(screen.getAllByRole('article').map((card) => card.textContent)).toEqual(rankingBefore)
    // Checkpoint markers keep the risk at arrival, which the ranking uses.
    expect(container.querySelectorAll('path.checkpoint-marker.risk-severe')).toHaveLength(0)
  })

  it('reports checkpoints without a forecast for the selected hour', () => {
    renderResults()

    fireEvent.change(screen.getByRole('slider'), { target: { value: 48 } })

    expect(
      screen.getByText('Forecast unavailable for 2 of 3 checkpoints at this hour.'),
    ).toBeInTheDocument()
  })

  it('selecting another route shows its checkpoints and clears the checkpoint selection', async () => {
    const { container, user } = renderResults()
    await user.click(screen.getByRole('button', { name: /Checkpoint 1 · 25.0 mi/ }))

    await user.click(screen.getByRole('button', { name: 'Show Route B on the map' }))

    expect(screen.getByRole('heading', { name: 'Map: Route B' })).toBeInTheDocument()
    expect(container.querySelectorAll('path.checkpoint-marker')).toHaveLength(2)
    expect(container.querySelector('path.checkpoint-marker.risk-no_travel')).toBeInTheDocument()
    expect(screen.getByText(/select a checkpoint on the map or in the list/i)).toBeInTheDocument()
  })

  it('selecting a checkpoint in the list shows its details and highlights its marker', async () => {
    const { container, user } = renderResults()

    await user.click(screen.getByRole('button', { name: /Checkpoint 1 · 25.0 mi/ }))

    const details = within(screen.getByRole('complementary', { name: 'Checkpoint details' }))
    expect(details.getByRole('heading', { name: 'Checkpoint 1 · 25.0 mi' })).toBeInTheDocument()
    expect(container.querySelector('path.checkpoint-marker.selected')).toHaveClass('risk-moderate')
  })

  it('selecting a checkpoint marker on the map shows its details', () => {
    const { container } = renderResults()

    fireEvent.click(container.querySelector('path.checkpoint-marker.risk-unknown')!)

    expect(screen.getByRole('heading', { name: 'Destination · 50.0 mi' })).toBeInTheDocument()
  })
})
