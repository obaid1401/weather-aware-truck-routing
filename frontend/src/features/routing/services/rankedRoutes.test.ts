import { describe, expect, it } from 'vitest'

import { multiRouteAnalysis } from '../../../shared/test/fixtures'
import { rankedRoutes } from './rankedRoutes'

const [routeA, routeB] = multiRouteAnalysis.routes
const recommendation = multiRouteAnalysis.recommendation!

describe('rankedRoutes', () => {
  it("follows the backend's ranking, not the provider order", () => {
    const ranked = rankedRoutes([routeB, routeA], recommendation)

    expect(ranked.map((r) => [r.route.id, r.rank, r.isRecommended])).toEqual([
      ['route-1', 1, true],
      ['route-2', 2, false],
    ])
    expect(ranked[1].reason).toBe('Route B ranks 2nd: 12.5 mi severe-risk.')
  })

  it('keeps provider order and marks routes unranked when there is no recommendation', () => {
    const ranked = rankedRoutes([routeB, routeA], null)

    expect(ranked.map((r) => [r.route.id, r.rank, r.isRecommended, r.reason])).toEqual([
      ['route-2', null, false, null],
      ['route-1', null, false, null],
    ])
  })
})
