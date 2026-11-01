import type { AnalyzedRoute, Recommendation } from '../../analysis/types/api'

export interface RankedRoute {
  route: AnalyzedRoute
  /** 1-based rank from the backend, or null if the backend did not rank this route. */
  rank: number | null
  isRecommended: boolean
  /** The backend's explanation for this route's rank, if any. */
  reason: string | null
}

/** Routes in the backend's ranked order (unranked routes after them, in provider order). The
 * ranking itself comes from the backend; nothing is re-ranked or re-scored here. */
export function rankedRoutes(
  routes: AnalyzedRoute[],
  recommendation: Recommendation | null,
): RankedRoute[] {
  const rankedIds = recommendation?.ranked_route_ids ?? []
  const withRank = routes.map((route) => {
    const index = rankedIds.indexOf(route.id)
    return {
      route,
      rank: index >= 0 ? index + 1 : null,
      isRecommended: route.id === recommendation?.recommended_route_id,
      reason: index >= 0 ? (recommendation?.ranking_reasons[index] ?? null) : null,
    }
  })
  // Array.prototype.sort is stable, so unranked routes keep provider order.
  return withRank.sort((a, b) => (a.rank ?? Infinity) - (b.rank ?? Infinity))
}
