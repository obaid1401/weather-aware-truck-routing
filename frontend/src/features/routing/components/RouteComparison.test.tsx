import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'

import { multiRouteAnalysis } from '../../../shared/test/fixtures'
import { RISK_DISPLAY } from '../../risk/services/riskDisplay'
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

const card = (name: string) => within(screen.getByRole('article', { name }))

/** The value shown next to a label on a route card. */
const valueOf = (name: string, label: string) =>
  card(name).getByText(label).nextElementSibling?.textContent

describe('RouteComparison', () => {
  it('lists routes in ranked order, each with its status', () => {
    renderComparison()

    const cards = screen.getAllByRole('article')
    expect(cards.map((c) => within(c).getByRole('heading', { level: 3 }).textContent)).toEqual([
      'Route A',
      'Route B',
    ])
    expect(card('Route A').getByText('Recommended')).toBeInTheDocument()
    expect(card('Route B').getByText('Rank 2 of 2')).toBeInTheDocument()
  })

  it('shows every required metric for each route', () => {
    renderComparison()

    expect(valueOf('Route B', 'Distance')).toBe('62.0 mi')
    expect(valueOf('Route B', 'Travel time')).toBe('1 h 15 min')
    expect(valueOf('Route B', 'Estimated arrival')).toBeTruthy()
    expect(valueOf('Route B', 'Severe-risk miles')).toBe('12.5 mi')
    expect(valueOf('Route B', 'High-risk miles')).toBe('30.0 mi')
    expect(valueOf('Route B', 'No-travel miles')).toBe('3.0 mi')
    expect(valueOf('Route B', 'Weather coverage')).toBe('100%')
    expect(valueOf('Route A', 'Weather coverage')).toBe('50%')
  })

  it("draws each route's backend mileage by risk level, with a text description", () => {
    renderComparison()

    expect(card('Route B').getByRole('img')).toHaveAccessibleName(
      'Route miles by risk: 25.0 mi low, 25.0 mi moderate, 30.0 mi high, 12.5 mi severe, 3.0 mi no travel',
    )
    expect(card('Route A').getByRole('img')).toHaveAccessibleName(
      'Route miles by risk: 25.0 mi low, 25.0 mi moderate, 25.0 mi unavailable',
    )
  })

  it('shows unavailable average risk as unavailable, and unknown miles only where there are any', () => {
    renderComparison()

    expect(valueOf('Route B', 'Average risk')).toBe('Unavailable')
    expect(valueOf('Route A', 'Average risk')).toBe('1.50 of 5')
    expect(valueOf('Route A', 'Unknown-risk miles')).toBe('25.0 mi')
    expect(card('Route B').queryByText('Unknown-risk miles')).not.toBeInTheDocument()
  })

  it('marks no-travel exposure with an icon as well as colour', () => {
    renderComparison()
    const routeB = card('Route B').getByText('No-travel miles').nextElementSibling!
    const routeA = card('Route A').getByText('No-travel miles').nextElementSibling!

    expect(routeB.querySelector('svg')).toBeInTheDocument()
    expect(routeB.firstElementChild).toHaveStyle({ color: RISK_DISPLAY.NO_TRAVEL.color })
    expect(routeA.querySelector('svg')).not.toBeInTheDocument()
  })

  it('explains the rank of a selected route that is not recommended', () => {
    renderComparison('route-2')

    expect(screen.getByRole('heading', { name: 'Why Route B is rank 2' })).toBeInTheDocument()
    expect(screen.getByText('Route B ranks 2nd: 12.5 mi severe-risk.')).toBeInTheDocument()
  })

  it('does not repeat the recommended route’s reason, which the verdict shows', () => {
    renderComparison('route-1')

    expect(screen.queryByRole('heading', { name: /^Why/ })).not.toBeInTheDocument()
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
