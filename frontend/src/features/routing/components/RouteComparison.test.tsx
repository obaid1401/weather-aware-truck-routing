import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'

import { multiRouteAnalysis } from '../../../shared/test/fixtures'
import { RouteComparison } from './RouteComparison'

function renderComparison(selectedRouteId = 'route-1') {
  const onSelectRoute = vi.fn()
  render(
    <RouteComparison
      routes={multiRouteAnalysis.routes}
      recommendation={multiRouteAnalysis.recommendation}
      selectedRouteId={selectedRouteId}
      onSelectRoute={onSelectRoute}
    />,
  )
  return { onSelectRoute, user: userEvent.setup() }
}

const card = (name: string) => screen.getByRole('article', { name })

describe('RouteComparison', () => {
  it('lists routes in ranked order with the recommendation status', () => {
    renderComparison()

    const cards = screen.getAllByRole('article')
    expect(cards.map((c) => within(c).getByRole('heading').textContent)).toEqual(['Route A', 'Route B'])
    expect(within(cards[0]).getByText('Recommended')).toBeInTheDocument()
    expect(within(cards[1]).getByText('Rank 2 of 2')).toBeInTheDocument()
  })

  it('shows every required metric and the ranking explanation', () => {
    renderComparison()
    const routeB = within(card('Route B'))

    for (const [term, value] of [
      ['Distance', '62.0 mi'],
      ['Travel time', '1 h 15 min'],
      ['Severe-risk miles', '12.5 mi'],
      ['High-risk miles', '30.0 mi'],
      ['No-travel miles', '3.0 mi'],
      ['Weather coverage', '100%'],
    ]) {
      expect(routeB.getByText(term).nextElementSibling).toHaveTextContent(value)
    }
    expect(routeB.getByText('Estimated arrival')).toBeInTheDocument()
    expect(routeB.getByText('Route B ranks 2nd: 12.5 mi severe-risk.')).toBeInTheDocument()
  })

  it('shows unavailable average risk as unavailable, and unknown miles when there are any', () => {
    renderComparison()

    expect(within(card('Route B')).getByText('Average risk').nextElementSibling).toHaveTextContent(
      'Unavailable',
    )
    expect(within(card('Route A')).getByText('Average risk').nextElementSibling).toHaveTextContent(
      '1.50 of 5',
    )
    expect(within(card('Route A')).getByText('Unknown-risk miles').nextElementSibling).toHaveTextContent(
      '25.0 mi',
    )
    expect(within(card('Route B')).queryByText('Unknown-risk miles')).not.toBeInTheDocument()
  })

  it('highlights no-travel exposure', () => {
    renderComparison()

    expect(within(card('Route B')).getByRole('note')).toHaveTextContent(
      'No-travel conditions on 3.0 mi',
    )
    expect(within(card('Route A')).queryByRole('note')).not.toBeInTheDocument()
  })

  it('selects a route with its button', async () => {
    const { onSelectRoute, user } = renderComparison()

    expect(screen.getByRole('button', { name: 'Show Route A on the map' })).toHaveAttribute(
      'aria-pressed',
      'true',
    )
    await user.click(screen.getByRole('button', { name: 'Show Route B on the map' }))

    expect(onSelectRoute).toHaveBeenCalledTimes(1)
    expect(onSelectRoute).toHaveBeenCalledWith('route-2')
  })
})
